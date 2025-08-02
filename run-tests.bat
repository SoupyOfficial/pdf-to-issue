@echo off
REM GitLab Issue Queue Bot - Test Runner
REM Convenient wrapper for running tests on Windows

setlocal enabledelayedexpansion

echo 🧪 GitLab Issue Queue Bot - Test Suite
echo ======================================

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
set GITLAB_TOKEN=test-token
set PROJECT_ID=12345

REM Parse command line arguments
if "%1"=="unit" goto unit_tests
if "%1"=="mock" goto mock_tests
if "%1"=="integration" goto integration_tests
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
echo   mock         Run mock integration tests only
echo   integration  Run real GitLab integration tests (requires credentials)
echo   all          Run unit and mock tests (default)
echo   help         Show this help message
echo.
echo Examples:
echo   run-tests.bat              Run all safe tests (unit + mock)
echo   run-tests.bat unit         Run only unit tests
echo   run-tests.bat integration  Run real GitLab tests (needs GITLAB_TOKEN)
pause
exit /b 0

:unit_tests
echo 🔬 Running Unit Tests Only...
python tests\test_runner.py --unit
goto end

:mock_tests
echo 🎭 Running Mock Integration Tests Only...
python tests\test_runner.py --mock
goto end

:integration_tests
echo ⚠️  WARNING: Integration tests will make real GitLab API calls!
echo Make sure GITLAB_TOKEN and PROJECT_ID are properly set.
echo.
set /p confirm="Continue with real GitLab integration tests? [y/N]: "
if /i not "%confirm%"=="y" (
    echo Integration tests cancelled.
    goto end
)
echo 🌐 Running Real GitLab Integration Tests...
python tests\test_integration.py
goto end

:all_tests
echo 🚀 Running All Safe Tests (Unit + Mock Integration)...
python tests\test_runner.py --all
goto end

:end
if errorlevel 1 (
    echo.
    echo ❌ Some tests failed. Check the output above for details.
    echo 💡 Tips:
    echo    - Make sure all dependencies are installed: pip install -r requirements.txt
    echo    - For integration tests, set GITLAB_TOKEN and PROJECT_ID environment variables
    echo    - Run individual test suites to isolate issues
) else (
    echo.
    echo ✅ All tests passed! Your GitLab bot is ready to go.
    echo.
    echo Next steps:
    echo 1. Configure your .env file with real GitLab credentials
    echo 2. Test with: run-bot.bat test
    echo 3. Run once: run-bot.bat
    echo 4. Set up GitLab CI/CD for automation
)

echo.
pause
