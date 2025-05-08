#!/usr/bin/env python
import os
import sys
import shutil
import argparse
import tomli
import subprocess
from pathlib import Path

PACKAGE_NAME = "factorio_learning_environment"
MODULES = ['agents', 'env', 'server', 'eval', 'cluster']
VERSION = "0.2.0rc1"

def create_package_structure(clean=False):
    """
    Create the package structure for hatch build
    """
    root_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    package_dir = root_dir / PACKAGE_NAME
    
    # Clean the package directory if requested
    if clean and package_dir.exists():
        print(f"Cleaning {package_dir}...")
        shutil.rmtree(package_dir)
    
    # Create the package directory
    package_dir.mkdir(exist_ok=True)
    
    # Get version from pyproject.toml
    try:
        with open(root_dir / "pyproject.toml", "rb") as f:
            version = tomli.load(f)["project"]["version"]
    except (FileNotFoundError, KeyError):
        version = VERSION  # Fallback version
    
    # Create or update __about__.py
    about_file = package_dir / "__about__.py"
    print(f"Creating {about_file}...")
    with open(about_file, "w") as f:
        f.write(f'__version__ = "{version}"\n')
    
    # Create or update __init__.py
    init_file = package_dir / "__init__.py"
    print(f"Creating {init_file}...")
    
    # Write __init__.py
    with open(init_file, "w") as f:
        f.write(f"""# {PACKAGE_NAME} package
import tomli
import sys
import importlib.util
import os

__version__ = "{version}"

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

# Re-export important classes and functions at the top level
try:
    from .env.src.instance import FactorioInstance
    from .env.src import entities, game_types, namespace

    sys.modules['{PACKAGE_NAME}.entities'] = entities
    sys.modules['{PACKAGE_NAME}.game_types'] = game_types
    sys.modules['{PACKAGE_NAME}.namespace'] = namespace

    __all__ = [
        # Modules
        'env', 'agents', 'server', 'eval', 'cluster', 'entities', 'game_types', 'namespace',
        # Classes and functions
        'FactorioInstance',
    ]
except ImportError:
    # Allow the package to import even if some modules are missing (during build)
    pass
""")
    
    # Copy run.py if it exists
    run_file = root_dir / "run.py"
    if run_file.exists():
        print(f"Copying {run_file} to {package_dir / 'run.py'}...")
        shutil.copy(run_file, package_dir / "run.py")
    
    # Define files/dirs to exclude
    exclude_patterns = [
        "__pycache__", "*.pyc", "*.pyo", "*.pyd",
        ".git", ".DS_Store",
        "data/plans/factorio_guides", "eval/open/summary_cache",
        "dist", "build", "*.egg-info",
        ".claude",
        "client/log", "client/unscored_log", "src/log",
        "environment/src/.neptune",
        "environment/src/skills/bottom_up/skill_generation_logs",
        "*.jsonl",
        "data/blueprints_to_policies/blueprints/decoded",
        "data/blueprints_to_policies/blueprints/mining",
        "data/blueprints_to_policies/blueprints/electricity",
        "data/blueprints_to_policies/blueprints/manufacturing",
        "data/blueprints_to_policies/blueprints/misc",
        "data/encoded", "data/full", 
        "data/place_next_to_connect", "data/refactor", "data/refactor2",
        "environment/src/skills/expanded_skills",
        "environment/src/skills/ground_truth_skills",
        "environment/src/datasetgen/mcts/plots",
        "environment/src/search/mcts/runs",
        "data/icons",
        "environment/src/search/beam/summary_cache",
        "environment/src/search/independent_runs/summary_cache",
        "data/screenshots",
        "src/search/plots",
        "eval/open/.neptune",
        "eval/open/plots/icons",
        "eval/open/plots/production_volumes",
        "eval/open/mcts/runs",
        "eval/open/independent_runs/summary_cache",
        "eval/open/beam/summary_cache",
        "eval/open/plots",
        "eval/open/summary_cache",
        "*.mp4", "*.tar.gz", "*.whl", "*.zip", "*.data", "*.db", "*.pkl",
        "data/_screenshots", "data/screenshots", "data/icons",
        "docs/assets/videos", "docs/assets/images",
        "eval/open/summary_cache",
        "cluster/docker/mods",
        "agents/voyager/summary_cache",
    ]
    
    # Copy all modules with content
    for module in MODULES:
        module_src = root_dir / module
        module_dest = package_dir / module
        
        if module_src.exists():
            print(f"Copying module {module}...")
            
            # Remove existing directory if it exists
            if module_dest.exists():
                shutil.rmtree(module_dest)
            
            # Create the module directory
            module_dest.mkdir(exist_ok=True)
            
            # Copy all files except those matching exclude patterns
            for item in os.listdir(module_src):
                item_path = module_src / item
                
                # Skip excluded patterns
                should_skip = False
                for pattern in exclude_patterns:
                    if pattern in str(item_path):
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                dest_path = module_dest / item
                if item_path.is_dir():
                    shutil.copytree(
                        item_path, 
                        dest_path,
                        ignore=shutil.ignore_patterns(*exclude_patterns),
                        dirs_exist_ok=True
                    )
                else:
                    shutil.copy2(item_path, dest_path)
            
            # Ensure __init__.py exists
            module_init = module_dest / "__init__.py"
            if not module_init.exists():
                module_src_init = module_src / "__init__.py"
                if module_src_init.exists():
                    shutil.copy(module_src_init, module_init)
                else:
                    # Create an empty __init__.py
                    with open(module_init, 'w') as f:
                        f.write(f"# {module} module for {PACKAGE_NAME}\n")
    
    # Create a .py file for each module to ensure it's included in the package
    for module in MODULES:
        module_py_file = package_dir / f"{module}.py"
        if not module_py_file.exists():
            with open(module_py_file, 'w') as f:
                f.write(f"""# {module} module for {PACKAGE_NAME}
from . import {module}
""")
    
    print(f"\nPackage structure for {PACKAGE_NAME} prepared successfully!")
    print(f"Package directory: {package_dir}")
    print(f"Module structure:")
    for item in os.listdir(package_dir):
        if os.path.isdir(package_dir / item):
            print(f"  - {item}/ (directory)")
        else:
            print(f"  - {item} (file)")

def build_wheel():
    """
    Build the wheel package using setuptools
    """
    # Ensure dist directory exists
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Build the wheel
    print("\nBuilding wheel package...")
    try:
        # First ensure we have a MANIFEST.in file to include all data files
        manifest_content = """
include README.md
include LICENSE
recursive-include factorio_learning_environment *
global-exclude __pycache__
global-exclude *.py[cod]
global-exclude *.so
global-exclude .DS_Store
"""
        with open("MANIFEST.in", "w") as f:
            f.write(manifest_content)
        
        # Create setup.cfg to ensure package data is included
        setup_cfg_content = """
[metadata]
name = factorio-learning-environment
version = attr: factorio_learning_environment.__version__

[options]
packages = find:
include_package_data = True
zip_safe = False
python_requires = >=3.10

[options.entry_points]
console_scripts =
    fle = factorio_learning_environment.run:main
"""
        with open("setup.cfg", "w") as f:
            f.write(setup_cfg_content)
        
        # Create setup.py temporary content
        setup_content = f"""
from setuptools import setup, find_packages
import os
import glob

# Find all non-Python files to include
package_data_files = []
for root, dirs, files in os.walk('factorio_learning_environment'):
    for file in files:
        if not file.endswith('.py') and not file.endswith('.pyc'):
            rel_path = os.path.join(root, file)
            if '__pycache__' not in rel_path and '.DS_Store' not in rel_path:
                package_data_files.append(rel_path)

setup(
    name="factorio-learning-environment",
    version="{VERSION}",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    package_data={{
        '': ['*.*'],  # Include all files in the package
    }},
    python_requires=">=3.10",
    install_requires=[
        "dotenv>=0.9.9",
        "pydantic>=2.10.6",
        "lupa>=2.4",
        "slpp>=1.2.3",
        "factorio-rcon-py==1.2.1",
        "construct>=2.10.70",
        "pillow>=11.1.0",
        "tomli",
        "mcp[cli]",
        "numpy>=2.2.3"
    ],
    entry_points={{
        'console_scripts': [
            'fle={PACKAGE_NAME}.run:main',
        ],
    }},
)
"""
        # Write temporary setup.py for wheel building
        with open("temp_setup.py", "w") as f:
            f.write(setup_content)
        
        # Build wheel using setuptools
        subprocess.run([sys.executable, "temp_setup.py", "bdist_wheel"], check=True)
        
        # Clean up temporary setup.py and other files
        os.remove("temp_setup.py")
        
        # Check the size of the wheel
        wheel_files = [f for f in os.listdir("dist") if f.endswith(".whl")]
        if wheel_files:
            wheel_path = os.path.join("dist", wheel_files[-1])
            wheel_size = os.path.getsize(wheel_path) / (1024)  # Size in KB
            print(f"Wheel size: {wheel_size:.2f} KB")
            
            if wheel_size < 100:  # If wheel is still too small
                print("Warning: Wheel is too small, likely missing important files.")
                print("Falling back to setuptools_build.py for more reliable packaging...")
                
                # Use setuptools_build.py as a fallback
                if os.path.exists("setuptools_build.py"):
                    subprocess.run([sys.executable, "setuptools_build.py", "bdist_wheel"], check=True)
                    
                    # Check the new wheel size
                    wheel_files = [f for f in os.listdir("dist") if f.endswith(".whl")]
                    if wheel_files:
                        wheel_path = os.path.join("dist", wheel_files[-1])
                        wheel_size = os.path.getsize(wheel_path) / (1024)  # Size in KB
                        print(f"New wheel size: {wheel_size:.2f} KB")
        
        print("Wheel built successfully!")
        # List created distributions
        print("Created distributions:")
        for file in os.listdir("dist"):
            if file.endswith(".whl"):
                print(f"  - dist/{file}")
        
        return True
    except Exception as e:
        print(f"Error building wheel: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare package structure and build wheel")
    parser.add_argument("--clean", action="store_true", help="Clean existing package directory before setup")
    parser.add_argument("--build", action="store_true", help="Build wheel package after preparing structure")
    parser.add_argument("--no-prepare", action="store_true", help="Skip package structure preparation (use with --build)")
    args = parser.parse_args()
    
    if not args.no_prepare:
        create_package_structure(clean=args.clean)
    
    if args.build or args.no_prepare:
        print("\nBuilding wheel package...")
        build_wheel()
    else:
        print("\nYou can now run: hatch build")
        print("Or to install in development mode: pip install -e .")
        print("To build a wheel directly: python prepare_build.py --build")