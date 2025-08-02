# GitLab Issue Queue Bot - Windows Setup Script
# Run this script in PowerShell to set up the bot

param(
    [string]$GitLabToken = "",
    [string]$ProjectId = "",
    [string]$GitLabUrl = "https://gitlab.com",
    [string]$Label = "auto-generated",
    [string]$Assignees = ""
)

Write-Host "🤖 GitLab Issue Queue Bot Setup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
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
    
    if ($GitLabToken -eq "") {
        $GitLabToken = Read-Host "Enter your GitLab Personal Access Token"
    }
    
    if ($ProjectId -eq "") {
        $ProjectId = Read-Host "Enter your GitLab Project ID (numeric)"
    }
    
    $envContent = @"
GITLAB_TOKEN=$GitLabToken
PROJECT_ID=$ProjectId
GITLAB_URL=$GitLabUrl
LABEL=$Label
ASSIGNEES=$Assignees
POLL_INTERVAL=900
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ Created .env file" -ForegroundColor Green
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Test the connection
Write-Host "`n🧪 Testing GitLab connection..." -ForegroundColor Yellow

# Load environment variables from .env file
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -match "^[^#].*=" } | ForEach-Object {
        $key, $value = $_ -split "=", 2
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

python scripts/test_gitlab.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🎉 Setup completed successfully!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Add some .md files to the issues/ directory" -ForegroundColor White
    Write-Host "2. Run a test promotion: python scripts/promote_next.py" -ForegroundColor White
    Write-Host "3. For continuous mode: python scripts/promote_next.py --continuous" -ForegroundColor White
    Write-Host "4. Set up GitLab CI/CD schedule for automation" -ForegroundColor White
} else {
    Write-Host "`n❌ Setup completed but connection test failed" -ForegroundColor Red
    Write-Host "Please check your GitLab token and project ID" -ForegroundColor Yellow
}
