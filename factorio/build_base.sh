aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin 216370203482.dkr.ecr.eu-west-2.amazonaws.com

docker context use default
docker build . -t 216370203482.dkr.ecr.eu-west-2.amazonaws.com/factorio
docker tag factorio 216370203482.dkr.ecr.eu-west-2.amazonaws.com/factorio
docker push 216370203482.dkr.ecr.eu-west-2.amazonaws.com/factorio