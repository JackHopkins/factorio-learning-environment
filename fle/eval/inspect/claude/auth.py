"""OAuth (PKCE) credentials for Claude Pro/Max subscriptions.

Authenticates with a Claude Pro/Max subscription using the same OAuth client
as Claude Code. Credentials are resolved from, in order:

1. FLE's own credential file (``~/.fle/claude_auth.json``)
2. Claude Code (``~/.claude/.credentials.json``, created by ``claude`` login)

Anthropic rotates the refresh token on use, so refreshed tokens are written
back to the file they came from (in that file's own schema) as well as to
FLE's own file -- otherwise refreshing borrowed credentials would silently
log Claude Code out.
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
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

log = logging.getLogger(__name__)

# OAuth client used by Claude Code (public client, PKCE).
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CALLBACK_PORT = 53692
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"
SCOPES = (
    "org:create_api_key user:profile user:inference "
    "user:sessions:claude_code user:mcp_servers user:file_upload"
)

FLE_CREDENTIALS_FILE = Path.home() / ".fle" / "claude_auth.json"
CLAUDE_CODE_CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"


class ClaudeAuthError(RuntimeError):
    """Raised when Claude OAuth credentials are missing or unusable."""


@dataclass
class ClaudeCredentials:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: float = 0.0
    scopes: list[str] = field(default_factory=list)
    subscription_type: Optional[str] = None
    source: str = "fle"
    origin: Optional[Path] = None

    def is_expired(self, margin: float = 60.0) -> bool:
        return time.time() >= self.expires_at - margin

    def to_dict(self, include_provenance: bool = False) -> dict[str, Any]:
        payload = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "scopes": self.scopes,
            "subscription_type": self.subscription_type,
        }
        if include_provenance:
            # Only FLE's own file records provenance; without it a reload
            # would forget the true origin after the first refresh and stop
            # writing rotated tokens back (logging Claude Code out).
            payload["source"] = self.source
            payload["origin"] = str(self.origin) if self.origin else None
        return payload


def _from_token_response(
    token_response: dict[str, Any], previous: Optional[ClaudeCredentials] = None
) -> ClaudeCredentials:
    scope = token_response.get("scope")
    return ClaudeCredentials(
        access_token=token_response["access_token"],
        refresh_token=token_response.get("refresh_token")
        or (previous.refresh_token if previous else None),
        expires_at=time.time() + float(token_response.get("expires_in", 3600)),
        scopes=scope.split() if isinstance(scope, str) else (previous.scopes if previous else []),
        subscription_type=previous.subscription_type if previous else None,
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
    credentials: ClaudeCredentials, path: Path = FLE_CREDENTIALS_FILE
) -> None:
    _atomic_write_json(path, credentials.to_dict(include_provenance=True))


def _write_back_to_origin(credentials: ClaudeCredentials) -> None:
    """Update the file the credentials were loaded from with the rotated tokens.

    Anthropic rotates the refresh token on every use, so refreshing Claude
    Code's credentials invalidates the copy Claude Code still holds --
    silently logging it out. Write the new pair back in that file's own
    schema (preserving unknown keys) so borrowing credentials stays
    non-destructive.
    """
    origin = credentials.origin
    if origin is None or origin == FLE_CREDENTIALS_FILE:
        return
    existing = _load_json(origin)
    if existing is None:
        return
    if credentials.source == "claude-code":
        oauth = existing.setdefault("claudeAiOauth", {})
        oauth["accessToken"] = credentials.access_token
        oauth["refreshToken"] = credentials.refresh_token
        oauth["expiresAt"] = int(credentials.expires_at * 1000)
        if credentials.scopes:
            oauth["scopes"] = credentials.scopes
    else:
        existing.update(credentials.to_dict())
    try:
        _atomic_write_json(origin, existing)
    except OSError as exc:
        log.warning(
            "Could not write refreshed Claude tokens back to %s: %s", origin, exc
        )


def persist_credentials(credentials: ClaudeCredentials) -> None:
    """Persist to FLE's own store and back to the file the tokens came from."""
    save_credentials(credentials)
    _write_back_to_origin(credentials)


def _load_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def load_credentials() -> Optional[ClaudeCredentials]:
    """Load credentials from the first usable source."""
    data = _load_json(FLE_CREDENTIALS_FILE)
    if data and data.get("access_token"):
        # Restore the provenance recorded by save_credentials() so tokens
        # borrowed from Claude Code keep being written back to its file
        # across refreshes, not just the first one.
        origin_str = data.get("origin")
        return ClaudeCredentials(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=float(data.get("expires_at") or 0.0),
            scopes=data.get("scopes") or [],
            subscription_type=data.get("subscription_type"),
            source=data.get("source") or "fle",
            origin=Path(origin_str) if origin_str else FLE_CREDENTIALS_FILE,
        )

    # Claude Code: {"claudeAiOauth": {"accessToken", "refreshToken",
    # "expiresAt" (ms), "scopes", "subscriptionType", ...}}
    data = _load_json(CLAUDE_CODE_CREDENTIALS_FILE)
    oauth = (data or {}).get("claudeAiOauth") or {}
    if oauth.get("accessToken"):
        return ClaudeCredentials(
            access_token=oauth["accessToken"],
            refresh_token=oauth.get("refreshToken"),
            expires_at=float(oauth.get("expiresAt") or 0.0) / 1000.0,
            scopes=oauth.get("scopes") or [],
            subscription_type=oauth.get("subscriptionType"),
            source="claude-code",
            origin=CLAUDE_CODE_CREDENTIALS_FILE,
        )

    return None


async def refresh_credentials(credentials: ClaudeCredentials) -> ClaudeCredentials:
    if not credentials.refresh_token:
        raise ClaudeAuthError(
            "Claude access token expired and no refresh token is available. "
            "Run 'fle claude login'."
        )
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": credentials.refresh_token,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(TOKEN_URL, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise ClaudeAuthError(
                    f"Claude token refresh failed ({resp.status}): {body[:500]}. "
                    "Run 'fle claude login' to re-authenticate."
                )
            token_response = await resp.json()
    refreshed = _from_token_response(token_response, previous=credentials)
    persist_credentials(refreshed)
    return refreshed


async def ensure_credentials() -> ClaudeCredentials:
    """Load credentials, refreshing if expired. Raises ClaudeAuthError if absent."""
    credentials = load_credentials()
    if credentials is None:
        raise ClaudeAuthError(
            "No Claude credentials found. Run 'fle claude login' "
            "(or log in to Claude Code to reuse its credentials)."
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


async def login() -> ClaudeCredentials:
    """Run the OAuth PKCE login flow in a browser and persist credentials."""
    verifier = secrets.token_urlsafe(64)[:128]
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    # Like Claude Code, the PKCE verifier doubles as the OAuth state; the
    # token endpoint validates it as part of the code exchange.
    state = verifier

    _CallbackHandler.auth_code = None
    _CallbackHandler.error = None
    _CallbackHandler.expected_state = state
    _CallbackHandler.received = Event()
    try:
        server = _CallbackServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise ClaudeAuthError(
                f"OAuth callback port {CALLBACK_PORT} is already in use "
                "(is another login flow running?)"
            ) from exc
        raise

    params = urlencode(
        {
            "code": "true",
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
    )
    auth_url = f"{AUTHORIZE_URL}?{params}"
    print(f"Opening browser for Claude login...\n  {auth_url}")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        if not _CallbackHandler.received.wait(timeout=180):
            raise ClaudeAuthError("OAuth callback timed out")
        if _CallbackHandler.error:
            raise ClaudeAuthError(f"OAuth error: {_CallbackHandler.error}")
        code = _CallbackHandler.auth_code
        if not code:
            raise ClaudeAuthError("No authorization code received")
    finally:
        server.shutdown()
        server.server_close()

    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "state": state,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(TOKEN_URL, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise ClaudeAuthError(
                    f"Token exchange failed ({resp.status}): {body[:500]}"
                )
            token_response = await resp.json()

    credentials = _from_token_response(token_response)
    save_credentials(credentials)
    print(
        f"Login successful ({credentials.subscription_type or 'unknown plan'}). "
        f"Credentials saved to {FLE_CREDENTIALS_FILE}"
    )
    return credentials
