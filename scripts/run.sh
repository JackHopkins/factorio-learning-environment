#!/bin/bash

# Check if Docker is running, if not start it
if ! docker info >/dev/null 2>&1; then
    echo "Starting Docker..."
    # On Mac, Docker Desktop runs as an app. So, open the Docker app.
    open -a Docker
    # Wait until Docker daemon is running
    while ! docker info >/dev/null 2>&1; do
        sleep 1
    done
fi
echo "Docker is running."

# Check if docker-compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo "Error: docker-compose is not installed."
    echo "Please install docker-compose and try again."
    exit 1
fi

cd ../src
# Check for the existence of the docker-compose file
DOCKER_COMPOSE_FILE="./docker-compose.yml"
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    DOCKER_COMPOSE_FILE="../docker-compose.yml"
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        echo "Error: docker-compose.yml not found in the current directory or one level up."
        exit 1
    fi
fi

# Check if the Factorio game client is running
FACTORIO_CLIENT_APP="Factorio.app"
if ! pgrep -f "$FACTORIO_CLIENT_APP" > /dev/null; then
    echo "Starting Factorio game client..."
    open -a "$FACTORIO_CLIENT_APP"
else
    echo "Factorio game client is already running."
fi


# Extract UDP ports from the docker-compose.yml file
UDP_PORTS=$(grep -E "^[ \t]*- '[0-9]+:.*udp'" $DOCKER_COMPOSE_FILE | grep -oE "[0-9]+" | head -n 1)

# Run the Factorio server docker container using the found docker-compose file
echo "Starting Factorio server docker container(s)..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d


echo "Go to 'Multiplayer' > 'Connect to address' and login to the Factorio servers using the following addresses (one at a time):"

# Prompt the user to login to the Factorio server using the extracted ports
for port in $UDP_PORTS; do
    echo "localhost:$port"
done

sleep 4

# Bring Factorio game client to focus
osascript -e 'tell application "Factorio" to activate'