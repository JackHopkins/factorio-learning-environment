import docker

client = docker.from_env()

container = client.containers.run(
    "factorio",
    {"34197/udp": 34197, "27015/tcp": 27000},
    platform="linux/amd64",
    detach=True,
)

print(container.logs())
