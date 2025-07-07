# Building the factorio_learning_environment Package

This document explains how to build and install the Factorio Learning Environment package.

### Building the Package

```bash
uv build
```

This will:
1. Create the package structure
2. Build a wheel (.whl) in the `dist/` directory

## Installing from the Wheel

```bash
pip install dist/factorio_learning_environment-*.whl
```

## Verifying the Installation

To verify that the installation was successful:

```bash
# Create a test environment
mkdir -p test_install && cd test_install
python -m venv test_env
source test_env/bin/activate

# Install the wheel
pip install ../dist/factorio_learning_environment-*.whl

# Verify installation
python -c "import factorio_learning_environment; print(factorio_learning_environment.__file__)"
```

## Using the Package

After installation, import the package in your code:

```python
# Import the main package
import fle

# Import specific components
from fle import env

# Access modules
env_instance = env.Instance()
```