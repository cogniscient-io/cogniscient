# Cogniscient Package Release Process

This document outlines the steps required to build and release the `cogniscient` package.

## Prerequisites

- Python 3.10 or higher
- `build` package: `pip install build`
- `twine` package: `pip install twine` (for uploading to PyPI)

## Build the Package

To build the package for distribution:

```bash
# Ensure you're in the project root directory
cd /path/to/cogniscient/PoC

# Upgrade build tools
pip install --upgrade build twine

# Build the package
python -m build
```

This will create `dist/` directory with both source distribution (`.tar.gz`) and wheel (`.whl`) files.

## Test the Package

Before releasing, test the package in a virtual environment:

```bash
# Create a virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install the built package
pip install dist/cogniscient-*.whl

# Test that the package can be imported and used
python -c "from cogniscient import GCSRuntime; print('Import successful')"
python -c "from cogniscient import cli; print('CLI import successful')"
```

## Release Process

### 1. Update Version Number

Update the version in `pyproject.toml` following semantic versioning (MAJOR.MINOR.PATCH):

```toml
[project]
name = "cogniscient"
version = "0.1.1"  # Update this before release
```

### 2. Tag the Release

```bash
git add pyproject.toml
git commit -m "Bump version to 0.1.1 for release"
git tag -a v0.1.1 -m "Release version 0.1.1"
```

### 3. Build the Package

```bash
python -m build
```

### 4. Upload to TestPyPI (Optional but Recommended)

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*
```

Test the installation from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ cogniscient
```

### 5. Upload to PyPI

```bash
# Upload to real PyPI
twine upload dist/*
```

## Verification

After releasing, verify the package is installable:

```bash
# Create new virtual environment
python -m venv verify_env
source verify_env/bin/activate  # On Windows: verify_env\Scripts\activate

# Install the released package
pip install cogniscient

# Test basic functionality
python -c "from cogniscient import GCSRuntime; print('Cogniscient imported successfully')"
python -c "from cogniscient import cli; print('CLI module available')"
```

## CLI Usage

Once installed, users can run the Cogniscient system via the CLI:

```bash
# Show help
cogniscient --help

# Run the system with default settings
cogniscient run

# List available configurations
cogniscient list-configs

# Load a specific configuration
cogniscient load-config --config-name my-config-name
```

## Development Installation

For development, install the package in editable mode:

```bash
pip install -e .
# Or with development dependencies
pip install -e ".[dev]"
```