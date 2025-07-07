#!/bin/bash
# Clean script to remove build artifacts before creating a new package

echo "Cleaning build artifacts..."

# Remove build directories
rm -rf dist/
rm -rf factorio_learning_environment/

# Remove any __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "Clean complete."