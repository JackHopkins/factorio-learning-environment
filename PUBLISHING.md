# Publishing the factorio-learning-environment Package

This guide explains how to publish the package to PyPI and test it from another project.

## Publishing to PyPI

### Files Excluded from Build

The build process respects `.gitignore` patterns and explicitly excludes:
- `.git*` files and directories
- `__pycache__` directories
- `.pyc` and other bytecode files
- Virtual environment directories
- Log files and directories
- All image files (png, jpg, jpeg, gif, etc.)
- Large data directories like `data/plans/factorio_guides`
- Cache directories and temporary files
- Previous build artifacts (dist, build, etc.)

**Important**: The package should be around 2-5MB. If it's significantly larger, something is wrong! The most common issue is including the `factorio_guides` directory or image files.

This ensures that your package remains clean and doesn't include unnecessary files.

### 1. Install Required Tools

```bash
pip install build twine
```

### 2. Build the Distribution Packages

Always clean before building to avoid including stale artifacts:

```bash
# Option 1: Use the clean build script (recommended)
./clean_build.py

# Option 2: Clean manually and build
./clean.sh
python -m build

# Option 3: For faster builds (if you're confident in your setup)
./clean_build.py --no-isolation
```

The clean build script will remove all build artifacts and then build the package, ensuring you don't include large files or directories that should be excluded.

This will create both a source distribution (.tar.gz) and a wheel (.whl) in the `dist/` directory.

### 3. Check Your Package

Before uploading, check that your package is valid:

```bash
twine check dist/*
```

### 4. Upload to TestPyPI (Recommended for Testing)

TestPyPI is a separate instance of PyPI that allows you to test the package without affecting the real PyPI:

```bash
twine upload --repository testpypi dist/*
```

You'll be prompted for your TestPyPI credentials. You can create an account at https://test.pypi.org/account/register/ if you don't have one.

### 5. Upload to PyPI (For Production)

Once you've verified everything works on TestPyPI:

```bash
twine upload dist/*
```

You'll need a PyPI account from https://pypi.org/account/register/.

## Testing Installation from PyPI

### Testing from TestPyPI

```bash
# Create a test environment
mkdir ~/test-install
cd ~/test-install
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ factorio-learning-environment

# With extras (e.g., agents)
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ "factorio-learning-environment[agents]"

# The extra-index-url is needed to get dependencies from the real PyPI
```

### Using the Test Script

You can also use the provided test script to test the remote installation:

```bash
# Test installation from TestPyPI
python test_remote_install.py --testpypi

# Test with extras
python test_remote_install.py --testpypi --extras="agents,eval"

# Test from regular PyPI
python test_remote_install.py
```

### Testing from PyPI

After publishing to the real PyPI:

```bash
# Create a test environment
mkdir ~/test-install
cd ~/test-install
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from PyPI
pip install factorio-learning-environment

# With extras
pip install factorio-learning-environment[agents]
```

## Verify Installation

```python
# Run Python
python

# Try importing
>>> import factorio_learning_environment as fle
>>> from factorio_learning_environment import env
>>> print(dir(fle))
```

## Using API Tokens (Recommended)

Instead of using your username and password with Twine, it's better to use API tokens:

1. Go to your account settings on TestPyPI or PyPI
2. Navigate to "API tokens" and create a new token
3. Store the token in a `.pypirc` file in your home directory:

```
# ~/.pypirc
[testpypi]
  username = __token__
  password = TOKEN

[pypi]
  username = __token__
  password = TOKEN
```

Replace the token values with your actual tokens.

## Version Management

Remember to update the version in `pyproject.toml` each time you publish:

```toml
[project]
name = "factorio-learning-environment"
version = "0.2.2"  # Increment this with each release
```

Follow [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for backward-compatible functionality
- PATCH version for backward-compatible bug fixes

## GitHub Releases

It's also good practice to tag releases on GitHub:

```bash
git tag v0.2.2
git push origin v0.2.2
```

Then create a release on GitHub with release notes detailing changes.