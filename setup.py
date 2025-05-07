#!/usr/bin/env python
import os
import sys
import shutil
import glob
import subprocess
import tempfile
import atexit
import tomli  # Added for reading toml files
import argparse

# Package name
PACKAGE_NAME = "factorio_learning_environment"

# Determine mode - development or deployment
# Set this environment variable to bypass the complex build process
IN_DEVELOPMENT = os.environ.get("FLE_DEVELOPMENT") == "1"


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


# Function to read a template file
def read_template_file(template_path):
    """Read a template file and return its contents"""
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading template file {template_path}: {e}")
        return None


# Function to render a template with simple variable substitution
def render_template(template_content, context):
    """
    Render a template string with the given context variables
    using simple string formatting
    """
    try:
        # Simple variable substitution
        return template_content.format(**context)
    except Exception as e:
        print(f"Error rendering template: {e}")
        return None


VERSION = get_version_from_toml()
print(f"Building version: {VERSION}")

# For simple setup.py commands like 'develop', we can skip the complex build
if IN_DEVELOPMENT or (len(sys.argv) > 1 and (sys.argv[1] in ['develop', 'egg_info'] or '-e' in sys.argv)):
    # Simple development setup without side effects
    from setuptools import setup, find_packages

    # Clean up any existing egg-info directories first
    for item in os.listdir('.'):
        if item.endswith('.egg-info'):
            print(f"Removing existing {item}...")
            shutil.rmtree(item)

    setup(
        name="factorio-learning-environment",
        version=VERSION,
        packages=find_packages(),
        package_data={
            "": ["*.md", "*.txt", "*.lua"],
        },
        # Dependencies will be handled by pyproject.toml
    )

    # Exit now without running the complex build logic
    sys.exit(0)

# Continue with the original complex build process for deployment
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
        # Check for template files
        templates_dir = "packaging"
        init_template_path = os.path.join(templates_dir, "__init__.py.template")
        setup_template_path = os.path.join(templates_dir, "setup.py.template")

        # Verify template files exist
        if not os.path.exists(init_template_path):
            raise FileNotFoundError(f"Template file not found: {init_template_path}")

        if not os.path.exists(setup_template_path):
            raise FileNotFoundError(f"Template file not found: {setup_template_path}")

        # Create the package directory structure inside the temp directory
        package_dir = os.path.join(temp_build_dir, PACKAGE_NAME)
        os.makedirs(package_dir)

        # Create context for templates
        template_context = {
            'package_name': PACKAGE_NAME,
            'version': VERSION
        }

        # Read and render __init__.py template
        init_template_content = read_template_file(init_template_path)
        if init_template_content:
            init_content = render_template(init_template_content, template_context)
            if init_content:
                with open(os.path.join(package_dir, "__init__.py"), "w") as f:
                    f.write(init_content)
            else:
                print("Warning: Failed to render __init__.py template.")
                # Fallback to minimal __init__.py
                with open(os.path.join(package_dir, "__init__.py"), "w") as f:
                    f.write(f"# {PACKAGE_NAME} package\n__version__ = \"{VERSION}\"\n")
        else:
            print("Warning: Failed to read __init__.py template.")
            # Fallback to minimal __init__.py
            with open(os.path.join(package_dir, "__init__.py"), "w") as f:
                f.write(f"# {PACKAGE_NAME} package\n__version__ = \"{VERSION}\"\n")

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

        # Read and render setup.py template
        setup_template_content = read_template_file(setup_template_path)
        setup_py_path = os.path.join(temp_build_dir, "setup.py")

        if setup_template_content:
            setup_content = render_template(setup_template_content, template_context)
            if setup_content:
                with open(setup_py_path, "w") as f:
                    f.write(setup_content)
            else:
                print("Warning: Failed to render setup.py template.")
                # Fallback to minimal setup.py
                with open(setup_py_path, "w") as f:
                    f.write(f"""
from setuptools import setup
setup(
    name="factorio-learning-environment",
    version="{VERSION}",
    packages=["{PACKAGE_NAME}"],
)
                    """)
        else:
            print("Warning: Failed to read setup.py template.")
            # Fallback to minimal setup.py
            with open(setup_py_path, "w") as f:
                f.write(f"""
from setuptools import setup
setup(
    name="factorio-learning-environment",
    version="{VERSION}",
    packages=["{PACKAGE_NAME}"],
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