import argparse

import uvicorn

from fle.envd.api import build_live_service, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Factorio environment service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8172)
    parser.add_argument("--factorio-address", default="localhost")
    parser.add_argument("--rcon-ports", default="27000")
    parser.add_argument("--lease-ttl", type=int, default=900)
    args = parser.parse_args()

    ports = [
        int(value.strip()) for value in args.rcon_ports.split(",") if value.strip()
    ]
    service = build_live_service(
        ports,
        address=args.factorio_address,
        lease_ttl_seconds=args.lease_ttl,
    )
    uvicorn.run(create_app(service), host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    main()
