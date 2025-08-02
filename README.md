# PDF to GitHub Issues Extractor

A Python tool to extract GitHub issues from ChatGPT PDF exports and convert them into numbered, GitHub-ready Markdown files.

## 🎯 Purpose

This tool solves the problem of converting ChatGPT conversation exports (PDFs) that contain GitHub issue specifications into properly formatted, individual Markdown files ready for GitHub import. Perfect for when you've had ChatGPT help you generate a comprehensive list of GitHub issues for your project.

## ✨ Features

- **PDF Text Extraction**: Extracts text from ChatGPT PDF exports using PyPDF2
- **Intelligent Issue Parsing**: Automatically identifies and separates individual GitHub issues from the PDF content
- **GitHub-Ready Formatting**: Converts issues to proper Markdown format with standardized sections
- **Unicode Sanitization**: Handles emojis and special characters from ChatGPT output
- **Numbered Output**: Creates sequentially numbered files (001-title.md, 002-title.md, etc.)
- **Comprehensive Logging**: Detailed logging for debugging and monitoring extraction progress
- **Error Handling**: Robust error handling for various PDF formats and content structures

## 📁 Project Structure

```
pdf-to-issue/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── scripts/
│   └── extract_issues.py       # Main extraction script
├── chat_exports/               # Place your ChatGPT PDF exports here
│   ├── AshTrail - GitHub Issue Creation.pdf
│   └── [your-pdf-files].pdf
├── issues/                     # Generated GitHub issues (output)
│   ├── 001-set-up-clean-architecture-foundation.md
│   ├── 002-implement-multi-account-user-switching.md
│   └── [numbered-issues].md
└── logs/
    └── extract_issues.log      # Extraction logs
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
