#!/usr/bin/env python
"""
This file is maintained for backward compatibility.
For modern installations, see BUILD.md for build options.

Alternative methods:
    python prepare_build.py --clean --build  # All-in-one build
    
    # OR using hatch
    python prepare_build.py --clean
    hatch build

For development installation:
    python prepare_build.py
    pip install -e .
"""
import os
import sys
import subprocess
import shutil
import pathlib

print("Note: See BUILD.md for details on all build options.")
print()

# Check if we are in development mode
IN_DEVELOPMENT = os.environ.get("FLE_DEVELOPMENT") == "1" or len(sys.argv) > 1 and sys.argv[1] in ['develop', 'egg_info']

# For development mode, prepare the build structure and install
if IN_DEVELOPMENT:
    subprocess.run([sys.executable, "prepare_build.py"], check=True)
    from setuptools import setup
    setup()
# For build commands, prefer setuptools_build.py if it exists, otherwise use hatch
elif len(sys.argv) > 1 and sys.argv[1] in ['bdist_wheel', 'sdist', 'build']:
    # Check if setuptools_build.py exists
    if pathlib.Path("setuptools_build.py").exists():
        print("Using setuptools_build.py for more reliable packaging...")
        try:
            subprocess.run([sys.executable, "setuptools_build.py", "bdist_wheel"], check=True)
            print("\nBuild completed successfully!")
            
            # List created distributions
            print("Created distributions:")
            for file in os.listdir("dist"):
                print(f"  - dist/{file}")
        except subprocess.CalledProcessError:
            print("\nBuild failed.")
            sys.exit(1)
    else:
        # Use prepare_build.py with direct build capability
        print("Using prepare_build.py with direct build capabilities...")
        try:
            subprocess.run([sys.executable, "prepare_build.py", "--clean", "--build"], check=True)
            print("\nBuild completed successfully!")
            
            # List created distributions
            print("Created distributions:")
            for file in os.listdir("dist"):
                print(f"  - dist/{file}")
        except subprocess.CalledProcessError:
            print("\nBuild failed.")
            sys.exit(1)
# For other commands, use setuptools
else:
    from setuptools import setup
    setup()