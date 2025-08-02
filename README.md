# PDF to GitHub Issues Extractor + GitLab Queue Bot

A Python tool to extract GitHub issues from ChatGPT PDF exports and convert them into numbered, GitHub-ready Markdown files. Now includes a GitLab bot that automatically promotes issues one at a time, waiting for each to be completed before creating the next.

## 🎯 Purpose

This tool solves two key problems:

1. **PDF to Markdown**: Converting ChatGPT conversation exports (PDFs) that contain GitHub issue specifications into properly formatted, individual Markdown files ready for GitHub import.

2. **Automated GitLab Queue**: A bot that promotes these Markdown files to GitLab issues one at a time, ensuring each issue is completed (closed by a merged MR) before creating the next one.

Perfect for when you've had ChatGPT help you generate a comprehensive list of GitHub issues for your project and want to manage them systematically in GitLab.

## ✨ Features

### PDF Extraction Features
- **PDF Text Extraction**: Extracts text from ChatGPT PDF exports using PyPDF2
- **Intelligent Issue Parsing**: Automatically identifies and separates individual GitHub issues from the PDF content
- **GitHub-Ready Formatting**: Converts issues to proper Markdown format with standardized sections
- **Unicode Sanitization**: Handles emojis and special characters from ChatGPT output
- **Numbered Output**: Creates sequentially numbered files (001-title.md, 002-title.md, etc.)
- **Comprehensive Logging**: Detailed logging for debugging and monitoring extraction progress
- **Error Handling**: Robust error handling for various PDF formats and content structures

### GitLab Queue Bot Features
- **Sequential Processing**: Creates GitLab issues one at a time in numerical order
- **Merge Gate**: Waits for issues to be closed by merged MRs before proceeding
- **Smart Status Checking**: Differentiates between manual closes and MR-based closes
- **Automatic Assignment**: Can auto-assign issues to specified users
- **Label Management**: Tags all bot-created issues with a configurable label
- **Multiple Deployment Options**: GitLab CI/CD, cron, or Docker container
- **Comprehensive Logging**: Detailed audit trail of all bot actions

## 📁 Project Structure

```
pdf-to-issue/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .gitlab-ci.yml              # GitLab CI/CD pipeline for bot automation
├── .env.example                # Configuration template
├── run-bot.bat                 # Windows batch runner for the bot
├── scripts/
│   ├── extract_issues.py       # PDF extraction script
│   ├── promote_next.py         # GitLab queue bot (main script)
│   ├── test_gitlab.py          # GitLab connection test
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
    └── promote_next.log        # GitLab bot logs
```

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Installation

1. **Clone or download this repository**:
   ```bash
   git clone <repository-url>
   cd pdf-to-issue
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

1. **Export your ChatGPT conversation to PDF**:
   - In ChatGPT, click the share button on your conversation
   - Select "Export" and choose PDF format
   - Save the PDF file to the `chat_exports/` directory

2. **Run the extraction script**:
   ```bash
   python scripts/extract_issues.py chat_exports/your-chatgpt-export.pdf
   ```

3. **Find your extracted issues**:
   - Generated Markdown files will be in the `issues/` directory
   - Files are numbered sequentially: `001-title.md`, `002-title.md`, etc.
   - Check `logs/extract_issues.log` for detailed extraction information

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

## 🔧 Advanced Usage

### Command Line Options

```bash
# Basic usage
python scripts/extract_issues.py <pdf_file>

# Example with full path
python scripts/extract_issues.py "C:\path\to\your\chatgpt-export.pdf"
```

### Logging Levels

The script provides comprehensive logging:
- **Console Output**: Shows progress and summary information
- **Log File**: Detailed debug information in `logs/extract_issues.log`

### Unicode Handling

The tool automatically converts common ChatGPT emojis and Unicode characters:
- 🔹 → `- ` (bullet points)
- ✅ → `[x] ` (checkmarks)
- 🚀 → `-> ` (arrows)
- 💡 → `* ` (ideas)

## 🛠️ Troubleshooting

### Common Issues

1. **No issues found in PDF**:
   - Ensure your ChatGPT conversation contains markdown code blocks with GitHub issues
   - Check that issues start with "### Title"
   - Verify the PDF exported correctly from ChatGPT

2. **PDF reading errors**:
   - Ensure the PDF file isn't corrupted
   - Try re-exporting from ChatGPT
   - Check file permissions

3. **Unicode/encoding errors**:
   - The tool handles most Unicode characters automatically
   - Check the log file for details about character replacements

### Getting Help

1. **Check the logs**: Look at `logs/extract_issues.log` for detailed error information
2. **Verify PDF content**: Manually check that your PDF contains the expected issue format
3. **Test with sample data**: Try the tool with the included sample PDFs

## 📊 Example Output

Running the tool on a ChatGPT export with 50 GitHub issues would produce:

```
2025-08-02 10:15:30 - __main__ - INFO - Starting PDF issue extraction
2025-08-02 10:15:30 - __main__ - INFO - Input: chat_exports/project-issues.pdf
2025-08-02 10:15:30 - __main__ - INFO - Output directory: issues
2025-08-02 10:15:31 - __main__ - INFO - PDF has 25 pages
2025-08-02 10:15:32 - __main__ - INFO - Extracted 125000 characters from PDF
2025-08-02 10:15:32 - __main__ - INFO - Found 50 issue sections
2025-08-02 10:15:33 - __main__ - INFO - ✅ Created: issues/001-set-up-authentication-system.md
2025-08-02 10:15:33 - __main__ - INFO - ✅ Created: issues/002-implement-user-dashboard.md
...
2025-08-02 10:15:35 - __main__ - INFO - ✅ Created: issues/050-add-performance-monitoring.md
2025-08-02 10:15:35 - __main__ - INFO - Successfully processed 50 out of 50 issues
```

## 📋 Dependencies

- **PyPDF2==3.0.1**: PDF text extraction
- **requests>=2.28.0**: HTTP API calls to GitLab
- **Python 3.7+**: Core runtime

## 🤝 Contributing

This tool was created to solve a specific workflow problem. If you encounter issues or have improvements:

1. Check the existing issues in the repository
2. Create a detailed bug report or feature request
3. Include sample PDF files (anonymized) that demonstrate the problem

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
4. **Import**: Upload the generated files to your GitHub repository as issues
5. **Develop**: Work through the issues systematically

Perfect for project planning, feature brainstorming, and systematic development approaches!

---

# 🤖 GitLab Queue Bot

The GitLab Queue Bot automatically promotes your numbered Markdown files to GitLab issues, but with a crucial twist: it only creates the next issue after the previous one has been **closed by a merged MR**. This ensures a steady, manageable workflow that prevents issue overload.

## 🔄 How It Works

1. **Check Last Issue**: Looks for the most recent bot-created issue
2. **Verify Completion**: Ensures it's closed AND the closing MR is merged
3. **Find Next File**: Locates the next numbered Markdown file
4. **Create Issue**: Posts it to GitLab with proper labels and assignments
5. **Wait**: Sleeps until the next poll cycle

## ⚙️ Quick Setup

### Prerequisites

- GitLab Personal Access Token with `api` scope
- Numeric GitLab Project ID
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
   GITLAB_TOKEN=your_token_here
   PROJECT_ID=123456
   LABEL=auto-generated
   ASSIGNEES=username1,username2
   ```

3. **Test connection**:
   ```bash
   python scripts/test_gitlab.py
   ```

4. **Run the bot**:
   ```bash
   # Single run
   python scripts/promote_next.py
   
   # Continuous mode
   python scripts/promote_next.py --continuous
   ```

## 🚀 Deployment Options

### GitLab CI/CD (Recommended for Production)

1. **Set CI/CD Variables** in GitLab (Settings > CI/CD > Variables):
   - `GITLAB_TOKEN`: Your Personal Access Token
   - `PROJECT_ID`: Your project's numeric ID
   - `LABEL`: Label for bot issues (optional)
   - `ASSIGNEES`: Comma-separated usernames (optional)

2. **Create a Pipeline Schedule**:
   - Go to CI/CD > Schedules
   - Click "New schedule"
   - Set interval: `*/15 * * * *` (every 15 minutes)
   - Target branch: `main` or `master`

3. **Push the `.gitlab-ci.yml`** - it's already configured!

### Cron (Linux/Mac)

```bash
# Add to crontab (crontab -e)
*/15 * * * * cd /path/to/pdf-to-issue && python scripts/promote_next.py >> /var/log/issuebot.log 2>&1
```

### Docker Container

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "scripts/promote_next.py", "--continuous"]
```

```bash
docker build -t gitlab-issue-bot .
docker run -d --restart unless-stopped \
  -e GITLAB_TOKEN=your_token \
  -e PROJECT_ID=123456 \
  gitlab-issue-bot
```

## 🔧 Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITLAB_TOKEN` | ✅ | - | Personal Access Token with `api` scope |
| `PROJECT_ID` | ✅ | - | Numeric GitLab project ID |
| `GITLAB_URL` | ❌ | `https://gitlab.com` | GitLab instance URL |
| `LABEL` | ❌ | `auto-generated` | Label for bot-created issues |
| `ASSIGNEES` | ❌ | - | Comma-separated usernames |
| `POLL_INTERVAL` | ❌ | `900` | Seconds between checks (continuous mode) |

## 🎯 Bot Logic Deep Dive

### Issue Completion Detection

The bot considers an issue "done" when:

1. **Issue is closed** (`state == "closed"`)
2. **AND** one of these conditions:
   - No closing MR (manual close) → Considered done
   - Closing MR exists AND is merged → Considered done
   - Closing MR exists BUT not merged → **NOT done** (keeps waiting)

### File Number Mapping

- Bot extracts numbers from issue titles: `"001-setup-auth"` → `1`
- Looks for next file: `issues/002-*.md`
- If file doesn't exist, bot stops and logs error

### Error Handling

- **API failures**: Retries with exponential backoff
- **Missing files**: Logs error and stops (manual intervention needed)
- **Permission issues**: Clear error messages with troubleshooting hints

## 📊 Monitoring & Logs

### Log Files

- `logs/promote_next.log`: Detailed bot activity
- Console output: Summary information

### Key Log Events

```
🔄 Checking for next issue to promote...
✅ Previous issue #42 is complete
🆕 opened https://gitlab.com/project/issues/43
🟡 Previous issue still in progress - waiting
✅ Queue is empty - no more issues to promote
```

### GitLab CI/CD Artifacts

- Logs stored as pipeline artifacts
- Available for 1 week after each run
- Download from GitLab UI for debugging

## 🛠️ Troubleshooting

### Common Issues

**"No issues found"**
- Check the `LABEL` matches your intended label
- Verify project permissions
- Run `python scripts/test_gitlab.py` to diagnose

**"Previous issue still in progress"**
- Check if the last issue is actually closed
- Verify the closing MR is merged (not just closed)
- Manual closes without MRs are considered complete

**"Could not extract number from issue title"**
- Ensure issue titles start with numbers: `001-title`
- Bot looks for patterns like `001-` or `001 `

**API Permission Errors**
- Verify `GITLAB_TOKEN` has `api` scope
- Check project membership and permissions
- Test with `python scripts/test_gitlab.py`

### Debug Mode

Run with increased logging:

```bash
# Linux/Mac
export PYTHONPATH=.
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python scripts/promote_next.py

# Windows
set PYTHONPATH=.
python scripts/promote_next.py
```

## 🔄 Workflow Integration

### Complete Development Workflow

1. **Planning**: Use ChatGPT to generate comprehensive issue list
2. **Extract**: Run `python scripts/extract_issues.py your-export.pdf`
3. **Review**: Check generated Markdown files in `issues/`
4. **Configure**: Set up GitLab bot with your project credentials
5. **Deploy**: Enable GitLab CI/CD schedule or run continuously
6. **Develop**: Work on issues as they're created automatically
7. **Complete**: Merge MRs to trigger next issue creation

### Team Workflow Benefits

- **Prevents overwhelm**: Only one active issue at a time
- **Ensures completion**: Forces proper issue closure process
- **Maintains momentum**: Continuous steady progress
- **Reduces context switching**: Focus on current task
- **Audit trail**: Clear history of what was worked on when

Perfect for solo developers, small teams, or anyone who wants structured, systematic project execution!

---

# 🧪 Testing & Validation

The GitLab bot includes comprehensive testing to ensure reliability and correctness.

## 🚀 Quick Test Run

### Windows (Recommended)
```cmd
# Run all safe tests (unit + mock integration)
run-tests.bat

# Run specific test types
run-tests.bat unit        # Unit tests only
run-tests.bat mock        # Mock integration tests only
run-tests.bat integration # Real GitLab API tests (requires credentials)
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
| **Real Integration** | Test against actual GitLab | GitLab token & project | ⚠️ Creates real issues |

## 🎯 Test Coverage

The test suite validates:
- ✅ Issue completion detection (open/closed/merged MR logic)
- ✅ File sequencing and numbering
- ✅ Manual close vs MR-based close handling  
- ✅ Waiting for unmerged MRs
- ✅ Empty queue detection
- ✅ API error handling
- ✅ Edge cases (gaps in numbering, malformed files)

## 🔍 Mock GitLab Server

For safe testing without real API calls:
- Complete GitLab API simulation
- State management across requests
- Pre-configured test scenarios
- No external dependencies

See [`docs/TESTING.md`](docs/TESTING.md) for detailed testing documentation.

---

# 🚀 VS Code Development Setup

The project includes comprehensive VS Code configurations for easy development and testing.

## 🎯 Launch Configurations

Press `F5` or use `Run and Debug` panel to access these configurations:

### Testing Configurations
- **🧪 Run All Tests (Safe)** - Unit + Mock tests (no credentials needed)
- **🔬 Run Unit Tests Only** - Fast isolated function tests
- **🎭 Run Mock Integration Tests** - Full workflow tests with fake GitLab API
- **🌐 Real GitLab Integration Tests** - Tests against actual GitLab (requires credentials)

### Bot Configurations  
- **🧰 Test GitLab Connection** - Validate credentials and project access
- **🤖 Run GitLab Bot (Single)** - Promote one issue and exit
- **🤖 Run GitLab Bot (Continuous)** - Run bot in loop mode (60s intervals)

### Utility Configurations
- **🔗 Start Mock GitLab Server** - Run standalone mock server for testing
- **Extract Issues from PDF** - Original PDF extraction functionality

## ⚙️ Quick Setup

1. **Open in VS Code**: `code .` from project directory
2. **Install Python Extension**: VS Code will prompt if not installed
3. **Select Python Interpreter**: VS Code will auto-detect `.venv` or system Python
4. **Run Tests**: Press `F5` → Select "🧪 Run All Tests (Safe)"

## 🔐 Credential Management

### For Testing (Safe)
Most test configurations use dummy credentials and don't require real GitLab access.

### For Real GitLab Integration
When using GitLab configurations, you'll be prompted for:

| Input | Description | Example |
|-------|-------------|---------|
| **GitLab Token** | Personal Access Token with `api` scope | `glpat-xxxxxxxxxxxx` |
| **Project ID** | Numeric project ID (not name) | `12345678` |
| **GitLab URL** | Instance URL | `https://gitlab.com` |
| **Label** | Bot issue label | `auto-generated` |
| **Assignees** | Usernames to assign (optional) | `alice,bob` |

### Security Notes
- 🔒 Tokens are marked as `password: true` (hidden input)
- 🚫 Credentials are **never stored** in files
- ✅ Each run prompts for fresh credentials
- 💡 Use dedicated test projects for integration tests

## 🛠️ VS Code Tasks

Use `Ctrl+Shift+P` → "Tasks: Run Task" to access:

- **🧪 Run All Tests** - Quick test execution
- **🔬 Run Unit Tests** - Fast unit test subset
- **🎭 Run Mock Tests** - Mock integration tests
- **📦 Install Dependencies** - `pip install -r requirements.txt`
- **🧹 Clean Test Artifacts** - Remove `__pycache__` and logs
- **🚀 Setup GitLab Bot** - Run PowerShell setup script
- **🔧 Test GitLab Connection** - Validate credentials

## 🐞 Debugging

### Breakpoints
- Set breakpoints in any Python file
- Use debug configurations to step through code
- Variables panel shows current state

### Common Debug Scenarios
1. **Test Failures**: Use "🔬 Run Unit Tests Only" with breakpoints
2. **Bot Logic**: Use "🤖 Run GitLab Bot (Single)" to debug promotion logic
3. **API Issues**: Use "🧰 Test GitLab Connection" to debug credentials
4. **Mock Server**: Use "🔗 Start Mock GitLab Server" to inspect API simulation

### Debug Environment Variables
All debug configurations automatically set:
```env
GITLAB_TOKEN=test-token     # For safe tests
PROJECT_ID=12345           # For safe tests  
LABEL=test-bot            # Avoid conflicts
```

## 📁 File Organization

```
.vscode/
├── launch.json           # Debug configurations
├── tasks.json           # Task definitions  
└── settings.json        # Project settings

.github/workflows/
└── test.yml            # GitHub Actions CI/CD

.gitlab-ci.yml          # GitLab CI/CD pipeline
```

## 🌐 GitHub Actions Integration

The project includes GitHub Actions workflows for:

- ✅ **Automatic testing** on push/PR
- 🖥️ **Cross-platform testing** (Windows, macOS, Linux) 
- 🐍 **Multi-Python version testing** (3.8-3.11)
- 🔍 **Code quality checks** (linting, formatting)
- 🌐 **Optional integration testing** with GitLab

### GitHub Secrets Setup
For integration tests, configure these repository secrets:

| Secret | Description |
|--------|-------------|
| `GITLAB_TOKEN` | GitLab Personal Access Token |
| `TEST_PROJECT_ID` | Numeric ID of test project |
| `GITLAB_URL` | GitLab instance URL (optional) |

## 💡 Pro Tips

### Quick Testing Workflow
1. **Development**: Use "🧪 Run All Tests (Safe)" for fast feedback
2. **Debugging**: Add breakpoints and use specific launch configs
3. **Integration**: Use "🧰 Test GitLab Connection" before real tests
4. **CI/CD**: GitHub Actions runs automatically on commits

### Efficient Development
- **Auto-format**: Files format on save with Black
- **Auto-test**: Tests auto-discover and run on save
- **IntelliSense**: Full Python auto-completion and type hints
- **Integrated Terminal**: Automatically activates virtual environment

This setup provides a complete development environment optimized for the GitLab Issue Queue Bot! 🎉
