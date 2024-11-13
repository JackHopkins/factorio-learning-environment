# This has has different mod location
docker build -t factorio .

cd mods
tar -czf headless-player_0.1.0.tgz headless-player_0.1.0
tar -czf stdlib_1.4.6.tgz stdlib_1.4.6

mv stdlib_1.4.6.tgz ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6.tgz
mv headless-player_0.1.0.tgz ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0.tgz

rm -rf ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6
rm -rf ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0

cp -rf stdlib_1.4.6 ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6
cp -rf headless-player_0.1.0 ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0

cd ..

cp config/mod-list.json ~/Applications/Factorio.app/Contents/Resources/mods/mod-list.json