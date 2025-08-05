# GitHub Label Management for Markdown Issues

This project provides scripts to automatically extract labels from markdown issue files and create them in GitHub repositories.

## Overview

The `extract_and_create_labels.py` script:
1. Reads all markdown files in the `issues/` directory
2. Extracts labels from the `## Labels` or `### Labels` sections
3. Filters out invalid/corrupted labels
4. Checks existing labels in the target GitHub repository
5. Creates missing labels with appropriate colors and descriptions

## Prerequisites

- Python 3.6+
- `requests` library (`pip install requests`)
- GitHub Personal Access Token with `repo` scope

## Installation

1. Clone or download this repository
2. Install requirements:
   ```bash
   pip install requests
   ```
3. Set up your GitHub token (see [GitHub Token Setup](#github-token-setup))

## GitHub Token Setup

You need a GitHub Personal Access Token with `repo` scope:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token"
3. Select the `repo` scope
4. Copy the generated token

Set the token as an environment variable:

**Windows (Command Prompt):**
```cmd
set GITHUB_TOKEN=your_token_here
```

**Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN = "your_token_here"
```

**Linux/Mac:**
```bash
export GITHUB_TOKEN=your_token_here
```

## Usage

### Basic Usage

**Single Repository:**
```bash
python extract_and_create_labels.py --repo owner/repository-name
```

**Multiple Repositories:**
```bash
python extract_and_create_labels.py --repos owner1/repo1 owner2/repo2 owner3/repo3
```

### Command Line Options

- `--repo, -r`: Single repository in format "owner/repo"
- `--repos`: Multiple repositories (space-separated)
- `--token, -t`: GitHub token (if not set as environment variable)
- `--issues-dir, -d`: Directory containing markdown files (default: "issues")
- `--github-url`: GitHub API URL (default: "https://api.github.com")
- `--dry-run`: Preview changes without creating labels

### Examples

**Dry run to preview changes:**
```bash
python extract_and_create_labels.py --repo SoupyOfficial/pdf-to-issue --dry-run
```

**Specify custom issues directory:**
```bash
python extract_and_create_labels.py --repo owner/repo --issues-dir my-issues
```

**Use inline token:**
```bash
python extract_and_create_labels.py --repo owner/repo --token ghp_your_token_here
```

**Process multiple repositories:**
```bash
python extract_and_create_labels.py --repos owner/repo1 owner/repo2 owner/repo3
```

### Using Batch/PowerShell Scripts

**Windows Batch (.bat):**
```cmd
extract-labels.bat SoupyOfficial/pdf-to-issue
extract-labels.bat SoupyOfficial/pdf-to-issue --dry-run
extract-labels.bat --repos owner1/repo1 owner2/repo2
```

**PowerShell (.ps1):**
```powershell
.\extract-labels.ps1 -Repo "SoupyOfficial/pdf-to-issue"
.\extract-labels.ps1 -Repo "SoupyOfficial/pdf-to-issue" -DryRun
.\extract-labels.ps1 -Repos "owner1/repo1","owner2/repo2"
```

## Markdown Issue Format

Your markdown files should contain a labels section:

```markdown
# Issue Title

Description of the issue...

## Labels
feature, ui, enhancement

## Or with ### Labels
### Labels
bug, frontend, high-priority
```

Labels should be:
- Comma-separated
- One label per line or multiple labels on one line
- Free of special characters that would make them invalid GitHub labels

## Label Colors and Descriptions

The script automatically assigns colors and descriptions based on label names:

| Label Type | Color | Example Labels |
|------------|--------|----------------|
| Architecture | Blue (#1f77b4) | architecture, foundation |
| UI/UX | Red/Purple (#d62728, #9467bd) | ui, ux, frontend |
| Data | Brown (#8c564b) | data, database, firestore |
| Features | Green (#00d4aa) | feature, enhancement |
| Analytics | Blue (#0366d6) | analytics, charts |
| Performance | Yellow (#fbca04) | performance, optimization |
| Testing | Purple (#6f42c1) | testing, qa |
| Sync/Offline | Light colors | sync, offline |

Default color is red (#d73a4a) for unrecognized labels.

## Error Handling

The script includes validation to filter out corrupted labels such as:
- Labels starting with numbers (e.g., "264/878")
- Labels containing "Issue" and "?"
- Labels starting with "RUNNING"
- Very long labels (>50 characters)

## Output

The script provides detailed output:
1. Lists all markdown files found
2. Shows labels extracted from each file
3. Displays unique labels to be created
4. Shows existing labels in the repository
5. Creates missing labels with success/failure messages

## Files

- `extract_and_create_labels.py` - Main Python script
- `extract-labels.bat` - Windows batch script wrapper
- `extract-labels.ps1` - PowerShell script wrapper
- `LABELS-README.md` - This documentation file

## Troubleshooting

**"GitHub token is required" error:**
- Set the `GITHUB_TOKEN` environment variable
- Or use `--token` argument

**"Repository must be in format 'owner/repo'" error:**
- Ensure repository format is correct: `username/repository-name`
- Don't include `https://github.com/`

**"Failed to get existing labels" error:**
- Check token permissions (needs `repo` scope)
- Verify repository exists and you have access
- Check if repository name is spelled correctly

**"No labels found in markdown files" error:**
- Ensure markdown files have `## Labels` or `### Labels` sections
- Check that files are in the correct directory
- Verify label format (comma-separated)

## Contributing

Feel free to submit issues and pull requests to improve the script functionality.

## License

This project is provided as-is for educational and productivity purposes.
