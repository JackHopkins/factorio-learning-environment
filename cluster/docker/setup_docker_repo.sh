aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin 216370203482.dkr.ecr.eu-west-2.amazonaws.com
aws ecr create-repository --repository-name factorio

#public.ecr.aws/y5j3i3w6/raveler

#docker login --username AWS --password-stdin public.ecr.aws/y5j3i3w6/paperclip_client:latest
#docker tag hello-world public.ecr.aws/y5j3i3w6/paperclip_client:latest
#docker push public.ecr.aws/y5j3i3w6/paperclip_client

#docker tag hello-world 216370203482.dkr.ecr.eu-west-2.amazonaws.com/hello-world
#docker push 216370203482.dkr.ecr.eu-west-2.amazonaws.com/hello-world #public.ecr.aws/y5j3i3w6/paperclip_client

#216370203482.dkr.ecr.eu-west-2.amazonaws.com/hello-world