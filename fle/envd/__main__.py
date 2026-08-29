import argparse
import os
import platform

import uvicorn

from fle.envd.api import build_live_service, create_agentenv_app, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Factorio environment service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8172)
    parser.add_argument("--factorio-address", default="localhost")
    parser.add_argument("--rcon-ports", default="27000")
    parser.add_argument(
        "--audit-rcon-ports",
        default=os.getenv("FLE_AUDIT_RCON_PORTS", ""),
        help="Comma-separated reserved Factorio ports used only for cloned audits",
    )
    parser.add_argument(
        "--lease-ttl",
        type=int,
        default=int(
            os.getenv(
                "FLE_LEASE_TTL",
                "86400" if os.getenv("AENV_TEMPLATE_ID") else "900",
            )
        ),
    )
    parser.add_argument(
        "--runtime",
        choices=["auto", "local", "agentenv"],
        default=os.getenv("FLE_ENVD_RUNTIME", "auto"),
        help=(
            "local uses the Docker/FLE RCON pool; agentenv creates one isolated "
            "microVM per lease; auto selects AgentENV when AENV_TEMPLATE_ID is set"
        ),
    )
    parser.add_argument(
        "--agentenv-api-url",
        default=os.getenv("AENV_API_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--agentenv-api-key",
        default=os.getenv("AENV_API_KEY", "dummy"),
    )
    parser.add_argument(
        "--agentenv-template-id",
        default=os.getenv("AENV_TEMPLATE_ID"),
    )
    parser.add_argument(
        "--agentenv-capacity",
        type=int,
        default=int(os.getenv("AENV_FACTORIO_CAPACITY", "64")),
    )
    parser.add_argument(
        "--agentenv-guest-envd-port",
        type=int,
        default=int(os.getenv("AENV_GUEST_ENVD_PORT", "8172")),
    )
    parser.add_argument(
        "--agentenv-sandbox-timeout",
        type=int,
        default=int(os.getenv("AENV_SANDBOX_TIMEOUT", "1800")),
    )
    parser.add_argument(
        "--agentenv-startup-timeout",
        type=float,
        default=float(os.getenv("AENV_STARTUP_TIMEOUT", "180")),
    )
    args = parser.parse_args()

    runtime = args.runtime
    if runtime == "auto":
        runtime = "agentenv" if args.agentenv_template_id else "local"
    if runtime == "agentenv":
        if not args.agentenv_template_id:
            parser.error(
                "--agentenv-template-id or AENV_TEMPLATE_ID is required for "
                "the AgentENV runtime"
            )
        from fle.envd.agentenv import AgentEnvConfig, AgentEnvEnvironmentGateway

        config = AgentEnvConfig(
            api_url=args.agentenv_api_url,
            api_key=args.agentenv_api_key,
            template_id=args.agentenv_template_id,
            guest_envd_port=args.agentenv_guest_envd_port,
            capacity=args.agentenv_capacity,
            sandbox_timeout_seconds=args.agentenv_sandbox_timeout,
            lease_ttl_seconds=args.lease_ttl,
            startup_timeout_seconds=args.agentenv_startup_timeout,
        )
        service = AgentEnvEnvironmentGateway(config)
        uvicorn.run(
            create_agentenv_app(service),
            host=args.host,
            port=args.port,
            workers=1,
        )
        return

    if platform.system() != "Windows" and args.runtime == "auto":
        print(
            "AENV_TEMPLATE_ID is not set; using the local Docker/FLE runtime.",
            flush=True,
        )
    ports = [
        int(value.strip()) for value in args.rcon_ports.split(",") if value.strip()
    ]
    audit_ports = [
        int(value.strip())
        for value in args.audit_rcon_ports.split(",")
        if value.strip()
    ]
    if set(ports) & set(audit_ports):
        parser.error("--rcon-ports and --audit-rcon-ports must be disjoint")
    service = build_live_service(
        ports,
        address=args.factorio_address,
        lease_ttl_seconds=args.lease_ttl,
        audit_tcp_ports=audit_ports,
    )
    uvicorn.run(create_app(service), host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    main()
