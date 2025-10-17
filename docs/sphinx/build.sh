#!/bin/bash

# Build Sphinx documentation
# This script builds the Sphinx documentation and outputs it to the build directory

set -e

echo "Building Sphinx documentation..."

# Change to the docs/sphinx directory
cd "$(dirname "$0")"

# Build the documentation
sphinx-build -b html source build/html

echo "Documentation built successfully!"
echo "Output directory: $(pwd)/build/html"
echo "Open $(pwd)/build/html/index.html in your browser to view the documentation."
