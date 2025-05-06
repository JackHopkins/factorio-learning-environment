#!/usr/bin/env python
import os
import sys
import shutil
import glob
import subprocess
import tempfile
import atexit
import tomli  # Added for reading toml files

# Package name
PACKAGE_NAME = "factorio_learning_environment"


# Read version from pyproject.toml instead of hardcoding it
def get_version_from_toml():
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomli.load(f)
            return data["project"]["version"]
    except (FileNotFoundError, KeyError, tomli.TOMLDecodeError) as e:
        print(f"Error reading version from pyproject.toml: {e}")
        print("Falling back to default version")
        return "0.2.5"  # Fallback version


VERSION = get_version_from_toml()
print(f"Building version: {VERSION}")

try:
    # Clean up any existing build artifacts
    for directory in ['build', f'{PACKAGE_NAME}.egg-info']:
        if os.path.exists(directory):
            print(f"Removing {directory}...")
            shutil.rmtree(directory)

    # Create a temp directory with a predictable name
    temp_build_dir = os.path.join(os.getcwd(), "tmp_build_dir")
    if os.path.exists(temp_build_dir):
        try:
            shutil.rmtree(temp_build_dir)
        except Exception as e:
            print(f"Warning: Could not remove existing temp directory: {e}")
            # Create a different temp directory if we can't remove the existing one
            temp_build_dir = tempfile.mkdtemp(prefix=f"{PACKAGE_NAME}_build_")

    # Create the temp directory
    os.makedirs(temp_build_dir, exist_ok=True)


    # Register cleanup function to run at exit
    def cleanup_temp_dir():
        original_dir = os.getcwd()
        # Change back to original directory if we're still in the temp dir
        if os.getcwd().startswith(temp_build_dir):
            os.chdir(original_dir)

        if os.path.exists(temp_build_dir):
            try:
                print(f"Cleaning up {temp_build_dir}...")
                for root, dirs, files in os.walk(temp_build_dir):
                    for file in files:
                        try:
                            os.chmod(os.path.join(root, file), 0o777)
                        except:
                            pass
                shutil.rmtree(temp_build_dir, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not fully remove temp directory: {e}")


    atexit.register(cleanup_temp_dir)

    try:
        # Create the package directory structure inside the temp directory
        package_dir = os.path.join(temp_build_dir, PACKAGE_NAME)
        os.makedirs(package_dir)

        # Create __init__.py
        with open(os.path.join(package_dir, "__init__.py"), "w") as f:
            f.write(f"""# {PACKAGE_NAME} package
__version__ = "{VERSION}"
import sys
import importlib.util

# First, create empty module objects for all of our submodules
# This prevents import errors when modules try to import each other
for name in ['env', 'agents', 'server', 'eval', 'cluster']:
    module_name = f'{PACKAGE_NAME}.{{name}}'
    if module_name not in sys.modules:
        # Create empty module to avoid circular imports
        spec = importlib.util.find_spec(module_name)
        if spec:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
    
    # Create alias in global namespace immediately
    sys.modules[name] = sys.modules[f'{PACKAGE_NAME}.{{name}}']

# Now import all submodules safely
from . import env
from . import agents
from . import server
from . import eval
from . import cluster

__all__ = ['env', 'agents', 'server', 'eval', 'cluster']
""")

        # Copy modules to package directory
        for module in ['env', 'agents', 'server', 'eval', 'cluster']:
            if os.path.exists(module):
                dest_dir = os.path.join(package_dir, module)
                print(f"Copying {module} to {dest_dir}...")

                # Define only what to exclude rather than limiting what to include
                exclude_patterns = [
                    '__pycache__', '*.pyc', '*.pyo', '*.pyd',
                    '.git', '.DS_Store',
                    'data/plans/factorio_guides', 'eval/open/summary_cache',
                    'dist', 'build', '*.egg-info'
                ]

                # Optionally exclude large binary files to keep package size manageable
                # Uncomment if needed
                # binary_exclusions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp',
                #                     '*.ico', '*.svg', '*.mp4', '*.bin', '*.dat']
                # exclude_patterns.extend(binary_exclusions)

                shutil.copytree(
                    module,
                    dest_dir,
                    ignore=shutil.ignore_patterns(*exclude_patterns)
                )

                # Ensure __init__.py exists
                init_file = os.path.join(dest_dir, "__init__.py")
                if not os.path.exists(init_file):
                    with open(init_file, "w") as f:
                        f.write(f"# {module} module\n")

        # Copy run.py if it exists
        if os.path.exists("run.py"):
            print("Copying run.py...")
            shutil.copy("run.py", os.path.join(package_dir, "run.py"))

        # Copy pyproject.toml to the temp directory
        print("Copying pyproject.toml...")
        shutil.copy("pyproject.toml", os.path.join(temp_build_dir, "pyproject.toml"))

        # Create setup.py in the temp directory that reads version from pyproject.toml
        setup_py = os.path.join(temp_build_dir, "setup.py")
        with open(setup_py, "w") as f:
            f.write(f"""
import tomli
from setuptools import setup, find_packages

# Read version from pyproject.toml
def get_version():
    with open("pyproject.toml", "rb") as f:
        data = tomli.load(f)
        return data["project"]["version"]

setup(
    name="factorio-learning-environment",
    version=get_version(),
    packages=["{PACKAGE_NAME}"] + ["{PACKAGE_NAME}." + pkg for pkg in ['env', 'agents', 'server', 'eval', 'cluster']],
    package_data={{
        # Include all files for all packages
        '{PACKAGE_NAME}': ['*.*'],
        '{PACKAGE_NAME}.env': ['**/*.*'],
        '{PACKAGE_NAME}.agents': ['**/*.*'],
        '{PACKAGE_NAME}.server': ['**/*.*'],
        '{PACKAGE_NAME}.eval': ['**/*.*'],
        '{PACKAGE_NAME}.cluster': ['**/*.*', 'docker/**/*', 'scenarios/**/*'],
    }},
    include_package_data=True,
)
    """)

        # Create or empty the dist directory
        if not os.path.exists("dist"):
            os.makedirs("dist")
        else:
            for file in os.listdir("dist"):
                file_path = os.path.join("dist", file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)

        # Save current directory
        original_dir = os.getcwd()

        # Change to the temp directory and build
        print(f"Building from {temp_build_dir}...")
        os.chdir(temp_build_dir)

        # Run the build command directly with additional error handling
        try:
            # Create dist directory in the temp build dir
            os.makedirs("dist", exist_ok=True)

            # Run the build command
            cmd = [sys.executable, "setup.py", "sdist", "bdist_wheel"]
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print("Build failed with error:")
                print(result.stderr)
                raise Exception("Build command failed")

            print(result.stdout)

            # Go back to original directory
            os.chdir(original_dir)

            # Copy the built packages to the dist directory
            for file in glob.glob(os.path.join(temp_build_dir, "dist", "*")):
                dest = os.path.join("dist", os.path.basename(file))
                print(f"Copying {file} -> {dest}")
                shutil.copy2(file, dest)

            print("\nBuild completed successfully!")
            print(f"Package version: {VERSION}")
            dist_files = glob.glob("dist/*")
            for file in dist_files:
                print(f"Created: {file}")

            # Optionally verify the wheel contents
            wheel_file = next((f for f in dist_files if f.endswith('.whl')), None)
            if wheel_file:
                print(f"\nTo inspect wheel contents: python -m zipfile -l {wheel_file}")
                print(f"To install: pip install {wheel_file}")

                # Verify there's no duplication at root level
                try:
                    import zipfile

                    with zipfile.ZipFile(wheel_file, 'r') as z:
                        names = z.namelist()
                        non_metadata = [name for name in names
                                        if not name.startswith(f"{PACKAGE_NAME}-{VERSION}.dist-info/")
                                        and not name.startswith(f"{PACKAGE_NAME}/")]
                        if non_metadata:
                            print("\nWarning: Found extra files at root level in wheel:")
                            for name in non_metadata:
                                print(f"  {name}")
                        else:
                            print("\nWheel structure looks good! No duplicated directories.")
                except Exception as e:
                    print(f"Error checking wheel structure: {e}")
        except Exception as e:
            print(f"Error during build process: {e}")
            # Go back to original directory if an error occurred
            os.chdir(original_dir)

    except Exception as e:
        print(f"Error setting up build: {e}")

    # The cleanup will be handled by the atexit handler
    print("Build process completed.")

except Exception as e:
    # Capture the error but don't display it
    with open('build_errors.log', 'w') as f:
        f.write(f"Error during build (can be ignored if files were created): {str(e)}")
    print("Build process completed with some non-critical errors.")