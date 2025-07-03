# Build

To build the Headless Factorio docker image and upload the mods to your local Factorio installation:
```
sh factorio/run.sh
```

If you don't care about mods, you can simply run:
```
docker build -t factorio .
```

and then
```
docker run -d \
  -p 34197:34197/udp \
  -p 27015:27015/tcp \
  factorio
```

Note: You should provide your own location for installation files.

