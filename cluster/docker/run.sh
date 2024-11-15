docker build -t factorio .

cd mods
tar -czf headless-player_0.1.0.tgz headless-player_0.1.0
tar -czf stdlib_1.4.6.tgz stdlib_1.4.6

mv stdlib_1.4.6.tgz ~/Library/Application\ Support/Factorio/mods/stdlib_1.4.6.tgz
mv headless-player_0.1.0.tgz ~/Library/Application\ Support/Factorio/mods/headless-player_0.1.0.tgz

rm -rf ~/Library/Application\ Support/Factorio/mods/stdlib_1.4.6
rm -rf ~/Library/Application\ Support/Factorio/mods/headless-player_0.1.0

cp -rf stdlib_1.4.6 ~/Library/Application\ Support/Factorio/mods/stdlib_1.4.6
cp -rf headless-player_0.1.0 ~/Library/Application\ Support/Factorio/mods/headless-player_0.1.0

cd ..

cp config/mod-list.json ~/Library/Application\ Support/Factorio/mods/mod-list.json

docker run -d \
  -p 34197:34197/udp \
  -p 27015:27015/tcp \
  factorio