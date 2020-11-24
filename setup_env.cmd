@echo off
@setlocal

REM This script creates a development environment.

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set PACKAGE_NAME=alerter
set ENV_DIR=%ROOT%\env\%PACKAGE_NAME%
set PIP_INI=%ENV_DIR%\pip.ini
set ACTIVATE_SCRIPT=%ENV_DIR%\Scripts\activate.bat
set DEACTIVATE_SCRIPT=%ENV_DIR%\Scripts\deactivate.bat
set REQ_FILE=%ROOT%\requirements.txt
set DEV_REQ_FILE=%ROOT%\dev_requirements.txt
set SRC_DIR=%ROOT%\src
set PACKAGE_DIR=%SRC_DIR%\%PACKAGE_NAME%

echo.
echo Creating environment "%ENV_DIR%"
python -m venv --clear "%ENV_DIR%"
if ERRORLEVEL 1 (
    echo Failed to create environment 1>&2
    exit /b 1
)

if not exist "%ENV_DIR%\." (
    echo Failed to create environment 1>&2
    exit /b 1
)

if not exist "%ACTIVATE_SCRIPT%" (
    echo Environment activation script "%ACTIVATE_SCRIPT%" does not exist. 1>&2
    exit /b 1
)

call "%ACTIVATE_SCRIPT%"
if ERRORLEVEL 1 (
    echo Failed to activate environment 1>&2
    exit /b 1
)

echo.
echo Updating pip to latest from public feed.
python -m pip install --upgrade pip
if ERRORLEVEL 1 (
    echo Failed to update pip 1>&2
    exit /b 1
)

REM echo.
REM echo Installing credential provider for azure devops from public feed.
REM python -m pip install artifacts-keyring --pre
REM
REM echo.
REM echo Creating PIP INI to point to index.
REM echo.[global]>"%PIP_INI%"
REM echo.index-url=https://pkgs.dev.azure.com/cold-logic/_packaging/roq_dependencies/pypi/simple/>>"%PIP_INI%"

echo.
echo Installing packages from "%REQ_FILE%"
python -m pip install --requirement "%REQ_FILE%"

echo.
echo Installing packages from "%DEV_REQ_FILE%"
python -m pip install --requirement "%DEV_REQ_FILE%"
REM This is for development only and allows unit test to be run off code-in-edit.

echo.
echo Installing ROQ in development mode to allow unit test to run natively
python -m pip install --no-index --no-deps -e "%ROOT%"

call "%DEACTIVATE_SCRIPT%"
if ERRORLEVEL 1 (
    echo Failed to deactivate environment 1>&2
    exit /b 1
)

echo.
echo Environment creation completed!
echo.
echo To activate run ... ^>^>^> "%ACTIVATE_SCRIPT%"
