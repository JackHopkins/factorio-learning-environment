import subprocess
import sys
import importlib
import os

# Path to the built package
package_path = "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/dist/factorio_learning_environment-0.2.5.tar.gz"

# Verify the file exists
if not os.path.exists(package_path):
    print(f"Error: Package file not found at {package_path}")
    sys.exit(1)

# Install the package
print(f"Installing package from {package_path}...")
try:
    # Use force-reinstall to ensure we're using the latest build
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--force-reinstall", package_path],
        capture_output=True,
        text=True,
        check=True
    )
    print("Installation output:")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("Installation failed:")
    print(e.stderr)
    sys.exit(1)

# Test importing the package
print("\nTesting import of factorio_learning_environment:")
try:
    # Force reload if it's already imported
    if "factorio_learning_environment" in sys.modules:
        importlib.reload(sys.modules["factorio_learning_environment"])
    else:
        import factorio_learning_environment

    print(f"Successfully imported factorio_learning_environment version: {factorio_learning_environment.__version__}")

    # Test importing submodules
    from factorio_learning_environment import env

    print("Successfully imported factorio_learning_environment.env")

    # List available submodules
    print("\nAvailable submodules:")
    for module_name in factorio_learning_environment.__all__:
        print(f"- {module_name}")

    print("\nPackage structure looks good!")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)