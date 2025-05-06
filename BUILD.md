# Building the factorio_learning_environment Package

This document explains how to build and install the Factorio Learning Environment package.

## Overview

The build process preserves the existing project structure while creating a package that can be imported with:

```python
from factorio_learning_environment import env
```

The build process:
1. Dynamically creates a `factorio_learning_environment` package during installation
2. Copies/links relevant code from the project into the package
3. Cleans up after building to maintain the original repo structure

## Building and Installing

### Development Installation (Editable Mode)

For development, install in editable mode:

```bash
# Install in development mode
pip install -e .

# Install with specific extras
pip install -e ".[agents]"  # LLM agent support
pip install -e ".[eval]"    # Evaluation tools
pip install -e ".[cluster]" # Cluster deployment
pip install -e ".[all]"     # All optional dependencies
pip install -e ".[dev]"     # Development dependencies
```

In editable mode, the temporary package structure will be kept in place to allow for live code changes.

### Building a Distribution Package

To build a wheel package for distribution:

```bash
# Install build dependencies
pip install build wheel

# Build the wheel
python -m build --wheel
```

The wheel file will be created in the `dist/` directory.

### Installing from the Wheel

```bash
pip install dist/factorio_learning_environment-*.whl
```

You can also specify extras:

```bash
pip install "dist/factorio_learning_environment-*.whl[agents]"
```

## Using the Package

After installation, import the package in your code:

```python
# Import the main package
import factorio_learning_environment as fle

# Import specific components
from factorio_learning_environment import env

# Access modules
env_instance = env.Instance()
```

## Testing the Installation

A test script is provided to verify the build and installation:

```bash
python test_install.py
```

This script:
1. Builds a wheel package
2. Creates a temporary virtual environment
3. Installs the package in editable mode
4. Tests importing the package
5. Reports the results

## Cleaning Up

If you need to clean up the dynamic package structure manually:

```bash
# Remove temporary files
rm -rf factorio_learning_environment/
rm -rf build/ dist/ *.egg-info/
```