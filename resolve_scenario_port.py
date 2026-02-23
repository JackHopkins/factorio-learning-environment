#!/usr/bin/env python3
"""Resolve a running Factorio TCP port by built-in scenario profile.

Supported scenario profiles:
- default_lab_scenario
- open_world
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from factorio_rcon import RCONClient

SUPPORTED_PROFILES = {"default_lab_scenario", "open_world"}


@dataclass
class Probe:
    port: int
    container: Optional[str]
    raw: str
    parsed: Dict[str, str]
    classified_profile: Optional[str]
    error: Optional[str]


def parse_ports(spec: str) -> List[int]:
    ports: List[int] = []
    for chunk in spec.split(","):
        token = chunk.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            left, right = int(a.strip()), int(b.strip())
            if right < left:
                left, right = right, left
            ports.extend(range(left, right + 1))
        else:
            ports.append(int(token))
    return ports


def discover_factorio_port_map() -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        for name in names:
            if "factorio" not in name.lower():
                continue
            inspect = subprocess.run(
                ["docker", "inspect", name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if inspect.returncode != 0 or not inspect.stdout.strip():
                continue
            info = json.loads(inspect.stdout)[0]
            ports = info.get("NetworkSettings", {}).get("Ports", {})
            for port_spec, bindings in ports.items():
                if not port_spec.endswith("/tcp") or not bindings:
                    continue
                for binding in bindings:
                    host_port = binding.get("HostPort")
                    if host_port:
                        mapping[int(host_port)] = name
    except Exception:
        return {}
    return mapping


def probe_command(resource_radius: int, water_radius: int) -> str:
    return (
        "/sc "
        "local p=game.players[1]; local s=game.surfaces[1]; "
        "local x,y=0,0; if p then x,y=p.position.x,p.position.y end; "
        f"local res_radius={resource_radius}; local water_radius={water_radius}; "
        "local names={'iron-ore','copper-ore','coal','stone','crude-oil'}; "
        "local out={'player@'..string.format('%.1f',x)..','..string.format('%.1f',y)}; "
        "for _,name in pairs(names) do "
        "  local ents=s.find_entities_filtered{position={x,y}, radius=res_radius, name=name}; "
        "  local best=nil; local bd=1e18; "
        "  for _,e in pairs(ents) do "
        "    local dx=e.position.x-x; local dy=e.position.y-y; local d=dx*dx+dy*dy; "
        "    if d<bd then bd=d; best=e end "
        "  end; "
        "  if best then "
        "    table.insert(out, name..'@'..string.format('%.1f',best.position.x)..','..string.format('%.1f',best.position.y)..':'..string.format('%.1f', math.sqrt(bd))) "
        "  else "
        "    table.insert(out, name..'@none') "
        "  end "
        "end; "
        "local wt=s.find_tiles_filtered{"
        "  area={{x-water_radius,y-water_radius},{x+water_radius,y+water_radius}}, "
        "  name={'water','deepwater','water-green','deepwater-green','water-shallow'}, "
        "  limit=1"
        "}; "
        "if #wt>0 then "
        "  local wp=wt[1].position; table.insert(out, 'water_tile@'..string.format('%.1f',wp.x)..','..string.format('%.1f',wp.y)) "
        "else "
        "  table.insert(out, 'water_tile@none') "
        "end; "
        "rcon.print(table.concat(out,'|'))"
    )


def parse_probe(raw: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for token in (raw or "").split("|"):
        if "@" not in token:
            continue
        key, value = token.split("@", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def classify_profile(parsed: Dict[str, str]) -> Optional[str]:
    required_common = ("iron-ore", "copper-ore", "coal", "stone")
    if any(parsed.get(name, "none").startswith("none") for name in required_common):
        return None
    if parsed.get("water_tile", "none").startswith("none"):
        return None
    has_crude = not parsed.get("crude-oil", "none").startswith("none")
    return "open_world" if has_crude else "default_lab_scenario"


def probe_port(address: str, port: int, password: str, timeout: float, container: Optional[str]) -> Probe:
    raw = ""
    parsed: Dict[str, str] = {}
    try:
        client = RCONClient(address, port, password, timeout=timeout, connect_on_init=False)
        client.connect()
        raw = client.send_command(probe_command(resource_radius=600, water_radius=1200)) or ""
        parsed = parse_probe(raw)
        client.close()
        profile = classify_profile(parsed)
        return Probe(
            port=port,
            container=container,
            raw=raw,
            parsed=parsed,
            classified_profile=profile,
            error=None,
        )
    except Exception as exc:
        return Probe(
            port=port,
            container=container,
            raw=raw,
            parsed=parsed,
            classified_profile=None,
            error=str(exc),
        )


def port_priority(port: int) -> tuple[int, int]:
    in_reserved_block = 41000 <= port <= 41009
    return (0 if in_reserved_block else 1, port)


def parse_args():
    parser = argparse.ArgumentParser(description="Resolve running Factorio port by scenario profile.")
    parser.add_argument("--profile", required=True, choices=sorted(SUPPORTED_PROFILES))
    parser.add_argument("--address", default="127.0.0.1")
    parser.add_argument("--password", default="factorio")
    parser.add_argument("--ports", default="")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--output", choices=("port", "json"), default="port")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping = discover_factorio_port_map()

    if args.ports:
        candidates = parse_ports(args.ports)
    else:
        candidates = sorted(mapping.keys(), key=port_priority)

    # Preserve order and drop dupes.
    seen = set()
    ordered: List[int] = []
    for port in candidates:
        if port in seen:
            continue
        seen.add(port)
        ordered.append(port)

    if not ordered:
        print("ERROR: no candidate ports available to probe", file=sys.stderr)
        return 2

    probes: List[Probe] = [
        probe_port(
            address=args.address,
            port=port,
            password=args.password,
            timeout=args.timeout,
            container=mapping.get(port),
        )
        for port in ordered
    ]

    matches = [p for p in probes if p.classified_profile == args.profile]
    matches.sort(key=lambda p: port_priority(p.port))

    if not matches:
        print(f"ERROR: no running server matches scenario profile '{args.profile}'", file=sys.stderr)
        for p in probes:
            if p.error:
                print(f"  tcp/{p.port}: error={p.error}", file=sys.stderr)
            else:
                print(f"  tcp/{p.port}: profile={p.classified_profile or 'unknown'} probe={p.raw}", file=sys.stderr)
        return 3

    selected = matches[0]
    if args.output == "port":
        print(selected.port)
    else:
        payload = {
            "selected_port": selected.port,
            "selected_profile": selected.classified_profile,
            "selected_container": selected.container,
            "probes": [
                {
                    "port": p.port,
                    "container": p.container,
                    "profile": p.classified_profile,
                    "error": p.error,
                    "raw_probe": p.raw,
                }
                for p in probes
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    if args.verbose:
        print(
            f"Resolved profile {args.profile} -> tcp/{selected.port} ({selected.container or 'unknown'})",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

