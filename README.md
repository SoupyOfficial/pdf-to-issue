# PDF to Issues Extractor + Issue Queue Bot

A Python tool to extract issues from ChatGPT PDF exports and convert them into numbered Markdown files. Includes an automated bot that promotes issues one at a time, waiting for each to be completed before creating the next.

## 🎯 Purpose

This tool solves two key problems:

1. **PDF to Markdown**: Converting ChatGPT conversation exports (PDFs) that contain issue specifications into properly formatted, individual Markdown files ready for import.

2. **Automated Issue Queue**: A bot that promotes these Markdown files to repository issues one at a time, ensuring each issue is completed (closed by a merged PR) before creating the next one.

Perfect for when you've had ChatGPT help you generate a comprehensive list of issues for your project and want to manage them systematically.

## ✨ Features

### PDF Extraction Features
- **PDF Text Extraction**: Extracts text from ChatGPT PDF exports using PyPDF2
- **Intelligent Issue Parsing**: Automatically identifies and separates individual GitHub issues from the PDF content
- **GitHub-Ready Formatting**: Converts issues to proper Markdown format with standardized sections
- **Unicode Sanitization**: Handles emojis and special characters from ChatGPT output
- **Numbered Output**: Creates sequentially numbered files (001-title.md, 002-title.md, etc.)
- **Comprehensive Logging**: Detailed logging for debugging and monitoring extraction progress
- **Error Handling**: Robust error handling for various PDF formats and content structures

### Issue Queue Bot Features
- **Sequential Processing**: Creates GitHub issues one at a time in numerical order
- **Merge Gate**: Waits for issues to be closed by merged PRs before proceeding
- **Smart Status Checking**: Differentiates between manual closes and PR-based closes
- **Automatic Assignment**: Can auto-assign issues to specified users
- **Label Management**: Tags all bot-created issues with a configurable label
- **Multiple Deployment Options**: GitHub Actions, cron, or Docker container
- **Comprehensive Logging**: Detailed audit trail of all bot actions

## 📁 Project Structure

```
pdf-to-issue/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .github/
│   └── workflows/
│       ├── test.yml             # GitHub Actions CI/CD (GitLab version)
│       └── test-github.yml      # GitHub Actions CI/CD (GitHub version)
├── .env.example                # Configuration template
├── run-bot.bat                 # Windows batch runner for the bot
├── scripts/
│   ├── extract_issues.py       # PDF extraction script
│   ├── promote_next.py         # GitLab queue bot (legacy)
│   ├── promote_next_github.py  # GitHub queue bot (main script)
│   ├── test_gitlab.py          # GitLab connection test (legacy)
│   ├── test_github.py          # GitHub connection test
│   └── setup.ps1               # Windows PowerShell setup script
├── chat_exports/               # Place your ChatGPT PDF exports here
│   ├── AshTrail - GitHub Issue Creation.pdf
│   └── [your-pdf-files].pdf
├── issues/                     # Generated GitHub issues (output)
│   ├── 001-set-up-clean-architecture-foundation.md
│   ├── 002-implement-multi-account-user-switching.md
│   └── [numbered-issues].md
└── logs/
    ├── extract_issues.log      # PDF extraction logs
    └── promote_next.log        # GitHub bot logs
```

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- A ChatGPT PDF export containing your issues
- GitHub repository access

### Installation
```bash
git clone https://github.com/your-username/pdf-to-issue.git
cd pdf-to-issue
pip install -r requirements.txt
```

### Usage
```bash
# 1. Extract issues from ChatGPT PDF
python scripts/extract_issues.py chat_exports/your-chatgpt-export.pdf

# 2. Run the GitHub bot (single check)
export GITHUB_TOKEN="your_github_token"
export REPO_OWNER="your-username"
export REPO_NAME="your-repo"
python scripts/promote_next_github.py

# 3. Run continuously (checks every 15 minutes)
python scripts/promote_next_github.py --continuous
```

### Example Command
```bash
python scripts/extract_issues.py chat_exports/AshTrail-GitHub-Issue-Creation.pdf
```

## 📝 Expected ChatGPT PDF Format

The tool expects your ChatGPT conversation to contain GitHub issues in this format:

```markdown
markdown
### Title
Your Issue Title Here

### Description
Detailed description of what needs to be implemented...

**Tasks**
- Task 1
- Task 2
- Task 3

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Labels
feature, backend, enhancement
```

## 📋 Output Format

Each extracted issue becomes a separate Markdown file with this structure:

**Filename**: `001-your-issue-title.md`

**Content**:
```markdown
Your Issue Title Here

### Title
Your Issue Title Here

### Description
Detailed description of what needs to be implemented...

**Tasks**
- Task 1
- Task 2
- Task 3

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Labels
feature, backend, enhancement
```

---

# 🤖 GitHub Queue Bot

The GitHub Queue Bot automatically promotes your numbered Markdown files to GitHub issues, but with a crucial twist: it only creates the next issue after the previous one has been **closed by a merged PR**. This ensures a steady, manageable workflow that prevents issue overload.

## 🔄 How It Works

1. **Check Last Issue**: Looks for the most recent bot-created issue
2. **Verify Completion**: Ensures it's closed AND the closing PR is merged
3. **Find Next File**: Locates the next numbered Markdown file
4. **Create Issue**: Posts it to GitHub with proper labels and assignments
5. **Wait**: Sleeps until the next poll cycle

## ⚙️ Quick Setup

### Prerequisites

- GitHub Personal Access Token with `repo` scope
- GitHub repository owner and name
- Python 3.7+

### Windows Setup (Recommended)

1. **Run the setup script**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
   ```

2. **Test the connection**:
   ```cmd
   run-bot.bat test
   ```

3. **Run once**:
   ```cmd
   run-bot.bat
   ```

4. **Run continuously**:
   ```cmd
   run-bot.bat continuous
   ```

### Manual Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment** (copy `.env.example` to `.env`):
   ```env
   GITHUB_TOKEN=your_token_here
   REPO_OWNER=your-username
   REPO_NAME=your-repo
   LABEL=auto-generated
   ASSIGNEES=username1,username2
   ```

3. **Test connection**:
   ```bash
   python scripts/test_github.py
   ```

4. **Run the bot**:
   ```bash
   # Single run
   python scripts/promote_next_github.py
   
   # Continuous mode
   python scripts/promote_next_github.py --continuous
   ```

## 🚀 Deployment Options

### GitHub Actions (Recommended for Production)

1. **Set Repository Secrets** in GitHub (Settings > Secrets and variables > Actions):
   - `GITHUB_TOKEN`: Your Personal Access Token
   - `REPO_OWNER`: Your repository owner
   - `REPO_NAME`: Your repository name
   - `LABEL`: Label for bot issues (optional)
   - `ASSIGNEES`: Comma-separated usernames (optional)

2. **Create a Workflow Schedule**:
   ```yaml
   name: GitHub Issue Queue Bot
   on:
     schedule:
       - cron: '*/15 * * * *'  # Every 15 minutes
   jobs:
     promote-issue:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v4
           with:
             python-version: '3.9'
         - run: pip install -r requirements.txt
         - run: python scripts/promote_next_github.py
           env:
             GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
             REPO_OWNER: ${{ secrets.REPO_OWNER }}
             REPO_NAME: ${{ secrets.REPO_NAME }}
             LABEL: ${{ secrets.LABEL }}
             ASSIGNEES: ${{ secrets.ASSIGNEES }}
   ```

### Cron (Linux/Mac)

```bash
# Add to crontab (crontab -e)
*/15 * * * * cd /path/to/pdf-to-issue && python scripts/promote_next_github.py >> /var/log/issuebot.log 2>&1
```

### Docker Container

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "scripts/promote_next_github.py", "--continuous"]
```

```bash
docker build -t github-issue-bot .
docker run -d --restart unless-stopped \
  -e GITHUB_TOKEN=your_token \
  -e REPO_OWNER=your-username \
  -e REPO_NAME=your-repo \
  github-issue-bot
```

## 🔧 Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | ✅ | - | Personal Access Token with `repo` scope |
| `REPO_OWNER` | ✅ | - | GitHub repository owner (username/org) |
| `REPO_NAME` | ✅ | - | GitHub repository name |
| `GITHUB_URL` | ❌ | `https://api.github.com` | GitHub API URL |
| `LABEL` | ❌ | `auto-generated` | Label for bot-created issues |
| `ASSIGNEES` | ❌ | - | Comma-separated usernames |
| `POLL_INTERVAL` | ❌ | `900` | Seconds between checks (continuous mode) |

## 🎯 Bot Logic Deep Dive

### Issue Completion Detection

The bot uses sophisticated logic to determine if an issue is "done":

1. **Check Issue State**: Issue must be in "closed" state
2. **Find Closing Event**: Analyze timeline to find what closed the issue
3. **PR Verification**: If closed by PR, verify the PR was merged (not just closed)
4. **Manual Close Handling**: If manually closed (no PR), consider it complete

### File Sequencing

- Scans `issues/` directory for `.md` files
- Extracts numbers from filenames (e.g., `001-title.md` → `1`)
- Finds the next available number after the last processed issue
- Handles gaps in numbering gracefully

### Error Handling

- **API Rate Limits**: Respects GitHub API rate limits
- **Network Issues**: Retries with exponential backoff
- **Permission Errors**: Clear error messages for troubleshooting
- **File Issues**: Validates markdown files before processing

## 📊 Monitoring & Logs

### Log Files

- `logs/promote_next.log`: Detailed bot activity
- Console output: Summary information

### Key Log Events

```
🔄 Checking for next issue to promote...
✅ Previous issue #42 is complete
🆕 Created issue #43: https://github.com/owner/repo/issues/43
🟡 Previous issue still in progress - waiting
✅ Queue is empty - no more issues to promote
```

### GitHub Actions Artifacts

- Logs stored as workflow artifacts
- Available for download from Actions tab
- Useful for debugging deployment issues

## 🛠️ Troubleshooting

### Common Issues

**"No issues found"**
- Check the `LABEL` matches your intended label
- Verify repository permissions
- Run `python scripts/test_github.py` to diagnose

**"Previous issue still in progress"**
- Check if the last issue is actually closed
- Verify the closing PR is merged (not just closed)
- Manual closes without PRs are considered complete

**"Could not extract number from issue title"**
- Ensure issue titles start with numbers: `001-title`
- Bot looks for patterns like `001-` or `001 `

**API Permission Errors**
- Verify `GITHUB_TOKEN` has `repo` scope
- Check repository access permissions
- Test with `python scripts/test_github.py`

### Debug Mode

Run with increased logging:

```bash
# Linux/Mac
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python scripts/promote_next_github.py

# Windows
set PYTHONPATH=.
python scripts/promote_next_github.py
```

---

# 🧪 Testing & Validation

The GitHub bot includes comprehensive testing to ensure reliability and correctness.

## 🚀 Quick Test Run

### Windows (Recommended)
```cmd
# Run all safe tests (unit + mock integration)
run-tests.bat

# Run specific test types
run-tests.bat unit        # Unit tests only
run-tests.bat mock        # Mock integration tests only
run-tests.bat integration # Real GitHub API tests (requires credentials)
```

### Command Line
```bash
# Install test dependencies
pip install -r requirements.txt

# Run all safe tests
python tests/test_runner.py --all

# Run specific test suites
python tests/test_runner.py --unit
python tests/test_runner.py --mock
```

## 🧬 Test Types

| Test Type | Purpose | Requirements | Safety |
|-----------|---------|--------------|--------|
| **Unit Tests** | Test individual functions | None | ✅ Safe |
| **Mock Integration** | Test full workflows with fake API | None | ✅ Safe |
| **Real Integration** | Test against actual GitHub | GitHub token & repo | ⚠️ Creates real issues |

## 🎯 Test Coverage

The test suite validates:
- ✅ Issue completion detection (open/closed/merged PR logic)
- ✅ File sequencing and numbering
- ✅ Manual close vs PR-based close handling  
- ✅ Waiting for unmerged PRs
- ✅ Empty queue detection
- ✅ API error handling
- ✅ Edge cases (gaps in numbering, malformed files)

---

# 🚀 VS Code Development Setup

This project includes a complete VS Code development environment with debugging configurations, tasks, and GitHub Actions integration.

## 🎯 Launch Configurations

Press `F5` or use `Run and Debug` panel to access these configurations:

### Testing Configurations
- **🧪 Run All Tests (Safe)** - Unit + Mock tests (no credentials needed)
- **🔬 Run Unit Tests Only** - Fast isolated function tests
- **🎭 Run Mock Integration Tests** - Full workflow tests with fake API
- **🌐 Real GitHub Integration Tests** - Tests against actual GitHub (requires credentials)

### Bot Configurations  
- **🧰 Test GitHub Connection** - Validate credentials and repository access
- **🤖 Run GitHub Bot (Single)** - Promote one issue and exit
- **🤖 Run GitHub Bot (Continuous)** - Run bot in loop mode (60s intervals)

### Legacy/Utility Configurations
- **🔗 Start Mock GitLab Server** - Run standalone mock server for testing
- **Extract Issues from PDF** - Original PDF extraction functionality
- **🧰 Test GitLab Connection** - Legacy GitLab testing
- **🤖 Run GitLab Bot** - Legacy GitLab bot versions

## 🔐 Credential Management

### For Testing (Safe)
Most test configurations use dummy credentials and don't require real GitHub access.

### For Real GitHub Integration
When using GitHub configurations, you'll be prompted for:

| Input | Description | Example |
|-------|-------------|---------|
| **GitHub Token** | Personal Access Token with `repo` scope | `ghp_xxxxxxxxxxxx` |
| **Repository Owner** | Username or organization name | `octocat` |
| **Repository Name** | Repository name (not full path) | `Hello-World` |
| **GitHub URL** | API URL | `https://api.github.com` |
| **Label** | Bot issue label | `auto-generated` |
| **Assignees** | Usernames to assign (optional) | `alice,bob` |

### Security Notes
- 🔒 Tokens are marked as `password: true` (hidden input)
- 🚫 Credentials are **never stored** in files
- ✅ Each run prompts for fresh credentials
- 💡 Use dedicated test repositories for integration tests

## 🌐 GitHub Actions Integration

The project includes GitHub Actions workflows for:

- ✅ **Automatic testing** on push/PR
- 🖥️ **Cross-platform testing** (Windows, macOS, Linux) 
- 🐍 **Multi-Python version testing** (3.8-3.11)
- 🔍 **Code quality checks** (linting, formatting)
- 🌐 **Optional integration testing** with GitHub

### GitHub Secrets Setup
For integration tests, configure these repository secrets:

| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `TEST_REPO_OWNER` | Test repository owner |
| `TEST_REPO_NAME` | Test repository name |
| `GITHUB_URL` | GitHub API URL (optional) |

## 💡 Pro Tips

### Quick Testing Workflow
1. **Development**: Use "🧪 Run All Tests (Safe)" for fast feedback
2. **Debugging**: Add breakpoints and use specific launch configs
3. **Integration**: Use "🧰 Test GitHub Connection" before real tests
4. **CI/CD**: GitHub Actions runs automatically on commits

### Efficient Development
- **Auto-format**: Files format on save with Black
- **Auto-test**: Tests auto-discover and run on save
- **IntelliSense**: Full Python auto-completion and type hints
- **Integrated Terminal**: Automatically activates virtual environment

This setup provides a complete development environment optimized for the GitHub Issue Queue Bot! 🎉

---

## 📋 Dependencies

- `PyPDF2>=3.0.1`: PDF text extraction
- `requests>=2.28.0`: HTTP API calls to GitHub

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Run the test suite
5. Submit a pull request

## 📄 License

This project is provided as-is for extracting GitHub issues from ChatGPT PDF exports. Use responsibly and in accordance with ChatGPT's terms of service.

## 💡 Tips for Best Results

1. **Structure your ChatGPT conversation**: Ask ChatGPT to format issues consistently
2. **Use clear section headers**: Ensure each issue has "### Title", "### Description", etc.
3. **Keep issues focused**: One issue per markdown code block works best
4. **Review before extraction**: Check your ChatGPT output before exporting to PDF
5. **Batch processing**: You can process multiple PDFs by running the script multiple times

## 🔄 Workflow Integration

This tool fits perfectly into a development workflow:

1. **Planning Phase**: Use ChatGPT to brainstorm and structure project issues
2. **Export**: Download the conversation as PDF
3. **Extract**: Use this tool to convert to individual Markdown files
4. **Import**: Let the bot automatically create GitHub issues one at a time
5. **Develop**: Work through the issues systematically with proper pacing

Perfect for project planning, feature brainstorming, and systematic development approaches!

---

*Ready to streamline your GitHub issue management? Start with the PDF extraction, then let the bot handle the rest! 🚀*
