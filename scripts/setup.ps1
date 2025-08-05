# Issue Queue Bot - Windows Setup Script
# Run this script in PowerShell to set up the bot

param(
    [string]$GitHubToken = "",
    [string]$RepoOwner = "",
    [string]$RepoName = "",
    [string]$GitHubUrl = "https://api.github.com",
    [string]$Label = "auto-generated",
    [string]$Assignees = ""
)

Write-Host "🤖 Issue Queue Bot Setup" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found. Please install Python 3.7+ first." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "requirements.txt")) {
    Write-Host "❌ Please run this script from the pdf-to-issue project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "`n📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "`n📝 Creating .env configuration file..." -ForegroundColor Yellow
    
    if ($GitHubToken -eq "") {
        $GitHubToken = Read-Host "Enter your GitHub Personal Access Token"
    }
    
    if ($RepoOwner -eq "") {
        $RepoOwner = Read-Host "Enter your Repository Owner (username or organization)"
    }
    
    if ($RepoName -eq "") {
        $RepoName = Read-Host "Enter your Repository Name"
    }
    
    $envContent = @"
GITHUB_TOKEN=$GitHubToken
REPO_OWNER=$RepoOwner
REPO_NAME=$RepoName
GITHUB_URL=$GitHubUrl
LABEL=$Label
ASSIGNEES=$Assignees
POLL_INTERVAL=900
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ Created .env file" -ForegroundColor Green
}
else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Test the connection
Write-Host "`n🧪 Testing API connection..." -ForegroundColor Yellow

# Load environment variables from .env file
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -match "^[^#].*=" } | ForEach-Object {
        $key, $value = $_ -split "=", 2
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

python scripts/test_connection.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🎉 Setup completed successfully!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Add some .md files to the issues/ directory" -ForegroundColor White
    Write-Host "2. Run a test promotion: python scripts/promote_next.py" -ForegroundColor White
    Write-Host "3. For continuous mode: python scripts/promote_next.py --continuous" -ForegroundColor White
    Write-Host "4. Set up GitHub Actions for automation" -ForegroundColor White
}
else {
    Write-Host "`n❌ Setup completed but connection test failed" -ForegroundColor Red
    Write-Host "Please check your token and repository settings" -ForegroundColor Yellow
}
