# GitLab to GitHub Migration Guide

This document outlines the changes made to adapt the project from GitLab to GitHub.

## 🔄 What Changed

### 1. New GitHub-Specific Files

| File | Purpose |
|------|---------|
| `scripts/promote_next_github.py` | Main GitHub bot (replaces GitLab version) |
| `scripts/test_github.py` | GitHub connection testing |
| `run-github-bot.bat` | Windows runner for GitHub bot |
| `.env.github.example` | GitHub environment template |
| `README-GITHUB.md` | GitHub-focused documentation |
| `.github/workflows/test-github.yml` | GitHub Actions for GitHub bot |

### 2. Updated VS Code Configuration

The `.vscode/launch.json` now includes GitHub-specific debug configurations:
- **🧰 Test GitHub Connection** - Test GitHub API access
- **🤖 Run GitHub Bot (Single)** - Debug single GitHub issue creation
- **🤖 Run GitHub Bot (Continuous)** - Debug continuous mode

The `.vscode/tasks.json` includes new GitHub tasks for quick access.

## 🔧 Key API Differences

### Authentication
```python
# GitLab
headers = {"Private-Token": gitlab_token}

# GitHub  
headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github.v3+json"
}
```

### Repository Identification
```python
# GitLab - Uses numeric project ID
PROJECT_ID = "12345"
url = f"/projects/{PROJECT_ID}/issues"

# GitHub - Uses owner/repo format
REPO_OWNER = "username"
REPO_NAME = "repository"
url = f"/repos/{REPO_OWNER}/{REPO_NAME}/issues"
```

### Issue Creation
```python
# GitLab
issue_data = {
    "title": title,
    "description": description,  # GitLab uses 'description'
    "labels": [LABEL]
}

# GitHub
issue_data = {
    "title": title,
    "body": description,  # GitHub uses 'body'
    "labels": [LABEL]
}
```

### Issue Closure Detection
```python
# GitLab - Has dedicated 'closed_by' endpoint
closed_by = api_request(f"/projects/{PROJECT_ID}/issues/{issue_iid}/closed_by")

# GitHub - Must analyze timeline events
timeline_events = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}/timeline")
```

### User Assignment
```python
# GitLab - Uses user IDs
issue_data["assignee_ids"] = [123, 456]

# GitHub - Uses usernames directly
issue_data["assignees"] = ["alice", "bob"]
```

## 🚀 Migration Steps

### 1. Choose Your Implementation

You now have two options:

**Option A: Use GitHub Bot Only**
- Focus on `scripts/promote_next_github.py`
- Use GitHub-specific VS Code configurations
- Follow `README-GITHUB.md`

**Option B: Keep Both (Hybrid)**
- Keep existing GitLab implementation for reference
- Add GitHub implementation alongside
- Choose based on your target platform

### 2. Environment Configuration

**For GitHub:**
```bash
cp .env.github.example .env
# Edit .env with your GitHub credentials
```

**For GitLab (existing):**
```bash
cp .env.example .env  
# Edit .env with your GitLab credentials
```

### 3. Update Documentation

If switching to GitHub completely:
```bash
# Replace main README
mv README.md README-GITLAB.md
mv README-GITHUB.md README.md
```

### 4. VS Code Setup

The launch configurations now support both:
- GitLab configurations (existing)
- GitHub configurations (new)

Press `F5` and choose the appropriate configuration for your platform.

## 🧪 Testing Strategy

### Both Platforms
```bash
# Test with safe mock tests
python tests/test_runner.py --all
```

### GitHub-Specific
```bash
# Test GitHub connection
python scripts/test_github.py

# Run GitHub bot once
python scripts/promote_next_github.py
```

### GitLab-Specific (Legacy)
```bash
# Test GitLab connection  
python scripts/test_gitlab.py

# Run GitLab bot once
python scripts/promote_next.py
```

## 📋 Environment Variables Comparison

| Purpose | GitLab | GitHub |
|---------|--------|---------|
| **Token** | `GITLAB_TOKEN` | `GITHUB_TOKEN` |
| **Repository** | `PROJECT_ID` (numeric) | `REPO_OWNER` + `REPO_NAME` |
| **API URL** | `GITLAB_URL` | `GITHUB_URL` |
| **Labels** | `LABEL` | `LABEL` |
| **Assignees** | `ASSIGNEES` | `ASSIGNEES` |

## 🔍 Code Structure Comparison

### File Organization
```
# GitLab Implementation
scripts/promote_next.py          # Main bot
scripts/test_gitlab.py           # Connection test
tests/mock_gitlab.py            # Mock server
tests/test_integration.py       # Integration tests

# GitHub Implementation  
scripts/promote_next_github.py  # Main bot
scripts/test_github.py          # Connection test
# Note: Mock server would need GitHub API simulation
```

### Key Function Changes

| Function | GitLab Version | GitHub Version |
|----------|----------------|----------------|
| **Issue ID** | `issue['iid']` | `issue['number']` |
| **Issue URL** | `issue['web_url']` | `issue['html_url']` |
| **Closure Check** | `closed_by` endpoint | Timeline analysis |
| **API Base** | `/api/v4` | `/` (different structure) |

## 💡 Recommendations

### For New Projects
- Use the GitHub implementation (`scripts/promote_next_github.py`)
- Follow `README-GITHUB.md` for setup
- Use GitHub Actions workflow (`.github/workflows/test-github.yml`)

### For Existing GitLab Users
- Keep your existing setup working
- Test the GitHub version in parallel
- Migrate when ready

### For Multi-Platform Support
- Keep both implementations
- Use appropriate environment variables for each
- Consider creating a unified wrapper script

## 🚨 Important Notes

1. **API Rate Limits**: GitHub has different rate limits than GitLab
2. **Token Scopes**: GitHub requires `repo` scope vs GitLab's `api` scope  
3. **Issue Numbering**: GitHub uses sequential numbers, GitLab uses project-specific IIDs
4. **Closure Logic**: GitHub's timeline analysis is more complex than GitLab's dedicated endpoint

## 🎯 Next Steps

1. **Test the GitHub implementation** with your repository
2. **Update your documentation** to reflect the platform choice
3. **Configure CI/CD** using the appropriate workflow
4. **Train your team** on the new environment variables and setup

The GitHub implementation provides the same core functionality as the GitLab version, with platform-specific optimizations for the GitHub API.
