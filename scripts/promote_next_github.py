#!/usr/bin/env python3
"""
GitHub Issue Queue Bot - Promotes one issue at a time
====================================================

Promotes numbered Markdown files from issues/ directory to GitHub issues,
but only after the previous issue has been closed by a merged PR.

Environment Variables Required:
- GITHUB_TOKEN: Personal Access Token with 'repo' scope
- REPO_OWNER: GitHub repository owner (username or organization)
- REPO_NAME: GitHub repository name

Optional Environment Variables:
- GITHUB_URL: GitHub instance URL (default: https://api.github.com)
- LABEL: Bot tracking label to identify bot-created issues (default: auto-generated)
- ASSIGNEES: Comma-separated GitHub usernames to assign (default: none)
- POLL_INTERVAL: Sleep interval in seconds for continuous mode (default: 900 = 15min)

Note: The bot will also read and apply labels from each issue's "## Labels" section,
creating any labels that don't exist in the repository.
"""

import hashlib
import json
import logging
import os
import pathlib
import re
import sys
import time
from typing import Any, Dict, List, Optional

import requests

# Configuration from environment
GITHUB_URL = os.environ.get("GITHUB_URL", "https://api.github.com")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
REPO_OWNER = os.environ.get("REPO_OWNER", "").strip()
REPO_NAME = os.environ.get("REPO_NAME", "").strip()
LABEL = os.environ.get("LABEL", "auto-generated").strip()
ASSIGNEES = [u.strip() for u in os.environ.get("ASSIGNEES", "").split(",") if u.strip()]
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "900"))  # 15 minutes

# Paths
ISSUES_DIR = pathlib.Path("issues")
LOG_DIR = pathlib.Path("logs")

# Setup logging
LOG_DIR.mkdir(exist_ok=True)

# Configure console handler to avoid Unicode issues on Windows
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Set console encoding to UTF-8 if possible, fallback to basic ASCII
try:
    console_handler.stream.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    # Fallback for older Python or systems that don't support UTF-8
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "promote_next.log", encoding='utf-8'),
        console_handler
    ]
)
logger = logging.getLogger(__name__)

# Cache for user ID lookups
_user_id_cache = {}

def validate_environment():
    """Validate required environment variables."""
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    
    if not REPO_OWNER:
        logger.error("REPO_OWNER environment variable is required")
        sys.exit(1)
    
    if not REPO_NAME:
        logger.error("REPO_NAME environment variable is required")
        sys.exit(1)
    
    logger.info(f"Configuration: GitHub URL={GITHUB_URL}, Repository={REPO_OWNER}/{REPO_NAME}, Label={LABEL}")
    if ASSIGNEES:
        logger.info(f"Default assignees: {ASSIGNEES}")

def api_request(path: str, method: str = "GET", **kwargs) -> Any:
    """Make an API request to GitHub."""
    url = f"{GITHUB_URL}{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Issue-Queue-Bot/1.0"
    }
    
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))
    
    try:
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        
        if response.status_code == 204:  # No content
            return None
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {method} {url} - {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"API error details: {error_detail}")
            except:
                logger.error(f"API error response: {e.response.text}")
        raise

def get_last_bot_issue() -> Optional[Dict[str, Any]]:
    """Get the most recently created bot issue (open or closed)."""
    params = {
        "labels": LABEL,
        "state": "all",
        "sort": "created",
        "direction": "desc",
        "per_page": 1
    }
    
    issues = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues", params=params)
    return issues[0] if issues else None

def is_issue_done(issue: Dict[str, Any]) -> bool:
    """
    Check if an issue is truly done:
    1. Must be closed
    2. If closed by PR, that PR must be merged
    3. If manually closed (no PR), consider it done
    """
    if issue["state"] != "closed":
        logger.debug(f"Issue #{issue['number']} is still open")
        return False
    
    # GitHub doesn't have a direct "closed_by" endpoint like GitLab
    # We need to check the timeline events to see if it was closed by a PR
    timeline_events = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue['number']}/timeline")
    
    # Look for events that closed the issue
    closing_pr = None
    for event in timeline_events:
        if event.get("event") == "closed" and event.get("commit_id"):
            # This indicates the issue was closed by a commit (likely from a PR)
            # We need to find which PR contains this commit
            commit_sha = event["commit_id"]
            
            # Search for PRs that contain this commit
            prs = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls", params={
                "state": "all",
                "sort": "updated",
                "direction": "desc"
            })
            
            for pr in prs:
                if pr["merge_commit_sha"] == commit_sha:
                    closing_pr = pr
                    break
            break
    
    if not closing_pr:
        logger.info(f"Issue #{issue['number']} was manually closed (no PR) - considering done")
        return True
    
    # Check if the closing PR is merged
    is_merged = closing_pr["merged_at"] is not None
    logger.debug(f"Issue #{issue['number']} closed by PR #{closing_pr['number']} (merged: {is_merged})")
    
    return is_merged

def get_next_file(after_issue_number: Optional[int] = None) -> Optional[pathlib.Path]:
    """Get the next markdown file to process."""
    if not ISSUES_DIR.exists():
        logger.error(f"Issues directory {ISSUES_DIR} does not exist")
        return None
    
    # Get all markdown files and sort them
    md_files = sorted(ISSUES_DIR.glob("*.md"))
    
    if not md_files:
        logger.info("No markdown files found in issues directory")
        return None
    
    # If no previous issue, return the first file
    if after_issue_number is None:
        logger.info(f"No previous issues found, starting with {md_files[0].name}")
        return md_files[0]
    
    # Find the next file in sequence (next available number > after_issue_number)
    for file_path in md_files:
        # Extract number from filename (e.g., "001-title.md" -> 1)
        match = re.match(r"^(\d+)-", file_path.name)
        if match:
            file_number = int(match.group(1))
            if file_number > after_issue_number:
                logger.info(f"Found next file: {file_path.name}")
                return file_path
    
    logger.info(f"No file found after number {after_issue_number:03d}")
    return None

def get_user_ids(usernames: List[str]) -> List[str]:
    """Get GitHub usernames (GitHub uses usernames directly, not IDs for assignment)."""
    valid_usernames = []
    
    for username in usernames:
        if username in _user_id_cache:
            valid_usernames.append(username)
            continue
        
        try:
            user = api_request(f"/users/{username}")
            if user:
                _user_id_cache[username] = username
                valid_usernames.append(username)
                logger.debug(f"Found user {username}")
            else:
                logger.warning(f"User {username} not found")
        except Exception as e:
            logger.warning(f"Failed to lookup user {username}: {e}")
    
    return valid_usernames

def parse_labels_from_content(content: str) -> List[str]:
    """Parse labels from the markdown content."""
    labels = []
    lines = content.splitlines()
    
    # Look for a Labels section
    in_labels_section = False
    for line in lines:
        line = line.strip()
        
        # Check for Labels section header
        if re.match(r"^#+\s*labels?$", line, re.IGNORECASE):
            in_labels_section = True
            continue
        
        # Check if we've moved to a new section
        if in_labels_section and line.startswith("#"):
            break
        
        # If we're in the labels section, parse the labels
        if in_labels_section and line:
            # Split by commas and clean up
            label_parts = [l.strip() for l in line.split(",")]
            for label in label_parts:
                if label and not label.startswith("#"):  # Ignore empty and comment lines
                    labels.append(label)
            break  # Assume labels are on one line after the header
    
    return labels

def ensure_labels_exist(labels: List[str]) -> List[str]:
    """Ensure all labels exist in the repository, create them if they don't."""
    existing_labels = {}
    valid_labels = []
    
    try:
        # Get existing labels from the repository
        repo_labels = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/labels")
        for label in repo_labels:
            existing_labels[label["name"].lower()] = label["name"]
        
        logger.debug(f"Found {len(existing_labels)} existing labels in repository")
        
    except Exception as e:
        logger.warning(f"Could not fetch existing labels: {e}")
        # Continue anyway, we'll try to create labels as needed
    
    for label in labels:
        label_clean = label.strip()
        if not label_clean:
            continue
            
        # Check if label already exists (case-insensitive)
        if label_clean.lower() in existing_labels:
            valid_labels.append(existing_labels[label_clean.lower()])
            logger.debug(f"Label '{label_clean}' already exists")
        else:
            # Create the label
            try:
                # Generate a color for the label (simple hash-based color)
                import hashlib
                color_hash = hashlib.md5(label_clean.encode()).hexdigest()[:6]
                
                label_data = {
                    "name": label_clean,
                    "color": color_hash,
                    "description": f"Auto-generated label for {label_clean}"
                }
                
                created_label = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/labels", 
                                          method="POST", json=label_data)
                valid_labels.append(created_label["name"])
                logger.info(f"Created new label: '{label_clean}' with color #{color_hash}")
                
            except Exception as e:
                logger.warning(f"Could not create label '{label_clean}': {e}")
                # Add it anyway, GitHub might accept it
                valid_labels.append(label_clean)
    
    return valid_labels

def extract_issue_number_from_title(title: str) -> Optional[int]:
    """Extract issue number from a GitHub issue title that might contain prefixes."""
    # Look for patterns like "001-" or just "001" at the start
    match = re.match(r"^(\d+)[-\s]", title)
    if match:
        return int(match.group(1))
    
    # Fallback: look for any 3-digit number at the start
    match = re.match(r"^(\d{3})", title)
    if match:
        return int(match.group(1))
    
    return None

def create_issue(file_path: pathlib.Path) -> Dict[str, Any]:
    """Create a GitHub issue from a markdown file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        if not lines:
            raise ValueError("File is empty")
        
        # First line is the title
        title = lines[0].strip()
        
        # Rest is the description
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        
        # Parse labels from the content
        content_labels = parse_labels_from_content(content)
        logger.debug(f"Parsed labels from content: {content_labels}")
        
        # Ensure all labels exist in the repository
        valid_content_labels = ensure_labels_exist(content_labels) if content_labels else []
        
        # Combine bot tracking label with content labels
        all_labels = [LABEL] + valid_content_labels
        
        # Remove duplicates while preserving order
        unique_labels = []
        seen = set()
        for label in all_labels:
            if label.lower() not in seen:
                unique_labels.append(label)
                seen.add(label.lower())
        
        logger.info(f"Issue will be created with labels: {unique_labels}")
        
        # Prepare issue data
        issue_data = {
            "title": title,
            "body": description,  # GitHub uses 'body' instead of 'description'
            "labels": unique_labels
        }
        
        # Add assignees if configured
        if ASSIGNEES:
            valid_assignees = get_user_ids(ASSIGNEES)
            if valid_assignees:
                issue_data["assignees"] = valid_assignees
        
        logger.info(f"Creating issue: {title}")
        new_issue = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues", method="POST", json=issue_data)
        
        logger.info(f"Created issue #{new_issue['number']}: {new_issue['html_url']}")
        if content_labels:
            logger.info(f"Applied labels: {unique_labels}")
        
        return new_issue
    
    except Exception as e:
        logger.error(f"Failed to create issue from {file_path}: {e}")
        raise

def promote_next_issue() -> bool:
    """
    Main logic: check if we can promote the next issue.
    Returns True if an issue was created, False otherwise.
    """
    logger.info("Checking for next issue to promote...")
    
    # 1. Get the last bot issue
    last_issue = get_last_bot_issue()
    
    if last_issue:
        logger.info(f"Last bot issue: #{last_issue['number']} - {last_issue['title']}")
        
        # 2. Check if it's done
        if not is_issue_done(last_issue):
            logger.info("Previous issue still in progress - waiting")
            return False
        
        logger.info(f"Previous issue #{last_issue['number']} is complete")
        
        # Extract the issue number from the title to determine what's next
        issue_number = extract_issue_number_from_title(last_issue['title'])
        if issue_number is None:
            logger.warning(f"Could not extract number from issue title: {last_issue['title']}")
            logger.warning("Assuming this is the first processed issue")
            issue_number = 0
    else:
        logger.info("No previous bot issues found - starting from the beginning")
        issue_number = None
    
    # 3. Find the next file to process
    next_file = get_next_file(issue_number)
    
    if not next_file:
        logger.info("Queue is empty - no more issues to promote")
        return False
    
    # 4. Create the new issue
    try:
        create_issue(next_file)
        return True
    except Exception as e:
        logger.error(f"Failed to create issue: {e}")
        return False

def main():
    """Main entry point."""
    validate_environment()
    
    # Check if we're in continuous mode
    continuous = "--continuous" in sys.argv or "--daemon" in sys.argv
    
    if continuous:
        logger.info(f"🔄 Starting continuous mode (polling every {POLL_INTERVAL} seconds)")
        
        while True:
            try:
                promote_next_issue()
            except KeyboardInterrupt:
                logger.info("👋 Shutting down gracefully")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            
            logger.info(f"😴 Sleeping for {POLL_INTERVAL} seconds...")
            time.sleep(POLL_INTERVAL)
    else:
        # Single run mode
        logger.info("🚀 Running single promotion check")
        success = promote_next_issue()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
