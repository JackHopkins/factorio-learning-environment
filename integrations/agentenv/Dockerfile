# This recipe references the upstream Factorio headless image but does not
# contain Factorio binaries in the repository. Keep built images private unless
# Wube and the upstream image terms explicitly permit redistribution.
FROM factoriotools/factorio:2.0.73 AS factorio

FROM python:3.12-slim-bookworm

RUN useradd --create-home --uid 1000 factorio

COPY --from=factorio /opt/factorio /opt/factorio
WORKDIR /workspace/fle
COPY . /workspace/fle
COPY fle/cluster/scenarios /opt/factorio/scenarios
COPY fle/cluster/config /opt/factorio/config
COPY fle/cluster/mods /opt/factorio/mods
COPY integrations/agentenv/entrypoint.sh /usr/local/bin/factorio-agentenv-entrypoint

RUN pip install --no-cache-dir .

# The upstream image links /opt/factorio/saves to /factorio/saves. COPY
# preserves that link but not the external directory, so recreate the writable
# runtime layout instead of trying to mkdir through a dangling symlink.
RUN chmod 0755 /usr/local/bin/factorio-agentenv-entrypoint \
    && mkdir -p /factorio/saves /factorio/script-output \
    && ln -s /factorio/script-output /opt/factorio/script-output \
    && chown -R factorio:factorio /factorio /opt/factorio /workspace/fle

USER factorio
EXPOSE 8172
ENTRYPOINT ["/usr/local/bin/factorio-agentenv-entrypoint"]
