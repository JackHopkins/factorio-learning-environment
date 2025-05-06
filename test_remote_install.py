#!/usr/bin/env python
"""
Script to test installing the package from PyPI (or TestPyPI) and importing it.
This should be run in a separate directory from the project.
"""

import os
import sys
import subprocess
import tempfile
import shutil

def test_remote_install(from_test_pypi=True, extras=None):
    """Test installing and importing the package from PyPI or TestPyPI."""
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # Create a virtual environment
        venv_dir = os.path.join(temp_dir, "venv")
        print(f"Creating virtual environment in {venv_dir}...")
        
        venv_result = subprocess.run(
            [sys.executable, "-m", "venv", venv_dir],
            capture_output=True,
            text=True
        )
        
        if venv_result.returncode != 0:
            print("Failed to create virtual environment!")
            print("STDOUT:", venv_result.stdout)
            print("STDERR:", venv_result.stderr)
            return False
        
        # Determine python and pip commands
        if os.name == "nt":  # Windows
            python_cmd = os.path.join(venv_dir, "Scripts", "python.exe")
            pip_cmd = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:  # Unix/Linux/Mac
            python_cmd = os.path.join(venv_dir, "bin", "python")
            pip_cmd = os.path.join(venv_dir, "bin", "pip")
        
        # Make pip more up-to-date
        subprocess.run(
            [pip_cmd, "install", "--upgrade", "pip"],
            capture_output=True
        )
        
        # Construct the installation command
        package_name = "factorio-learning-environment"
        
        # Add extras if specified
        if extras:
            if isinstance(extras, list):
                package_name += "[" + ",".join(extras) + "]"
            else:
                package_name += f"[{extras}]"
        
        if from_test_pypi:
            # Install from TestPyPI with regular PyPI as a fallback for dependencies
            print(f"Installing {package_name} from TestPyPI...")
            install_command = [
                pip_cmd, "install", 
                "--index-url", "https://test.pypi.org/simple/", 
                "--extra-index-url", "https://pypi.org/simple/",
                package_name
            ]
        else:
            # Install directly from PyPI
            print(f"Installing {package_name} from PyPI...")
            install_command = [
                pip_cmd, "install", package_name
            ]
        
        # Run the installation
        install_result = subprocess.run(
            install_command,
            capture_output=True,
            text=True
        )
        
        print("Installation STDOUT:", install_result.stdout)
        if install_result.stderr:
            print("Installation STDERR:", install_result.stderr)
        
        if install_result.returncode != 0:
            print("Failed to install package!")
            return False
        
        # Test importing the package
        print("\nTesting import...")
        import_test = """
try:
    # Get site-packages directory for debugging
    import site
    site_packages = site.getsitepackages()
    print(f"Site packages directories: {site_packages}")
    import os
    if site_packages:
        pkg_dir = os.path.join(site_packages[0], 'factorio_learning_environment')
        if os.path.exists(pkg_dir):
            print(f"Package directory exists: {pkg_dir}")
            print(f"Contents: {os.listdir(pkg_dir)}")
        else:
            print(f"Package directory does not exist: {pkg_dir}")
    
    # Try the import
    import factorio_learning_environment as fle
    print(f"Successfully imported factorio_learning_environment {fle.__version__ if hasattr(fle, '__version__') else '(version unknown)'}")
    print(f"Available modules: {dir(fle)}")
    
    # Check all submodules
    modules_status = {}
    
    try:
        from factorio_learning_environment import env
        modules_status['env'] = 'Success'
        print(f"Env modules: {dir(env)}")
    except ImportError as e:
        modules_status['env'] = f'Failed: {str(e)}'
    
    for module in ['agents', 'eval', 'cluster', 'server']:
        try:
            # Use exec for dynamic import
            exec(f"from factorio_learning_environment import {module}")
            modules_status[module] = 'Success'
        except ImportError as e:
            modules_status[module] = f'Failed: {str(e)}'
    
    for module, status in modules_status.items():
        print(f"  - {module}: {status}")
        
except Exception as e:
    print(f"Error importing: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    raise
"""
        
        test_result = subprocess.run(
            [python_cmd, "-c", import_test],
            capture_output=True,
            text=True
        )
        
        print("\nImport test results:")
        print("STDOUT:", test_result.stdout)
        if test_result.stderr:
            print("STDERR:", test_result.stderr)
        
        return "Successfully imported factorio_learning_environment" in test_result.stdout

if __name__ == "__main__":
    print("=== Testing Remote Installation of factorio-learning-environment ===")
    
    # Check command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Test installing the package from PyPI or TestPyPI.')
    parser.add_argument('--testpypi', action='store_true', 
                        help='Install from TestPyPI instead of regular PyPI')
    parser.add_argument('--extras', type=str, 
                        help='Comma-separated list of extras to include (e.g., "agents,eval")')
    args = parser.parse_args()
    
    extras = args.extras.split(',') if args.extras else None
    success = test_remote_install(from_test_pypi=args.testpypi, extras=extras)
    
    if success:
        print("\n✅ Installation and import test successful!")
        sys.exit(0)
    else:
        print("\n❌ Installation or import test failed!")
        sys.exit(1)