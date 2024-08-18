FROM --platform=linux/amd64 factoriotools/factorio:1.1.107

ARG CACHEBUST=4

COPY config /factorio/config

COPY mods factorio/mods

# Open ports:
#      - '34197:34197/udp'
#      - '27015:27015/tcp'

# Expose ports
EXPOSE 34197/udp
EXPOSE 27015/tcp

RUN ["chmod", "+x", "/scenario.sh"]