export IMAGE_URL=factoriotools/factorio:latest
docker pull $IMAGE_URL
docker create --name temp_container $IMAGE_URL
#docker exec -it temp_container mkdir factorio/config
docker cp config temp_container:/factorio
docker cp config/server-settings.json temp_container:/opt/factorio/data/server-settings.example.json
docker cp config/rconpw temp_container:/opt/factorio/rconpw

docker exec temp_container cat /opt/factorio/rconpw

docker commit temp_container 216370203482.dkr.ecr.eu-west-2.amazonaws.com/factorio:configured
#docker tag temp_container 216370203482.dkr.ecr.eu-west-2.amazonaws.com/factorio
docker push 216370203482.dkr.ecr.eu-west-2.amazonaws.com/factorio

#docker run -p 27015:27015/tcp temp_container

#docker rm temp_container
docker run -p 27015:27015/tcp 216370203482.dkr.ecr.eu-west-2.amazonaws.com/factorio