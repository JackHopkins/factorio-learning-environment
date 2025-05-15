#!/bin/bash

# Define the port to find and share
PORT=34198
PROTOCOL=udp

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if zrok is installed
if ! command -v zrok &> /dev/null; then
    echo -e "${RED}Error: zrok is not installed.${NC}"
    echo "Please install zrok first:"
    echo "  curl -L https://github.com/openziti/zrok/releases/latest/download/zrok_linux_amd64.tar.gz | tar xzf -"
    echo "  sudo mv zrok /usr/local/bin/"
    exit 1
fi

# Check if zrok is enabled
if ! zrok status &> /dev/null; then
    echo -e "${YELLOW}zrok is not enabled. You need to enable it with an account token.${NC}"
    echo "Run: zrok enable YOUR_TOKEN"
    exit 1
fi

# Find the process using the specified port
echo -e "${YELLOW}Looking for process using ${PORT}/${PROTOCOL}...${NC}"

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    PROCESS_INFO=$(lsof -i ${PROTOCOL}:${PORT} -n -P 2>/dev/null)
    if [ -z "$PROCESS_INFO" ]; then
        echo -e "${RED}No process found using ${PORT}/${PROTOCOL}${NC}"
        exit 1
    fi

    PID=$(echo "$PROCESS_INFO" | grep LISTEN 2>/dev/null || echo "$PROCESS_INFO" | grep -v "COMMAND" | head -1 | awk '{print $2}')
    PROCESS_NAME=$(echo "$PROCESS_INFO" | grep -v "COMMAND" | head -1 | awk '{print $1}')
    COMMAND=$(ps -p $PID -o command= 2>/dev/null || echo "Unknown command")

else
    # Linux
    PROCESS_INFO=$(ss -${PROTOCOL}lpn "sport = :${PORT}" 2>/dev/null)
    if [ -z "$PROCESS_INFO" ]; then
        echo -e "${RED}No process found using ${PORT}/${PROTOCOL}${NC}"
        exit 1
    fi

    PID_INFO=$(echo "$PROCESS_INFO" | grep -v "State" | head -1 | sed -n 's/.*pid=\([^,]*\).*/\1/p')
    if [ -z "$PID_INFO" ]; then
        echo -e "${RED}Could not determine PID for the process using ${PORT}/${PROTOCOL}${NC}"
        exit 1
    fi

    PID=$PID_INFO
    PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "Unknown")
    COMMAND=$(ps -p $PID -o cmd= 2>/dev/null || echo "Unknown command")
fi

if [ -z "$PID" ]; then
    echo -e "${RED}Could not determine PID for the process using ${PORT}/${PROTOCOL}${NC}"
    exit 1
fi

# Display the process information
echo -e "${GREEN}Found process:${NC}"
echo -e "  Process Name: ${YELLOW}${PROCESS_NAME}${NC}"
echo -e "  PID: ${YELLOW}${PID}${NC}"
echo -e "  Command: ${YELLOW}${COMMAND}${NC}"
echo -e "  Port: ${YELLOW}${PORT}/${PROTOCOL}${NC}"

# Confirm whether to share the process
read -p "Do you want to share this process using zrok? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Share the process using zrok
echo -e "\n${YELLOW}Sharing process on ${PORT}/${PROTOCOL} using zrok...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop sharing when done.${NC}\n"

# If UDP, use udpTunnel mode
if [ "$PROTOCOL" = "udp" ]; then
    zrok share private --backend-mode udpTunnel 127.0.0.1:${PORT}
else
    # Fallback to tcp if not udp
    zrok share private --backend-mode tcpTunnel 127.0.0.1:${PORT}
fi

exit 0