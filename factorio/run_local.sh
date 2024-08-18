docker run -d \
  -p 34197:34197/udp \
  -p 27015:27015/tcp \
  --name=factorio \
  --restart=always \
  -it factorio