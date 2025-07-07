#ssh -i "factorio.pem" ec2-user@ec2-18-133-239-115.eu-west-2.compute.amazonaws.com

# Setup
sudo yum update -y
sudo amazon-linux-extras install docker -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Docker
sudo mkdir -p /opt/factorio
sudo chown 845:845 /opt/factorio
sudo docker run -d \
  -p 34197:34197/udp \
  -p 27015:27015/tcp \
  -v /opt/factorio:/factorio \
  --name factorio \
  --restart=always \
  factoriotools/factorio

sudo docker logs factorio
sudo docker stop factorio

nano /opt/factorio/config/server-settings.json