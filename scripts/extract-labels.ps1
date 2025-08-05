#!/usr/bin/env powershell
<#
.SYNOPSIS
    Extract and create GitHub labels from markdown issues

.DESCRIPTION
    This script reads all markdown files in the issues/ directory, extracts labels,
    and creates them in the specified GitHub repository if they don't already exist.

.PARAMETER Repo
    Repository in format "owner/repo" (e.g., "SoupyOfficial/pdf-to-issue")

.PARAMETER Repos
    Multiple repositories in format "owner/repo"

.PARAMETER Token
    GitHub Personal Access Token (or set GITHUB_TOKEN env var)

.PARAMETER IssuesDir
    Directory containing markdown issue files (default: issues)

.PARAMETER GitHubUrl
    GitHub API URL (default: https://api.github.com)

.PARAMETER DryRun
    Show what would be created without actually creating labels

.EXAMPLE
    .\extract-labels.ps1 -Repo "SoupyOfficial/pdf-to-issue"

.EXAMPLE
    .\extract-labels.ps1 -Repo "SoupyOfficial/pdf-to-issue" -DryRun

.EXAMPLE
    .\extract-labels.ps1 -Repos "owner1/repo1","owner2/repo2"

.EXAMPLE
    .\extract-labels.ps1 -Repo "SoupyOfficial/pdf-to-issue" -Token "your_token_here"
#>

param(
    [string]$Repo,
    [string[]]$Repos,
    [string]$Token,
    [string]$IssuesDir = "issues",
    [string]$GitHubUrl = "https://api.github.com",
    [switch]$DryRun
)

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH"
    exit 1
}

# Check if extract_and_create_labels.py exists
if (-not (Test-Path "extract_and_create_labels.py")) {
    Write-Error "extract_and_create_labels.py not found in current directory"
    exit 1
}

# Build arguments for Python script
$args = @()

if ($Repos) {
    $args += "--repos"
    $args += $Repos
} elseif ($Repo) {
    $args += "--repo"
    $args += $Repo
} else {
    Write-Error "Either -Repo or -Repos must be specified"
    exit 1
}

if ($Token) {
    $args += "--token"
    $args += $Token
}

if ($IssuesDir -ne "issues") {
    $args += "--issues-dir"
    $args += $IssuesDir
}

if ($GitHubUrl -ne "https://api.github.com") {
    $args += "--github-url"
    $args += $GitHubUrl
}

if ($DryRun) {
    $args += "--dry-run"
}

# Run the Python script
Write-Host "Running: python extract_and_create_labels.py $($args -join ' ')"
& python extract_and_create_labels.py @args
