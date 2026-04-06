# =============================================================================
# Stage 1: Build FLE wheel from source
# =============================================================================
FROM python:3.12-slim AS fle-builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY fle/ fle/

RUN pip install --no-cache-dir build \
    && python -m build --wheel --outdir /build/dist

# =============================================================================
# Stage 2: Runtime image based on Factorio server
# =============================================================================
FROM factoriotools/factorio:2.0.73

USER root

# Install Python 3.12, pip, supervisor, and build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        supervisor gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/fle-venv
ENV PATH="/opt/fle-venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/fle-venv"

# Install FLE wheel and dependencies
COPY --from=fle-builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# --- Copy FLE assets into fixed container paths ---

# FLE Lua mods and tools (used by FactorioInstance via FLE_MODS_DIR / FLE_TOOLS_DIR)
COPY fle/env/mods/ /opt/fle/mods/
COPY fle/env/tools/ /opt/fle/tools/

# Bridge scripts
COPY fle/eval/inspect/sandbox/bridge_service.py /opt/fle/bridge_service.py
COPY fle/eval/inspect/sandbox/bridge_client.py /opt/fle/bridge_client.py

# Factorio scenarios
COPY fle/cluster/scenarios/ /opt/factorio/scenarios/

# Factorio server config
COPY fle/cluster/config/ /opt/factorio/config/

# Factorio mod-list (disables DLC mods)
COPY fle/cluster/mods/ /opt/factorio/mods/

# Create empty ban/whitelist files if they don't exist
RUN touch /opt/factorio/config/server-banlist.json \
    && touch /opt/factorio/config/server-whitelist.json \
    && echo '[]' > /opt/factorio/config/server-banlist.json \
    && echo '[]' > /opt/factorio/config/server-whitelist.json

# Remove DLC data directories so the server runs vanilla base-game only
RUN rm -rf /opt/factorio/data/elevated-rails \
           /opt/factorio/data/quality \
           /opt/factorio/data/space-age

# --- Supervisor configuration ---
COPY fle/eval/inspect/sandbox/supervisord.conf /etc/supervisor/conf.d/fle.conf

# --- Entrypoint ---
COPY fle/eval/inspect/sandbox/entrypoint.sh /opt/fle/entrypoint.sh
RUN chmod +x /opt/fle/entrypoint.sh

# Environment variables for FLE path resolution
ENV FLE_MODS_DIR="/opt/fle/mods"
ENV FLE_TOOLS_DIR="/opt/fle/tools"
ENV FLE_SCENARIO="default_lab_scenario"
ENV FLE_ENV_ID="iron_ore_throughput"
ENV FLE_NUM_AGENTS="1"

ENTRYPOINT ["/opt/fle/entrypoint.sh"]
