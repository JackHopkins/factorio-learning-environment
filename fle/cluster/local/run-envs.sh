#!/bin/bash

# Function to detect and set host architecture
setup_platform() {
    ARCH=$(uname -m)
    OS=$(uname -s)
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        export DOCKER_PLATFORM="linux/arm64"
    else
        export DOCKER_PLATFORM="linux/amd64"
    fi
    # Detect OS for mods path
    if [[ "$OS" == *"MINGW"* ]] || [[ "$OS" == *"MSYS"* ]] || [[ "$OS" == *"CYGWIN"* ]]; then
        # Windows detected
        export OS_TYPE="windows"
        # Use %APPDATA% which is available in Windows bash environments
        export MODS_PATH="${APPDATA}/Factorio/mods"
        # Fallback if APPDATA isn't available
        if [ -z "$MODS_PATH" ] || [ "$MODS_PATH" == "/Factorio/mods" ]; then
            export MODS_PATH="${USERPROFILE}/AppData/Roaming/Factorio/mods"
        fi
    else
        # Assume Unix-like OS (Linux, macOS)
        export OS_TYPE="unix"
        export MODS_PATH="~/Applications/Factorio.app/Contents/Resources/mods"
    fi
    echo "Detected architecture: $ARCH, using platform: $DOCKER_PLATFORM"
    echo "Using mods path: $MODS_PATH"
}

# Function to check for docker compose command
setup_compose_cmd() {
    if command -v docker &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        echo "Error: Docker not found. Please install Docker."
        exit 1
    fi
}

# Generate the dynamic docker-compose.yml file
generate_compose_file() {
    NUM_INSTANCES=${1:-1}
    SCENARIO=${2:-"default_lab_scenario"}
    
    # Validate scenario
    if [ "$SCENARIO" != "open_world" ] && [ "$SCENARIO" != "default_lab_scenario" ]; then
        echo "Error: Scenario must be either 'open_world' or 'default_lab_scenario'."
        exit 1
    fi
    
    # Validate input
    if ! [[ "$NUM_INSTANCES" =~ ^[0-9]+$ ]]; then
        echo "Error: Number of instances must be a positive integer."
        exit 1
    fi
    
    if [ "$NUM_INSTANCES" -lt 1 ] || [ "$NUM_INSTANCES" -gt 33 ]; then
        echo "Error: Number of instances must be between 1 and 33."
        exit 1
    fi
    
    # Create the docker-compose file
    cat > docker-compose.yml << EOF
version: '3'

services:
EOF
    
    # Add the specified number of factorio services
    for i in $(seq 0 $(($NUM_INSTANCES - 1))); do
        UDP_PORT=$((34197 + i))
        TCP_PORT=$((27000 + i))
        
        cat >> docker-compose.yml << EOF
  factorio_${i}:
    image: factorio
    platform: \${DOCKER_PLATFORM:-linux/amd64}
    command: /opt/factorio/bin/x64/factorio --start-server-load-scenario ${SCENARIO}
      --port 34197 --server-settings /opt/factorio/config/server-settings.json --map-gen-settings
      /opt/factorio/config/map-gen-settings.json --map-settings /opt/factorio/config/map-settings.json
      --server-banlist /opt/factorio/config/server-banlist.json --rcon-port 27015
      --rcon-password "factorio" --server-whitelist /opt/factorio/config/server-whitelist.json
      --use-server-whitelist --server-adminlist /opt/factorio/config/server-adminlist.json
      --mod-directory /opt/factorio/mods --map-gen-seed 44340
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1024m
    entrypoint: []
    environment:
    - SAVES=/opt/factorio/saves
    - CONFIG=/opt/factorio/config
    - MODS=/opt/factorio/mods
    - SCENARIOS=/opt/factorio/scenarios
    - PORT=34197
    - RCON_PORT=27015
    ports:
    - ${UDP_PORT}:34197/udp
    - ${TCP_PORT}:27015/tcp
    pull_policy: never
    restart: unless-stopped
    user: factorio
    volumes:
    - source: ../scenarios/default_lab_scenario
      target: /opt/factorio/scenarios/default_lab_scenario
      type: bind
    - source: ../scenarios/open_world
      target: /opt/factorio/scenarios/open_world
      type: bind
    - source: ${MODS_PATH}
      target: /opt/factorio/mods
      type: bind
    - source: ../../data/_screenshots
      target: /opt/factorio/script-output
      type: bind

EOF
    done
    
    echo "Generated docker-compose.yml with $NUM_INSTANCES Factorio instance(s) using scenario $SCENARIO"
}

# Function to start Factorio cluster
start_cluster() {
    NUM_INSTANCES=$1
    SCENARIO=$2
    
    setup_platform
    setup_compose_cmd
    
    # Generate the docker-compose file
    generate_compose_file "$NUM_INSTANCES" "$SCENARIO"
    
    # Run the docker-compose file
    echo "Starting $NUM_INSTANCES Factorio instance(s) with scenario $SCENARIO..."
    export NUM_INSTANCES  # Make it available to docker-compose
    $COMPOSE_CMD -f docker-compose.yml up -d
    
    echo "Factorio cluster started with $NUM_INSTANCES instance(s) using platform $DOCKER_PLATFORM and scenario $SCENARIO"
}

# Function to stop Factorio cluster
stop_cluster() {
    setup_compose_cmd
    
    if [ -f "docker-compose.yml" ]; then
        echo "Stopping Factorio cluster..."
        $COMPOSE_CMD -f docker-compose.yml down
        echo "Cluster stopped."
    else
        echo "Error: docker-compose.yml not found. No cluster to stop."
        exit 1
    fi
}

# Function to restart Factorio cluster
restart_cluster() {
    setup_compose_cmd
    
    if [ ! -f "docker-compose.yml" ]; then
        echo "Error: docker-compose.yml not found. No cluster to restart."
        exit 1
    fi
    
    echo "Extracting current configuration..."
    
    # Extract the number of instances
    CURRENT_INSTANCES=$(grep -c "factorio_" docker-compose.yml)
    
    # Extract the scenario from the first instance
    CURRENT_SCENARIO=$(grep -A1 "command:" docker-compose.yml | grep "start-server-load-scenario" | head -1 | sed -E 's/.*start-server-load-scenario ([^ ]+).*/\1/')
    
    if [ -z "$CURRENT_SCENARIO" ]; then
        CURRENT_SCENARIO="default_lab_scenario"
        echo "Warning: Could not determine current scenario, using default: $CURRENT_SCENARIO"
    fi
    
    echo "Found cluster with $CURRENT_INSTANCES instances using scenario: $CURRENT_SCENARIO"
    
    # Stop the current cluster
    echo "Stopping current cluster..."
    $COMPOSE_CMD -f docker-compose.yml down
    
    # Start with the same configuration
    echo "Restarting cluster..."
    start_cluster "$CURRENT_INSTANCES" "$CURRENT_SCENARIO"
    
    echo "Factorio cluster restarted successfully."
}

# Show usage information
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start         Start Factorio instances (default command)"
    echo "  stop          Stop all running instances"
    echo "  restart       Restart the current cluster with the same configuration"
    echo "  help          Show this help message"
    echo ""
    echo "Options:"
    echo "  -n NUMBER     Number of Factorio instances to run (1-33, default: 1)"
    echo "  -s SCENARIO   Scenario to run (open_world or default_lab_scenario, default: default_lab_scenario)"
    echo ""
    echo "Examples:"
    echo "  $0                           Start 1 instance with default_lab_scenario"
    echo "  $0 -n 5                      Start 5 instances with default_lab_scenario"
    echo "  $0 -n 3 -s open_world        Start 3 instances with open_world"
    echo "  $0 start -n 10 -s open_world Start 10 instances with open_world"
    echo "  $0 stop                      Stop all running instances"
    echo "  $0 restart                   Restart the current cluster"
}

# Main script execution
COMMAND="start"
NUM_INSTANCES=1
SCENARIO="default_lab_scenario"

# Check if first arg is a command
if [[ "$1" == "start" || "$1" == "stop" || "$1" == "restart" || "$1" == "help" ]]; then
    COMMAND="$1"
    shift
fi

# Parse options with getopts
while getopts ":n:s:h" opt; do
    case ${opt} in
        n )
            if ! [[ "$OPTARG" =~ ^[0-9]+$ ]]; then
                echo "Error: Number of instances must be a positive integer."
                exit 1
            fi
            NUM_INSTANCES=$OPTARG
            ;;
        s )
            if [ "$OPTARG" != "open_world" ] && [ "$OPTARG" != "default_lab_scenario" ]; then
                echo "Error: Scenario must be either 'open_world' or 'default_lab_scenario'."
                exit 1
            fi
            SCENARIO=$OPTARG
            ;;
        h )
            show_help
            exit 0
            ;;
        \? )
            echo "Error: Invalid option: -$OPTARG"
            show_help
            exit 1
            ;;
        : )
            echo "Error: Option -$OPTARG requires an argument."
            show_help
            exit 1
            ;;
    esac
done
shift $((OPTIND -1))

# Execute the appropriate command
case "$COMMAND" in
    start)
        start_cluster "$NUM_INSTANCES" "$SCENARIO"
        ;;
    stop)
        stop_cluster
        ;;
    restart)
        restart_cluster
        ;;
    help)
        show_help
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        show_help
        exit 1
        ;;
esac