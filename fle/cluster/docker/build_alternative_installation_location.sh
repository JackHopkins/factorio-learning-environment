# This has has different mod location
docker build -t factorio . --platform linux/amd64

cd mods
tar -czf headless-player_0.1.0.tgz headless-player_0.1.0
tar -czf stdlib_1.4.6.tgz stdlib_1.4.6

mv stdlib_1.4.6.tgz ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6.tgz
mv headless-player_0.1.0.tgz ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0.tgz

# unzip
# cd ~/Applications/Factorio.app/Contents/Resources/mods


# remove old files
rm -rf ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6
rm -rf ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0

# untar files
#tar -xzf ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6.tgz
#tar -xzf ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0.tgz

# move files to mods directory
cp -rf stdlib_1.4.6 ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6
cp -rf headless-player_0.1.0 ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0

#rm -rf ~/Applications/Factorio.app/Contents/Resources/mods/stdlib_1.4.6.tgz
#rm -rf ~/Applications/Factorio.app/Contents/Resources/mods/headless-player_0.1.0.tgz

cd ..

cp config/mod-list.json ~/Applications/Factorio.app/Contents/Resources/mods/mod-list.json