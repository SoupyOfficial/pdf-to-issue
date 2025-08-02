#!/usr/bin/env python
"""
Split a ChatGPT PDF export into numbered GitHub-ready Markdown
files.  Usage:
    python scripts/extract_issues.py chat_exports/AshTrail_Chat_Issues.pdf
Output:
    issues/001-some-title.md
    issues/002-another-title.md
…
"""

import re, sys, pathlib, textwrap, logging
from PyPDF2 import PdfReader

# Configure logging with industry best practices
def setup_logging():
    """Configure logging with proper formatting and levels."""
    # Create logs directory if it doesn't exist
    log_dir = pathlib.Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure formatter with timestamp, level, and message
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Console handler for user feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # File handler for detailed logging
    file_handler = logging.FileHandler(
        log_dir / "extract_issues.log", 
        mode='a', 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

def sanitize_text(text):
    """
    Sanitize text to remove problematic Unicode characters while preserving readability.
    
    Args:
        text (str): Input text that may contain Unicode characters
        
    Returns:
        str: Sanitized text safe for file writing
    """
    # Map common Unicode characters to ASCII equivalents
    unicode_replacements = {
        '🔹': '- ',  # Blue diamond bullet point
        '🔸': '- ',  # Orange diamond bullet point  
        '✅': '[x] ',  # Check mark
        '⚠️': '[!] ',  # Warning sign
        '❌': '[x] ',  # Cross mark
        '📝': '* ',   # Memo
        '🚀': '-> ',  # Rocket
        '💡': '* ',   # Light bulb
        '🎯': '* ',   # Target
        '📊': '[chart] ',  # Chart
        '📈': '[trend] ',  # Trending up
        '📉': '[decline] ', # Trending down
        '🔗': '[link] ',   # Link
        '📱': '[mobile] ', # Mobile phone
        '💻': '[desktop] ', # Laptop
        '⭐': '* ',    # Star
        '👍': '[+] ',  # Thumbs up
        '👎': '[-] ',  # Thumbs down
    }
    
    # Replace Unicode characters
    for unicode_char, replacement in unicode_replacements.items():
        text = text.replace(unicode_char, replacement)
    
    # Remove any remaining non-ASCII characters that might cause encoding issues
    # Keep common punctuation and preserve line breaks
    sanitized = ''
    for char in text:
        if ord(char) < 128 or char in '\n\r\t':
            sanitized += char
        else:
            # Log unknown Unicode characters for future handling
            logger.debug(f"Replaced unknown Unicode character: {repr(char)} (U+{ord(char):04X})")
            sanitized += '?'  # Replace with question mark
    
    return sanitized

def extract_pdf_text(pdf_path):
    """
    Extract text from PDF file with error handling.
    
    Args:
        pdf_path (pathlib.Path): Path to PDF file
        
    Returns:
        str: Extracted text from all pages
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        Exception: If PDF reading fails
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    logger.info(f"Reading PDF: {pdf_path}")
    
    try:
        reader = PdfReader(pdf_path)
        logger.info(f"PDF has {len(reader.pages)} pages")
        
        full_text = "\n".join(page.extract_text() for page in reader.pages)
        logger.info(f"Extracted {len(full_text)} characters from PDF")
        
        return full_text
        
    except Exception as e:
        logger.error(f"Failed to read PDF {pdf_path}: {e}")
        raise

def extract_github_issues(text):
    """
    Extract GitHub issues from ChatGPT PDF text by finding sections
    that start with 'markdown' followed by issue specifications.
    
    Args:
        text (str): Full PDF text content
        
    Returns:
        list: List of dictionaries containing parsed issue data
    """
    logger.info("Extracting GitHub issues from PDF text")
    
    issues = []
    
    # Pattern to find sections that start with "markdown" and contain GitHub issues
    # Look for "markdown" followed by "### Title" 
    issue_pattern = r'markdown\s*\n### Title\s*\n(.*?)(?=markdown\s*\n### Title|\Z)'
    
    # Find all issue sections
    issue_matches = re.findall(issue_pattern, text, re.DOTALL | re.IGNORECASE)
    logger.info(f"Found {len(issue_matches)} issue sections")
    
    for match_idx, issue_content in enumerate(issue_matches, 1):
        logger.debug(f"Processing issue section {match_idx}")
        
        # Reconstruct the full issue text (add back the title header)
        full_issue_text = f"### Title\n{issue_content}"
        
        # Parse the issue
        parsed_issue = parse_issue_text(full_issue_text)
        if parsed_issue:
            issues.append(parsed_issue)
            logger.debug(f"Successfully parsed issue: {parsed_issue.get('title', 'Unknown')}")
    
    logger.info(f"Successfully extracted {len(issues)} GitHub issues")
    return issues

def parse_issue_text(text):
    """
    Parse individual GitHub issue text and extract components.
    
    Args:
        text (str): Raw issue text from markdown block
        
    Returns:
        dict: Parsed issue data or None if parsing fails
    """
    issue = {}
    
    # Clean up text by removing RUNNING INDEX sections and other artifacts
    cleaned_text = clean_issue_text(text)
    
    # Extract Title
    title_match = re.search(r'### Title\s*\n(.+?)(?=\n|$)', cleaned_text, re.DOTALL)
    if not title_match:
        logger.warning("No title found in issue text")
        return None
    
    issue['title'] = title_match.group(1).strip()
    
    # Extract Description  
    desc_match = re.search(r'### Description\s*\n(.*?)(?=\n### |\n\*\*Tasks\*\*|\Z)', cleaned_text, re.DOTALL)
    if desc_match:
        issue['description'] = desc_match.group(1).strip()
    
    # Extract Tasks (if present)
    tasks_match = re.search(r'\*\*Tasks\*\*\s*\n(.*?)(?=\n### |\Z)', cleaned_text, re.DOTALL)
    if tasks_match:
        issue['tasks'] = tasks_match.group(1).strip()
    
    # Extract Acceptance Criteria
    criteria_match = re.search(r'### Acceptance Criteria\s*\n(.*?)(?=\n### |\Z)', cleaned_text, re.DOTALL)
    if criteria_match:
        issue['acceptance_criteria'] = criteria_match.group(1).strip()
    
    # Extract Labels
    labels_match = re.search(r'### Labels\s*\n(.+?)(?=\n### |\n\*\*|$)', cleaned_text, re.DOTALL)
    if labels_match:
        issue['labels'] = labels_match.group(1).strip()
    
    return issue if issue.get('title') else None

def clean_issue_text(text):
    """
    Clean issue text by removing ChatGPT artifacts and unwanted sections.
    Improved version that preserves content and handles whitespace properly.
    
    Args:
        text (str): Raw issue text
        
    Returns:
        str: Cleaned issue text with proper formatting
    """
    logger.debug("Cleaning issue text with improved algorithm")
    
    # Step 1: Remove RUNNING INDEX sections and their associated content
    # This is the most aggressive step - remove the entire RUNNING INDEX block
    text = re.sub(r'\d+/\d+[🔹🔸]?\s*RUNNING INDEX.*?(?=Introduce|### |$)', '', text, flags=re.DOTALL)
    
    # Step 2: Remove the numbered index items that come after RUNNING INDEX
    # Remove lines like "#1 Set up Clean Architecture Foundation"
    text = re.sub(r'#\d+\s+[^\n]*\n?', '', text)
    
    # Step 3: Remove index truncation messages
    text = re.sub(r'\(index truncated.*?\)\n?', '', text, flags=re.DOTALL)
    
    # Step 4: Remove estimate sections
    text = re.sub(r'### Estimate\s*\n.*?(?=\n### |\Z)', '', text, flags=re.DOTALL)
    
    # Step 5: Remove "markdown" artifacts
    text = re.sub(r'\nmarkdown\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^markdown\s*\n', '', text, flags=re.MULTILINE)
    
    # Step 6: Remove other ChatGPT artifacts
    text = re.sub(r'BEGIN:VEVENT.*?END:VEVENT', '', text, flags=re.DOTALL)
    text = re.sub(r'Got it! I.*?redesign\.', '', text, flags=re.DOTALL)
    text = re.sub(r'Time to generate.*?redesign\.', '', text, flags=re.DOTALL)
    text = re.sub(r'You.*?task is to generate.*?until', '', text, flags=re.DOTALL)
    text = re.sub(r'\? Issue \d+ delivered.*?(?=\n- \[|### |\Z)', '', text, flags=re.DOTALL)
    text = re.sub(r'\? Issue \d+ delivered.*?next run in.*?min\.', '', text, flags=re.DOTALL)
    
    # Step 7: Fix text that got concatenated without proper spacing
    # Handle cases where content got smashed together
    text = re.sub(r'([a-z])([A-Z][a-z])', r'\1 \2', text)  # Add space between camelCase breaks
    text = re.sub(r'Dashboard([A-Z])', r'Dashboard\n\n\1', text)  # Fix Dashboard concatenation
    text = re.sub(r'\.compile without warnings', '. compile without warnings', text)
    text = re.sub(r'min\.compile', 'min. compile', text)
    
    # Step 8: Fix broken words from PDF extraction
    text = re.sub(r'S witching', 'Switching', text)
    text = re.sub(r'R olling', 'Rolling', text)
    text = re.sub(r'T able', 'Table', text)
    text = re.sub(r'S tats', 'Stats', text)
    text = re.sub(r'Lo gs', 'Logs', text)
    text = re.sub(r'Lo o', 'Loo', text)
    
    # Step 9: Clean up whitespace and formatting
    # Remove excessive spaces and normalize line breaks
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space
    text = re.sub(r' \n', '\n', text)    # Remove trailing spaces before newlines
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double newlines max
    
    # Step 10: Ensure proper section spacing
    # Add proper spacing around section headers
    text = re.sub(r'\n(### [^\n]+)\n', r'\n\n\1\n', text)
    text = re.sub(r'\n(\*\*Tasks\*\*)\n', r'\n\n\1\n', text)
    
    # Step 11: Remove duplicate ### Labels sections
    text = re.sub(r'(### Labels[^\n]*\n)(.*?\n)(### Labels[^\n]*\n)', r'\1\2', text, flags=re.DOTALL)
    
    # Step 12: Clean up final whitespace
    text = text.strip()
    
    logger.debug("Issue text cleaning completed")
    return text

def format_issue_markdown(issue):
    """
    Format parsed issue data into clean GitHub-ready markdown.
    
    Args:
        issue (dict): Parsed issue data
        
    Returns:
        str: Formatted markdown content
    """
    markdown_parts = []
    
    # Title (as H1 for the filename, but we'll use the title as-is)
    markdown_parts.append(issue['title'])
    markdown_parts.append('')
    
    # Title section
    markdown_parts.append('### Title')
    markdown_parts.append(issue['title'])
    markdown_parts.append('')
    
    # Description
    if issue.get('description'):
        markdown_parts.append('### Description')
        markdown_parts.append(issue['description'])
        markdown_parts.append('')
    
    # Tasks
    if issue.get('tasks'):
        markdown_parts.append('**Tasks**')
        markdown_parts.append(issue['tasks'])
        markdown_parts.append('')
    
    # Acceptance Criteria
    if issue.get('acceptance_criteria'):
        markdown_parts.append('### Acceptance Criteria')
        markdown_parts.append(issue['acceptance_criteria'])
        markdown_parts.append('')
    
    # Labels
    if issue.get('labels'):
        markdown_parts.append('### Labels')
        markdown_parts.append(issue['labels'])
    
    return '\n'.join(markdown_parts)

def process_issues(issues, output_dir):
    """
    Process extracted issues and create markdown files.
    
    Args:
        issues (list): List of parsed issue dictionaries
        output_dir (pathlib.Path): Directory to write output files
        
    Returns:
        int: Number of successfully processed files
    """
    processed_count = 0
    
    for idx, issue in enumerate(issues, start=1):
        title = issue.get('title', f'untitled-issue-{idx}')
        logger.debug(f"Processing issue {idx}/{len(issues)}: {title}")
        
        # Create filename slug from title
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        
        # Format the issue as clean markdown
        markdown_content = format_issue_markdown(issue)
        
        # Sanitize the content to handle Unicode characters
        sanitized_content = sanitize_text(markdown_content)
        
        out_file = output_dir / f"{idx:03d}-{slug}.md"
        
        try:
            # Write with explicit UTF-8 encoding
            out_file.write_text(sanitized_content, encoding='utf-8')
            logger.info(f"✅ Created: {out_file.relative_to(output_dir.parent)}")
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to write file {out_file}: {e}")
            continue
    
    return processed_count

def main():
    """Main function with comprehensive error handling."""
    try:
        if len(sys.argv) != 2:
            logger.error("Usage: python scripts/extract_issues.py <pdf_file>")
            sys.exit(1)
        
        PDF_PATH = pathlib.Path(sys.argv[1])
        OUT_DIR = pathlib.Path("issues")
        
        logger.info("Starting PDF issue extraction")
        logger.info(f"Input: {PDF_PATH}")
        logger.info(f"Output directory: {OUT_DIR}")
        
        # Create output directory
        OUT_DIR.mkdir(exist_ok=True)
        logger.debug(f"Created/verified output directory: {OUT_DIR}")

        # Extract PDF text
        full_text = extract_pdf_text(PDF_PATH)
        
        # Extract GitHub issues from the PDF text
        issues = extract_github_issues(full_text)
        
        if not issues:
            logger.warning("No GitHub issues found in PDF")
            return
        
        # Process issues and create files
        processed_count = process_issues(issues, OUT_DIR)
        
        logger.info(f"Successfully processed {processed_count} out of {len(issues)} issues")
        
        if processed_count == 0:
            logger.error("No issues were successfully extracted")
            sys.exit(1)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
