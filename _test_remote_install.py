import subprocess
import sys
import importlib
import os

# Test installing from TestPyPI
print("Testing installation from TestPyPI...")
try:
    # Use force-reinstall to ensure we're using the latest version
    # Also use --no-deps to avoid dependency conflicts from test.pypi.org
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps",
         "-i", "https://test.pypi.org/simple/", "factorio-learning-environment"],
        capture_output=True,
        text=True,
        check=True
    )
    print("Installation output:")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("Installation from TestPyPI failed:")
    print(e.stderr)
    print("\nFallback to installing from local file...")

    # Path to the built package
    package_path = "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/dist/factorio_learning_environment-0.2.5.tar.gz"

    # Verify the file exists
    if not os.path.exists(package_path):
        print(f"Error: Package file not found at {package_path}")
        sys.exit(1)

    # Install the package from local file
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", package_path],
            capture_output=True,
            text=True,
            check=True
        )
        print("Local installation output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Local installation failed:")
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
    from factorio_learning_environment import agents
    from factorio_learning_environment import cluster
    from factorio_learning_environment import eval

    print("Successfully imported factorio_learning_environment.env")

    # List available submodules
    print("\nAvailable submodules:")
    for module_name in factorio_learning_environment.__all__:
        print(f"- {module_name}")

    print("\nPackage structure looks good!")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)