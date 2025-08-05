@echo off
REM Extract and create GitHub labels from markdown issues
REM Usage: extract-labels.bat [repo] [options]

if "%1"=="" (
    echo Usage: extract-labels.bat REPO [OPTIONS]
    echo   REPO: Repository in format "owner/repo" ^(e.g., "SoupyOfficial/pdf-to-issue"^)
    echo   OPTIONS: Additional options to pass to the Python script
    echo.
    echo Examples:
    echo   extract-labels.bat SoupyOfficial/pdf-to-issue
    echo   extract-labels.bat SoupyOfficial/pdf-to-issue --dry-run
    echo   extract-labels.bat SoupyOfficial/pdf-to-issue --token YOUR_TOKEN
    echo.
    echo Multiple repositories:
    echo   extract-labels.bat --repos owner1/repo1 owner2/repo2 owner3/repo3
    echo.
    echo Environment Variables:
    echo   GITHUB_TOKEN: GitHub Personal Access Token ^(required if not passed via --token^)
    goto :eof
)

REM Check if first argument starts with --repos for multiple repositories
if "%1"=="--repos" (
    python extract_and_create_labels.py %*
) else (
    python extract_and_create_labels.py --repo %*
)
