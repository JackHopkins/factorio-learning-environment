FROM --platform=linux/amd64 factoriotools/factorio:1.1.110
#--platform=linux/amd64/v2

COPY config /opt/factorio/config
COPY config /factorio/config
COPY mods /opt/factorio/mods
COPY config/scenario.sh /opt/factorio/scenario.sh


# Open ports:
#      - '34197:34197/udp'
#      - '27015:27015/tcp'

# Expose ports
EXPOSE 34197/udp
EXPOSE 27015/tcp


RUN chmod +x /opt/factorio/scenario.sh  # Fix the chmod path
ENTRYPOINT ["/opt/factorio/scenario.sh"]