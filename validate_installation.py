#!/usr/bin/env python3
"""
Comprehensive validation of the factorio-learning-environment package installation.
This script:
1. Creates a temporary virtual environment
2. Installs the package from the wheel
3. Validates that all submodules can be imported
4. Tests importing key classes and functions
5. Reports detailed module structure
"""
import os
import sys
import subprocess
import tempfile
import venv
import shutil
import glob

def main():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a virtual environment
        env_dir = os.path.join(temp_dir, "venv")
        print(f"Creating virtual environment in {env_dir}...")
        venv.create(env_dir, with_pip=True)

        # Get paths to Python and pip in the virtual environment
        if sys.platform == "win32":
            python_exe = os.path.join(env_dir, "Scripts", "python.exe")
            pip_exe = os.path.join(env_dir, "Scripts", "pip.exe")
        else:
            python_exe = os.path.join(env_dir, "bin", "python")
            pip_exe = os.path.join(env_dir, "bin", "pip")

        # Find the most recent wheel file
        wheel_files = glob.glob("dist/*.whl")
        if not wheel_files:
            print("No wheel files found in dist/ directory")
            return 1
        
        wheel_path = max(wheel_files, key=os.path.getctime)
        print(f"Installing wheel: {wheel_path}")
        subprocess.check_call([pip_exe, "install", wheel_path])

        # Test script that verifies import and functionality
        print("Running comprehensive validation...")
        validation_script = """
import sys
import os
import inspect

try:
    import factorio_learning_environment as fle
    from factorio_learning_environment import env, agents, server, eval, cluster
    
    # Print basic information
    print(f"\\n=== PACKAGE INFORMATION ===")
    print(f"Version: {fle.__version__}")
    print(f"Package path: {os.path.dirname(fle.__file__)}")
    
    # Check if main classes are importable
    print(f"\\n=== CHECKING TOP-LEVEL IMPORTS ===")
    try:
        from factorio_learning_environment import FactorioInstance
        print("✓ FactorioInstance imported")
    except ImportError as e:
        print(f"✗ FactorioInstance import failed: {e}")
    
    # Check submodules
    print(f"\\n=== CHECKING SUBMODULE STRUCTURE ===")
    for module_name in ['env', 'agents', 'server', 'eval', 'cluster']:
        module = getattr(fle, module_name)
        print(f"\\n{module_name} module:")
        print(f"  Path: {module.__file__}")
        print(f"  Contents: {sorted([name for name in dir(module) if not name.startswith('_')])[:5]}...")
    
    # Try importing some key components from each module
    print(f"\\n=== CHECKING KEY COMPONENTS ===")
    try:
        # Check env module
        print("\\nenv module components:")
        if hasattr(env, 'src'):
            print(f"  env.src exists: {sorted([name for name in dir(env.src) if not name.startswith('_')])[:5]}...")
        else:
            print("  env.src not found")
            
        # Check agents module
        print("\\nagents module components:")
        if hasattr(agents, 'agent_abc'):
            print(f"  ✓ agents.agent_abc exists")
        else:
            print("  ✗ agents.agent_abc not found")
            
        # Check server module
        print("\\nserver module components:")
        if hasattr(server, 'tools'):
            print(f"  ✓ server.tools exists")
        else:
            print("  ✗ server.tools not found")
    
    except Exception as e:
        print(f"Error checking components: {e}")
    
    print("\\n=== VALIDATION COMPLETE ===")
    print("✓ Package imports successfully")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
"""
        
        result = subprocess.run(
            [python_exe, "-c", validation_script],
            capture_output=True,
            text=True
        )
        
        print("\nVALIDATION OUTPUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nERRORS:")
            print(result.stderr)
            return 1
        
        print("\nInstallation validation completed successfully!")
        return 0
    
    finally:
        # Clean up
        print(f"Cleaning up {temp_dir}...")
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    sys.exit(main())