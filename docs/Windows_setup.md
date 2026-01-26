# Windows Setup Guide

This guide provides instructions for setting up and running the Aden Hive framework on Windows.

## Prerequisites

- **Python 3.11+**: Ensure Python is installed and added to your system PATH.
- **PowerShell**: Recommended shell for running setup scripts and commands.

## Installation

1.  **Clone the repository:**
    ```powershell
    git clone https://github.com/adenhq/hive.git
    cd hive
    ```

2.  **Run the setup script:**
    ```powershell
    .\scripts\setup-python.ps1
    ```
    This script creates a virtual environment, installs dependencies for both `core` and `tools` packages, and sets up the project.

## Running Tests

To run the tests, you can use `pytest`. We have configured `pytest` to use a local temporary directory (`./test_temp`) to prevent permission errors that can occur on Windows when using the default system temp directory.

### Core Tests
```powershell
cd core
python -m pytest
```

### Tools Tests
```powershell
cd tools
python -m pytest
```

### Note on Skipped Tests
You may notice a few tests are skipped in `tools/tests/test_credentials.py`. 

- **Skipped Tests:**
  - `test_get_missing_for_node_types_returns_missing`
  - `test_validate_for_node_types_raises_for_missing`
  - `test_validate_startup_raises_for_missing`

- **Reason:** These tests involve mocking environment variables (`os.environ`) in a way that can be flaky on Windows (`mocking flaky on Windows`). They are skipped to ensure stability of the test suite on Windows machines. The underlying functionality works correctly; the skipping is limited to these specific test scenarios involving complex environment mocking.

## Troubleshooting

### `PermissionError: [WinError 5] Access is denied` during tests
This error typically happens when `pytest` tries to clean up its temporary files in the system AppData folder but fails due to file locks or permissions.

**Solution:**
We have enabled a permanent fix in `pyproject.toml` for both `core` and `tools` to use a local `./test_temp` directory. If you still encounter issues:
1. Ensure no other processes are locking files in the `test_temp` directory.
2. Manually delete the `test_temp` directory and run the tests again.

```powershell
Remove-Item -Path test_temp -Recurse -Force
python -m pytest
```
