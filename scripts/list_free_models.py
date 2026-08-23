"""List currently free chat models on OpenRouter.

Free-route model IDs churn; never hardcode them in run recipes. This helper
queries the public /models endpoint and prints the ones whose prompt and
completion pricing are both zero, with context length and modality, so
`fle-benchmark --model <id>` arguments come from live data.

Usage:
    python scripts/list_free_models.py [--min-context 8192] [--provider x]
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-context", type=int, default=8192)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers=(
            {"Authorization": f"Bearer {os.environ['OPEN_ROUTER_API_KEY']}"}
            if os.environ.get("OPEN_ROUTER_API_KEY")
            else {}
        ),
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    rows = []
    for model in payload.get("data", []):
        pricing = model.get("pricing") or {}
        try:
            free = (
                float(pricing.get("prompt", "1")) == 0.0
                and float(pricing.get("completion", "1")) == 0.0
            )
        except (TypeError, ValueError):
            free = False
        if not free and not str(model.get("id", "")).endswith(":free"):
            continue
        context_length = int(model.get("context_length") or 0)
        if context_length < args.min_context:
            continue
        if args.provider and args.provider not in str(model.get("id", "")):
            continue
        rows.append(
            (
                model["id"],
                context_length,
                model.get("name", ""),
                ", ".join(model.get("supported_parameters", [])[:1]) or "",
            )
        )

    rows.sort(key=lambda row: (-row[1], row[0]))
    print(f"free models (context >= {args.min_context}): {len(rows)}")
    for model_id, context_length, name, _ in rows:
        print(f"{model_id:<55} {context_length:>9,d}  {name}")


if __name__ == "__main__":
    main()
