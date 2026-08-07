"""OAuth (PKCE) credentials for the ChatGPT Codex backend.

Authenticates with a ChatGPT Plus/Pro subscription using the same OAuth
client as the official Codex CLI. Credentials are resolved from, in order:

1. FLE's own credential file (``~/.fle/codex_auth.json``)
2. The official Codex CLI (``~/.codex/auth.json``, created by ``codex login``)
3. codex-proxy (``~/.codex-proxy/credentials.json``)

Refreshed tokens are always written back to FLE's own file so we never
clobber another tool's refresh token.
"""

import base64
import errno
import hashlib
import json
import logging
import os
import secrets
import tempfile
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

log = logging.getLogger(__name__)

# OAuth client used by the official Codex CLI (public client, PKCE).
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CALLBACK_PORT = 1455
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/auth/callback"
SCOPE = "openid profile email offline_access"
JWT_CLAIM_PATH = "https://api.openai.com/auth"

FLE_CREDENTIALS_FILE = Path.home() / ".fle" / "codex_auth.json"
CODEX_CLI_AUTH_FILE = Path.home() / ".codex" / "auth.json"
CODEX_PROXY_CREDENTIALS_FILE = Path.home() / ".codex-proxy" / "credentials.json"


class CodexAuthError(RuntimeError):
    """Raised when Codex OAuth credentials are missing or unusable."""


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


def _jwt_claim(token: Optional[str], *names: str) -> Optional[str]:
    if not token:
        return None
    try:
        payload = _decode_jwt_payload(token)
    except (ValueError, json.JSONDecodeError):
        return None
    for name in names:
        value = payload.get(name)
        if isinstance(value, str) and value:
            return value
    return None


def _jwt_expiry(token: str) -> Optional[float]:
    try:
        exp = _decode_jwt_payload(token).get("exp")
        return float(exp) if exp else None
    except (ValueError, json.JSONDecodeError, TypeError):
        return None


def extract_account_id(access_token: str) -> str:
    try:
        payload = _decode_jwt_payload(access_token)
    except (ValueError, json.JSONDecodeError) as exc:
        raise CodexAuthError(
            "Access token is not a decodable JWT, so the ChatGPT account id "
            "cannot be determined. Run 'fle codex login' to re-authenticate."
        ) from exc
    account_id = payload.get(JWT_CLAIM_PATH, {}).get("chatgpt_account_id")
    if not account_id:
        raise CodexAuthError("No chatgpt_account_id claim in access token")
    return account_id


@dataclass
class CodexCredentials:
    access_token: str
    account_id: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    email: Optional[str] = None
    expires_at: float = 0.0
    source: str = "fle"
    origin: Optional[Path] = None

    def is_expired(self, margin: float = 60.0) -> bool:
        return time.time() >= self.expires_at - margin

    def to_dict(self, include_provenance: bool = False) -> dict[str, Any]:
        payload = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "account_id": self.account_id,
            "email": self.email,
            "expires_at": self.expires_at,
        }
        if include_provenance:
            # Only FLE's own file records provenance; without it a reload
            # would forget the true origin after the first refresh and stop
            # writing rotated tokens back (logging the owning tool out).
            payload["source"] = self.source
            payload["origin"] = str(self.origin) if self.origin else None
        return payload


def _from_token_response(
    token_response: dict[str, Any], previous: Optional[CodexCredentials] = None
) -> CodexCredentials:
    access_token = token_response["access_token"]
    id_token = token_response.get("id_token") or (
        previous.id_token if previous else None
    )
    expires_at = _jwt_expiry(access_token) or (
        time.time() + float(token_response.get("expires_in", 3600))
    )
    return CodexCredentials(
        access_token=access_token,
        refresh_token=token_response.get("refresh_token")
        or (previous.refresh_token if previous else None),
        account_id=extract_account_id(access_token),
        id_token=id_token,
        email=_jwt_claim(id_token, "email") or (previous.email if previous else None),
        expires_at=expires_at,
        source=previous.source if previous else "fle",
        origin=previous.origin if previous else FLE_CREDENTIALS_FILE,
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON 0600 via a same-directory temp file + rename.

    A torn write to a credential file logs the owning tool out, so the file is
    only ever replaced once it is complete on disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.chmod(0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def save_credentials(
    credentials: CodexCredentials, path: Path = FLE_CREDENTIALS_FILE
) -> None:
    _atomic_write_json(path, credentials.to_dict(include_provenance=True))


def _write_back_to_origin(credentials: CodexCredentials) -> None:
    """Update the file the credentials were loaded from with the rotated tokens.

    OpenAI rotates the refresh token on every use, so refreshing another tool's
    credentials invalidates the copy that tool still holds -- silently breaking
    e.g. the official ``codex`` CLI. Write the new pair back in that file's own
    schema so borrowing credentials stays non-destructive.
    """
    origin = credentials.origin
    if origin is None or origin == FLE_CREDENTIALS_FILE:
        return
    existing = _load_json(origin)
    if existing is None:
        return
    if credentials.source == "codex-cli":
        tokens = existing.setdefault("tokens", {})
        tokens["access_token"] = credentials.access_token
        tokens["refresh_token"] = credentials.refresh_token
        tokens["account_id"] = credentials.account_id
        if credentials.id_token:
            tokens["id_token"] = credentials.id_token
        existing["last_refresh"] = (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        )
    else:
        existing.update(credentials.to_dict())
    try:
        _atomic_write_json(origin, existing)
    except OSError as exc:
        log.warning(
            "Could not write refreshed Codex tokens back to %s: %s", origin, exc
        )


def persist_credentials(credentials: CodexCredentials) -> None:
    """Persist to FLE's own store and back to the file the tokens came from."""
    save_credentials(credentials)
    _write_back_to_origin(credentials)


def _load_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def load_credentials() -> Optional[CodexCredentials]:
    """Load credentials from the first usable source."""
    data = _load_json(FLE_CREDENTIALS_FILE)
    if data and data.get("access_token"):
        try:
            # Restore the provenance recorded by save_credentials() so tokens
            # borrowed from another tool keep being written back to that
            # tool's file across refreshes, not just the first one.
            origin_str = data.get("origin")
            return CodexCredentials(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                account_id=data.get("account_id")
                or extract_account_id(data["access_token"]),
                id_token=data.get("id_token"),
                email=data.get("email"),
                expires_at=float(
                    data.get("expires_at") or _jwt_expiry(data["access_token"]) or 0.0
                ),
                source=data.get("source") or "fle",
                origin=Path(origin_str) if origin_str else FLE_CREDENTIALS_FILE,
            )
        except CodexAuthError as exc:
            log.warning(
                "Ignoring unusable credentials in %s: %s", FLE_CREDENTIALS_FILE, exc
            )

    # Official Codex CLI: {"tokens": {"access_token", "refresh_token", ...}}
    data = _load_json(CODEX_CLI_AUTH_FILE)
    tokens = (data or {}).get("tokens") or {}
    if tokens.get("access_token"):
        try:
            return CodexCredentials(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                account_id=tokens.get("account_id")
                or extract_account_id(tokens["access_token"]),
                id_token=tokens.get("id_token"),
                email=_jwt_claim(tokens.get("id_token"), "email"),
                expires_at=_jwt_expiry(tokens["access_token"]) or 0.0,
                source="codex-cli",
                origin=CODEX_CLI_AUTH_FILE,
            )
        except CodexAuthError as exc:
            log.warning(
                "Ignoring unusable credentials in %s: %s", CODEX_CLI_AUTH_FILE, exc
            )

    # codex-proxy: same schema as FLE's own file
    data = _load_json(CODEX_PROXY_CREDENTIALS_FILE)
    if data and data.get("access_token"):
        try:
            return CodexCredentials(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                account_id=data.get("account_id")
                or extract_account_id(data["access_token"]),
                id_token=data.get("id_token"),
                email=data.get("email"),
                expires_at=float(
                    data.get("expires_at") or _jwt_expiry(data["access_token"]) or 0.0
                ),
                source="codex-proxy",
                origin=CODEX_PROXY_CREDENTIALS_FILE,
            )
        except CodexAuthError as exc:
            log.warning(
                "Ignoring unusable credentials in %s: %s",
                CODEX_PROXY_CREDENTIALS_FILE,
                exc,
            )

    return None


async def refresh_credentials(credentials: CodexCredentials) -> CodexCredentials:
    if not credentials.refresh_token:
        raise CodexAuthError(
            "Codex access token expired and no refresh token is available. "
            "Run 'fle codex login'."
        )
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": credentials.refresh_token,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(TOKEN_URL, data=data) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise CodexAuthError(
                    f"Codex token refresh failed ({resp.status}): {body[:500]}. "
                    "Run 'fle codex login' to re-authenticate."
                )
            token_response = await resp.json()
    refreshed = _from_token_response(token_response, previous=credentials)
    persist_credentials(refreshed)
    return refreshed


async def ensure_credentials() -> CodexCredentials:
    """Load credentials, refreshing if expired. Raises CodexAuthError if absent."""
    credentials = load_credentials()
    if credentials is None:
        raise CodexAuthError(
            "No ChatGPT/Codex credentials found. Run 'fle codex login' "
            "(or 'codex login' with the official Codex CLI)."
        )
    if credentials.is_expired():
        credentials = await refresh_credentials(credentials)
    return credentials


# --- Interactive PKCE login flow ---


class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code: Optional[str] = None
    error: Optional[str] = None
    expected_state: Optional[str] = None
    received = Event()

    def do_GET(self) -> None:  # noqa: N802
        params = parse_qs(urlparse(self.path).query)
        state = params.get("state", [None])[0]
        if _CallbackHandler.expected_state and state != _CallbackHandler.expected_state:
            _CallbackHandler.error = "state_mismatch"
            self._respond(400, "<h1>Login failed: state mismatch</h1>")
            _CallbackHandler.received.set()
            return
        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            self._respond(
                200, "<h1>Login successful!</h1><p>You can close this tab.</p>"
            )
        elif "error" in params:
            _CallbackHandler.error = params["error"][0]
            desc = params.get("error_description", [""])[0]
            self._respond(400, f"<h1>Login failed: {desc}</h1>")
        else:
            self.send_response(404)
            self.end_headers()
            return
        _CallbackHandler.received.set()

    def _respond(self, status: int, html: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format: str, *args: Any) -> None:
        pass


class _CallbackServer(HTTPServer):
    allow_reuse_address = True


async def login() -> CodexCredentials:
    """Run the OAuth PKCE login flow in a browser and persist credentials."""
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    state = secrets.token_urlsafe(32)

    _CallbackHandler.auth_code = None
    _CallbackHandler.error = None
    _CallbackHandler.expected_state = state
    _CallbackHandler.received = Event()
    try:
        server = _CallbackServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise CodexAuthError(
                f"OAuth callback port {CALLBACK_PORT} is already in use "
                "(is another login flow or the Codex CLI running?)"
            ) from exc
        raise

    params = urlencode(
        {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "audience": "https://api.openai.com/v1",
            "state": state,
        }
    )
    auth_url = f"{AUTHORIZE_URL}?{params}"
    print(f"Opening browser for ChatGPT login...\n  {auth_url}")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        if not _CallbackHandler.received.wait(timeout=180):
            raise CodexAuthError("OAuth callback timed out")
        if _CallbackHandler.error:
            raise CodexAuthError(f"OAuth error: {_CallbackHandler.error}")
        code = _CallbackHandler.auth_code
        if not code:
            raise CodexAuthError("No authorization code received")
    finally:
        server.shutdown()
        server.server_close()

    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": REDIRECT_URI,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(TOKEN_URL, data=data) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise CodexAuthError(
                    f"Token exchange failed ({resp.status}): {body[:500]}"
                )
            token_response = await resp.json()

    credentials = _from_token_response(token_response)
    save_credentials(credentials)
    print(
        f"Login successful ({credentials.email or 'unknown account'}). "
        f"Credentials saved to {FLE_CREDENTIALS_FILE}"
    )
    return credentials
