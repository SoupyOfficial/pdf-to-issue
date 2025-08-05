@echo off
REM Issue Queue Bot - Test Runner
REM Convenient wrapper for running tests on Windows

setlocal enabledelayedexpansion

echo 🧪 Issue Queue Bot - Test Suite
echo ==============================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.7+ first.
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "requirements.txt" (
    echo ❌ Please run this from the pdf-to-issue project root directory
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist ".venv" (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Set up environment for tests
set GITHUB_TOKEN=test-token
set REPO_OWNER=test-owner
set REPO_NAME=test-repo

REM Parse command line arguments
if "%1"=="unit" goto unit_tests
if "%1"=="labels" goto label_tests
if "%1"=="all" goto all_tests
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help

REM Default: run all tests
goto all_tests

:show_help
echo Usage: run-tests.bat [option]
echo.
echo Options:
echo   unit         Run unit tests only
echo   labels       Run label parsing tests only
echo   all          Run all tests (default)
echo   help         Show this help message
echo.
echo Examples:
echo   run-tests.bat              Run all tests
echo   run-tests.bat unit         Run only unit tests
echo   run-tests.bat labels       Run only label parsing tests
pause
exit /b 0

:unit_tests
echo 🔬 Running Unit Tests Only...
python tests\test_runner.py --unit
goto end

:label_tests
echo �️  Running Label Parsing Tests Only...
python tests\test_runner.py --labels
goto end

:all_tests
echo 🚀 Running All Tests...
python tests\test_runner.py --all
goto end

:end
if errorlevel 1 (
    echo.
    echo ❌ Some tests failed. Check the output above for details.
    echo 💡 Tips:
    echo    - Make sure all dependencies are installed: pip install -r requirements.txt
    echo    - Run individual test suites to isolate issues
) else (
    echo.
    echo ✅ All tests passed! Your bot is ready to go.
    echo.
    echo Next steps:
    echo 1. Configure your .env file with real credentials
    echo 2. Test with: run-bot.bat test
    echo 3. Run once: run-bot.bat
    echo 4. Set up GitHub Actions for automation
)

echo.
pause
