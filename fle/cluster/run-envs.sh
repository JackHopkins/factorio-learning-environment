#!/bin/bash

# Function to detect and set host architecture
setup_platform() {
    ARCH=$(uname -m)
    OS=$(uname -s)
    if [ "$FORCE_AMD" = true ]; then
        export DOCKER_PLATFORM="linux/amd64"
    elif [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        # On macOS ARM64, automatically use AMD64 emulation since Factorio image lacks ARM64 support
        if [ "$OS" = "Darwin" ]; then
            export DOCKER_PLATFORM="linux/amd64"
            echo "Note: Using AMD64 emulation on macOS ARM64 (Factorio image lacks native ARM64 support)"
        else
            export DOCKER_PLATFORM="linux/arm64"
        fi
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
    # Expand leading ~ in MODS_PATH so docker-compose gets an absolute path
    if [[ "$MODS_PATH" == ~* ]]; then
        MODS_PATH="${HOME}${MODS_PATH:1}"
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
    COMMAND=${3:-"--start-server-load-scenario ${SCENARIO}"}

    # Build optional mods volume block based on ATTACH_MOD
    MODS_VOLUME=""
    if [ "$ATTACH_MOD" = true ]; then
        MODS_VOLUME=$(printf "    - source: %s\n      target: /opt/factorio/mods\n      type: bind\n" "$MODS_PATH")
    fi

    # Build optional save file volume block based on SAVE_ADDED
    SAVE_VOLUME=""
    if [ "$SAVE_ADDED" = true ]; then
        # Check if SAVE_FILE is a .zip file
        if [[ "$SAVE_FILE" != *.zip ]]; then
            echo "Error: Save file must be a .zip file."
            exit 1
        fi
        
        # Create saves directory if it doesn't exist
        mkdir -p ../../.fle/saves
        
        # Get the save file name (basename)
        SAVE_FILE_NAME=$(basename "$SAVE_FILE")
        
        # Copy the save file to the local saves directory
        cp "$SAVE_FILE" "../../.fle/saves/$SAVE_FILE_NAME"
        
        # Create variable for the container path
        CONTAINER_SAVE_PATH="/opt/factorio/saves/$SAVE_FILE_NAME"
        
        SAVE_VOLUME="    - source: ../../.fle/saves
      target: /opt/factorio/saves
      type: bind"
      COMMAND="--start-server ${SAVE_FILE_NAME}"
    fi
    
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
    image: factoriotools/factorio:1.1.110
    platform: \${DOCKER_PLATFORM:-linux/amd64}
    command: /opt/factorio/bin/x64/factorio ${COMMAND}
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
    ports:
    - ${UDP_PORT}:34197/udp
    - ${TCP_PORT}:27015/tcp
    pull_policy: missing
    restart: unless-stopped
    user: factorio
    volumes:
    - source: ./scenarios
      target: /opt/factorio/scenarios
      type: bind
    - source: ./config
      target: /opt/factorio/config
      type: bind
    - source: ../../.fle/data/_screenshots
      target: /opt/factorio/script-output
      type: bind
${SAVE_VOLUME}
${MODS_VOLUME}
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
    
    echo "Restarting existing Factorio services without regenerating docker-compose..."
    $COMPOSE_CMD -f docker-compose.yml restart
    echo "Factorio services restarted."
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
    echo "  -sv SAVE_FILE, --use_save SAVE_FILE Use a .zip save file from factorio"
    echo "  -m, --attach_mods Attach mods to the instances"
    echo "  -f86, --force_amd Force AMD platform"
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
SAVE_FILE=""

# Boolean: attach mods or not
ATTACH_MOD=false
FORCE_AMD=false
SAVE_ADDED=false

# Parse args (supporting both short and long options)
while [[ $# -gt 0 ]]; do
  case "$1" in
    start|stop|restart|help)
      COMMAND="$1"
      shift
      ;;
    -n|--number)
      if [[ -z "$2" || "$2" == -* ]]; then
        echo "Error: -n|--number requires an argument."
        show_help
        exit 1
      fi
      if ! [[ "$2" =~ ^[0-9]+$ ]]; then
        echo "Error: Number of instances must be a positive integer."
        exit 1
      fi
      NUM_INSTANCES="$2"
      shift 2
      ;;
    -s|--scenario)
      if [[ -z "$2" || "$2" == -* ]]; then
        echo "Error: -s|--scenario requires an argument."
        show_help
        exit 1
      fi
      case "$2" in
        open_world|default_lab_scenario)
          SCENARIO="$2"
          ;;
        *)
          echo "Error: Scenario must be either 'open_world' or 'default_lab_scenario'."
          exit 1
          ;;
      esac
      shift 2
      ;;
    -sv|--use_save)
      if [[ -z "$2" || "$2" == -* ]]; then
        echo "Error: -sv|--use_save requires an argument."
        show_help
        exit 1
      fi
      if [[ ! -f "$2" ]]; then
        echo "Error: Save file '$2' does not exist."
        exit 1
      fi
      SAVE_FILE="$2"
      SAVE_ADDED=true
      shift 2
      ;;
    -m|--attach_mods)
      ATTACH_MOD=true
      shift
      ;;
    -f86|--force_amd)
      FORCE_AMD=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Error: Invalid option: $1"
      show_help
      exit 1
      ;;
    *)
      # Unrecognized positional; ignore and continue
      shift
      ;;
  esac
done

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
