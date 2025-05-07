# Building the factorio_learning_environment Package

This document explains how to build and install the Factorio Learning Environment package.

## Using prepare_build.py

You can also build directly with the `prepare_build.py` script, which now includes direct wheel building functionality.

### Building the Package

```bash
# Clean, prepare, and build in one step
python prepare_build.py --clean --build
```

This will:
1. Clean the existing package structure
2. Create the package structure
3. Build a wheel (.whl) in the `dist/` directory

You can also run these steps separately:

```bash
# Just prepare the package structure
python prepare_build.py --clean

# Just build the wheel (using previously prepared structure)
python prepare_build.py --no-prepare --build
```

### Using Hatch

If you prefer using Hatch, you can still do so:

1. Install Hatch:
   ```bash
   pip install hatch
   ```

2. Prepare the package structure:
   ```bash
   python prepare_build.py --clean
   ```

3. Build the package with Hatch:
   ```bash
   hatch build
   ```

   This will create both a source distribution (.tar.gz) and a wheel (.whl) in the `dist/` directory.

### Development Installation

For development, you can install the package in editable mode:

```bash
python prepare_build.py
pip install -e .
```

This creates the necessary package structure and installs the package in development mode, allowing changes to be reflected immediately without reinstalling.

You can also specify extras:

```bash
pip install -e ".[agents]"  # LLM agent support
pip install -e ".[eval]"    # Evaluation tools
pip install -e ".[cluster]" # Cluster deployment
pip install -e ".[all]"     # All optional dependencies
pip install -e ".[dev]"     # Development dependencies
```

## Installing from the Wheel

```bash
pip install dist/factorio_learning_environment-*.whl
```

You can also specify extras:

```bash
pip install "dist/factorio_learning_environment-*.whl[agents]"
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
import factorio_learning_environment as fle

# Import specific components
from factorio_learning_environment import env

# Access modules
env_instance = env.Instance()
```

## Cleaning Up

If you need to clean up the dynamic package structure manually:

```bash
# Remove temporary files
rm -rf factorio_learning_environment/
rm -rf build/ dist/ *.egg-info/
rm -rf wheel_extract/ test_install*/
```