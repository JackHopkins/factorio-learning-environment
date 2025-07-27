#!/bin/bash

# Function to detect and set host architecture
setup_platform() {
    ARCH=$(uname -m)
    OS=$(uname -s)
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        export DOCKER_PLATFORM="linux/amd64"
    else
        export DOCKER_PLATFORM="linux/amd64"
    fi
    export SAVES_PATH="../../../.fle/saves"
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

# Function to check for saves and find the latest one
check_saves_and_get_latest() {
    # Check if saves directory exists
    if [ ! -d "$SAVES_PATH" ]; then
        echo "Error: Saves directory not found at $SAVES_PATH"
        exit 1
    fi

    # Add the specified number of factorio services
    for i in $(seq 0 $(($NUM_INSTANCES - 1))); do
        if ! ls "$SAVES_PATH/${i}"/*.zip 1> /dev/null 2>&1; then
            echo "Error: No .zip save files found in $SAVES_PATH/${i} for instance $i"
            exit 1
        fi
    done

    # Find the latest save file based on modification time
    LATEST_SAVE=$(ls -t "$SAVES_PATH"/*.zip | head -1)
    LATEST_SAVE_NAME=$(basename "$LATEST_SAVE")
    
    echo "Found latest save: $LATEST_SAVE_NAME"
    echo "Using save path: $SAVES_PATH"
}

# Generate the dynamic docker-compose.yml file
generate_compose_file() {
    NUM_INSTANCES=${1:-1}
    SCENARIO=${2:-"default_lab_scenario"}
    USE_LATEST_SAVE=${3:-false}
    
    # Validate scenario if not using latest save
    if [ "$USE_LATEST_SAVE" = "false" ]; then
        if [ "$SCENARIO" != "open_world" ] && [ "$SCENARIO" != "default_lab_scenario" ]; then
            echo "Error: Scenario must be either 'open_world' or 'default_lab_scenario'."
            exit 1
        fi
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
    
    # Determine the command based on whether to use latest save or scenario
    if [ "$USE_LATEST_SAVE" = "true" ]; then
        # Add the specified number of factorio services
        for i in $(seq 0 $(($NUM_INSTANCES - 1))); do
            mkdir -p ${SAVES_PATH}/${i}
        done
    
        START_COMMAND="--start-server-load-latest"
    else
        START_COMMAND="--start-server-load-scenario ${SCENARIO}"
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
    command: /opt/factorio/bin/x64/factorio ${START_COMMAND}
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
    - source: ${SAVES_PATH}/${i}
      target: /opt/factorio/saves
      type: bind

EOF
    done
    
    if [ "$USE_LATEST_SAVE" = "true" ]; then
        echo "Generated docker-compose.yml with $NUM_INSTANCES Factorio instance(s) using latest save"
    else
        echo "Generated docker-compose.yml with $NUM_INSTANCES Factorio instance(s) using scenario $SCENARIO"
    fi
}

# Function to start Factorio cluster
start_cluster() {
    NUM_INSTANCES=$1
    SCENARIO=$2
    USE_LATEST_SAVE=$3
    
    setup_platform
    setup_compose_cmd
    
    # Check for saves if using latest save mode
    if [ "$USE_LATEST_SAVE" = "true" ]; then
        check_saves_and_get_latest
    fi
    
    # Generate the docker-compose file
    generate_compose_file "$NUM_INSTANCES" "$SCENARIO" "$USE_LATEST_SAVE"
    
    # Run the docker-compose file
    if [ "$USE_LATEST_SAVE" = "true" ]; then
        echo "Starting $NUM_INSTANCES Factorio instance(s) with latest save..."
    else
        echo "Starting $NUM_INSTANCES Factorio instance(s) with scenario $SCENARIO..."
    fi
    export NUM_INSTANCES  # Make it available to docker-compose
    $COMPOSE_CMD -f docker-compose.yml up -d
    
    if [ "$USE_LATEST_SAVE" = "true" ]; then
        echo "Factorio cluster started with $NUM_INSTANCES instance(s) using platform $DOCKER_PLATFORM and latest save"
    else
        echo "Factorio cluster started with $NUM_INSTANCES instance(s) using platform $DOCKER_PLATFORM and scenario $SCENARIO"
    fi
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
    
    # Check if using latest save or scenario
    if grep -q "start-server-load-latest" docker-compose.yml; then
        CURRENT_MODE="latest_save"
        echo "Found cluster using latest save mode"
    else
        CURRENT_MODE="scenario"
        # Extract the scenario from the first instance
        CURRENT_SCENARIO=$(grep -A1 "command:" docker-compose.yml | grep "start-server-load-scenario" | head -1 | sed -E 's/.*start-server-load-scenario ([^ ]+).*/\1/')
        
        if [ -z "$CURRENT_SCENARIO" ]; then
            CURRENT_SCENARIO="default_lab_scenario"
            echo "Warning: Could not determine current scenario, using default: $CURRENT_SCENARIO"
        fi
        echo "Found cluster with scenario: $CURRENT_SCENARIO"
    fi
    
    echo "Found cluster with $CURRENT_INSTANCES instances"
    
    # Stop the current cluster
    echo "Stopping current cluster..."
    $COMPOSE_CMD -f docker-compose.yml down
    
    # Start with the same configuration
    echo "Restarting cluster..."
    if [ "$CURRENT_MODE" = "latest_save" ]; then
        start_cluster "$CURRENT_INSTANCES" "" "true"
    else
        start_cluster "$CURRENT_INSTANCES" "$CURRENT_SCENARIO" "false"
    fi
    
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
    echo "  -l            Use latest save instead of scenario (loads most recent .zip save from ../../../.fle/saves/0..n)"
    echo ""
    echo "Examples:"
    echo "  $0                           Start 1 instance with default_lab_scenario"
    echo "  $0 -n 5                      Start 5 instances with default_lab_scenario"
    echo "  $0 -n 3 -s open_world        Start 3 instances with open_world"
    echo "  $0 -l                        Start 1 instance with latest save"
    echo "  $0 -n 5 -l                   Start 5 instances with latest save"
    echo "  $0 start -n 10 -s open_world Start 10 instances with open_world"
    echo "  $0 stop                      Stop all running instances"
    echo "  $0 restart                   Restart the current cluster"
    echo ""
    echo "Note: When using -l (latest save), the system will:"
    echo "  1. Check for .zip save files in ../../../.fle/saves/0..n"
    echo "  2. Finds the most recently modified save file"
    echo "  3. Start the server with --start-server-load-latest"
}

# Main script execution
COMMAND="start"
NUM_INSTANCES=1
SCENARIO="default_lab_scenario"
USE_LATEST_SAVE=false

# Check if first arg is a command
if [[ "$1" == "start" || "$1" == "stop" || "$1" == "restart" || "$1" == "help" ]]; then
    COMMAND="$1"
    shift
fi

# Parse options with getopts
while getopts ":n:s:lh" opt; do
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
        l )
            USE_LATEST_SAVE=true
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

# Validate that scenario and latest save are not used together
if [ "$USE_LATEST_SAVE" = "true" ] && [ "$SCENARIO" != "default_lab_scenario" ]; then
    echo "Error: Cannot use both -l (latest save) and -s (scenario) options together."
    echo "When using -l, the scenario option is ignored as the server loads the latest save."
    exit 1
fi

# Execute the appropriate command
case "$COMMAND" in
    start)
        start_cluster "$NUM_INSTANCES" "$SCENARIO" "$USE_LATEST_SAVE"
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