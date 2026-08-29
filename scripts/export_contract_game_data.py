"""Export authoritative prototypes for privileged benchmark setup over RCON.

This utility uses Factorio's runtime scripting API and must never be exposed as
an agent tool. Agents use the public recipe/research actions instead.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from factorio_rcon import RCONClient


def _lua_string(value: str) -> str:
    return json.dumps(value)


def _json_command(client: RCONClient, source: str) -> Any:
    response = client.send_command("/sc " + source)
    try:
        return json.loads(response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Factorio returned non-JSON {response!r} for Lua: {source}"
        ) from exc


def _empty_table_as_list(value: Any) -> Any:
    return [] if isinstance(value, dict) and not value else value


def export_game_data(host: str, port: int, password: str) -> dict[str, Any]:
    client = RCONClient(host, port, password)
    client.connect()
    try:
        version = _json_command(
            client,
            "rcon.print(helpers.table_to_json({"
            "factorio_version=script.active_mods['base']}))",
        )["factorio_version"]
        recipe_names = _json_command(
            client,
            "local o={} for n,_ in pairs(prototypes.recipe) do "
            "table.insert(o,n) end table.sort(o) "
            "rcon.print(helpers.table_to_json(o))",
        )
        technology_names = _json_command(
            client,
            "local o={} for n,_ in pairs(prototypes.technology) do "
            "table.insert(o,n) end table.sort(o) "
            "rcon.print(helpers.table_to_json(o))",
        )

        recipes = []
        for name in recipe_names:
            quoted = _lua_string(name)
            recipe = _json_command(
                client,
                "local r=prototypes.recipe["
                + quoted
                + "] local i={} local p={} "
                "for _,v in pairs(r.ingredients) do table.insert(i,{"
                "name=v.name,amount=v.amount,type=v.type}) end "
                "for _,v in pairs(r.products) do local a=v.amount "
                "or ((v.amount_min or 0)+(v.amount_max or 0))/2 "
                "* (v.probability or 1) table.insert(p,{name=v.name,"
                "amount=a,type=v.type}) end "
                "rcon.print(helpers.table_to_json({name=r.name,"
                "category=r.category,energy=r.energy,enabled=r.enabled,"
                "ingredients=i,products=p}))",
            )
            recipe["ingredients"] = _empty_table_as_list(recipe.get("ingredients"))
            recipe["products"] = _empty_table_as_list(recipe.get("products"))
            recipes.append(recipe)

        technologies = []
        for name in technology_names:
            quoted = _lua_string(name)
            technology = _json_command(
                client,
                "local t=prototypes.technology["
                + quoted
                + "] local p={} local u={} "
                "for n,_ in pairs(t.prerequisites) do table.insert(p,n) end "
                "for _,e in pairs(t.effects) do if e.type=='unlock-recipe' "
                "then table.insert(u,e.recipe) end end table.sort(p) "
                "table.sort(u) local count=t.research_unit_count "
                "if type(count)~='number' then count=1 end "
                "rcon.print(helpers.table_to_json({name=t.name,"
                "prerequisites=p,unlocked_recipes=u,unit_count=count,"
                "unit_energy=t.research_unit_energy}))",
            )
            technology["prerequisites"] = _empty_table_as_list(
                technology.get("prerequisites")
            )
            technology["unlocked_recipes"] = _empty_table_as_list(
                technology.get("unlocked_recipes")
            )
            technologies.append(technology)
        # Prototype metadata is kept separate from recipes so lookup tools can
        # answer machine/prototype questions without asking the agent to infer
        # them from a category string.  Only stable, serializable fields are
        # exported; field access is guarded because not every entity prototype
        # exposes every machine property.
        prototypes = _json_command(
            client,
            "local o={} for n,e in pairs(prototypes.entity) do "
            "local categories={} local ok,cats=pcall(function() return e.crafting_categories end) "
            "if ok and cats then for c,_ in pairs(cats) do table.insert(categories,c) end end "
            "table.sort(categories) local energy=nil local eok,ev=pcall(function() return e.energy_usage end) "
            "if eok then energy=ev end table.insert(o,{name=e.name,type=e.type,crafting_categories=categories,energy_usage=energy}) "
            "end table.sort(o,function(a,b) return a.name<b.name end) "
            "rcon.print(helpers.table_to_json(o))",
        )
        prototypes = _empty_table_as_list(prototypes)
        return {
            "factorio_version": version,
            "recipes": recipes,
            "technologies": technologies,
            "prototypes": prototypes,
        }
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=27000)
    parser.add_argument("--password", default="factorio")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = export_game_data(args.host, args.port, args.password)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {len(payload['recipes'])} recipes and "
        f"{len(payload['technologies'])} technologies to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
