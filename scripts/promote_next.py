#!/usr/bin/env python3
"""
GitLab Issue Queue Bot - Promotes one issue at a time
=====================================================

Promotes numbered Markdown files from issues/ directory to GitLab issues,
but only after the previous issue has been closed by a merged MR.

Environment Variables Required:
- GITLAB_TOKEN: Personal Access Token or CI Job Token with 'api' scope
- PROJECT_ID: Numeric GitLab project ID (e.g. 123456)

Optional Environment Variables:
- GITLAB_URL: GitLab instance URL (default: https://gitlab.com)
- LABEL: Label to mark bot-created issues (default: auto-generated)
- ASSIGNEES: Comma-separated GitLab usernames to assign (default: none)
- POLL_INTERVAL: Sleep interval in seconds for continuous mode (default: 900 = 15min)
"""

import os
import json
import pathlib
import re
import requests
import sys
import time
import logging
from typing import Optional, Dict, List, Any

# Configuration from environment
GITLAB_URL = os.environ.get("GITLAB_URL", "https://gitlab.com")
GITLAB_API = f"{GITLAB_URL}/api/v4"
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
PROJECT_ID = os.environ.get("PROJECT_ID")
LABEL = os.environ.get("LABEL", "auto-generated")
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
    if not GITLAB_TOKEN:
        logger.error("GITLAB_TOKEN environment variable is required")
        sys.exit(1)
    
    if not PROJECT_ID:
        logger.error("PROJECT_ID environment variable is required")
        sys.exit(1)
    
    if not PROJECT_ID.isdigit():
        logger.error("PROJECT_ID must be numeric")
        sys.exit(1)
    
    logger.info(f"Configuration: GitLab URL={GITLAB_URL}, Project ID={PROJECT_ID}, Label={LABEL}")
    if ASSIGNEES:
        logger.info(f"Default assignees: {ASSIGNEES}")

def api_request(path: str, method: str = "GET", **kwargs) -> Any:
    """Make an API request to GitLab."""
    url = f"{GITLAB_API}{path}"
    headers = {"Private-Token": GITLAB_TOKEN}
    
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
        "scope": "all",
        "order_by": "created_at",
        "sort": "desc",
        "per_page": 1
    }
    
    issues = api_request(f"/projects/{PROJECT_ID}/issues", params=params)
    return issues[0] if issues else None

def is_issue_done(issue: Dict[str, Any]) -> bool:
    """
    Check if an issue is truly done:
    1. Must be closed
    2. If closed by MR, that MR must be merged
    3. If manually closed (no MR), consider it done
    """
    if issue["state"] != "closed":
        logger.debug(f"Issue #{issue['iid']} is still open")
        return False
    
    # Check what closed this issue
    closed_by = api_request(f"/projects/{PROJECT_ID}/issues/{issue['iid']}/closed_by")
    
    if not closed_by:
        logger.info(f"Issue #{issue['iid']} was manually closed (no MR) - considering done")
        return True
    
    # Check if the closing MR is merged
    mr = closed_by[0]  # Take the first MR
    mr_details = api_request(f"/projects/{PROJECT_ID}/merge_requests/{mr['iid']}")
    
    is_merged = mr_details["state"] == "merged"
    logger.debug(f"Issue #{issue['iid']} closed by MR !{mr['iid']} (state: {mr_details['state']})")
    
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

def get_user_ids(usernames: List[str]) -> List[int]:
    """Get GitLab user IDs for the given usernames."""
    user_ids = []
    
    for username in usernames:
        if username in _user_id_cache:
            user_ids.append(_user_id_cache[username])
            continue
        
        try:
            users = api_request(f"/users", params={"username": username})
            if users:
                user_id = users[0]["id"]
                _user_id_cache[username] = user_id
                user_ids.append(user_id)
                logger.debug(f"Found user {username} with ID {user_id}")
            else:
                logger.warning(f"User {username} not found")
        except Exception as e:
            logger.warning(f"Failed to lookup user {username}: {e}")
    
    return user_ids

def extract_issue_number_from_title(title: str) -> Optional[int]:
    """Extract issue number from a GitLab issue title that might contain prefixes."""
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
    """Create a GitLab issue from a markdown file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        if not lines:
            raise ValueError("File is empty")
        
        # First line is the title
        title = lines[0].strip()
        
        # Rest is the description
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        
        # Prepare issue data
        issue_data = {
            "title": title,
            "description": description,
            "labels": [LABEL]
        }
        
        # Add assignees if configured
        if ASSIGNEES:
            assignee_ids = get_user_ids(ASSIGNEES)
            if assignee_ids:
                issue_data["assignee_ids"] = assignee_ids
        
        logger.info(f"Creating issue: {title}")
        new_issue = api_request(f"/projects/{PROJECT_ID}/issues", method="POST", json=issue_data)
        
        logger.info(f"Created issue #{new_issue['iid']}: {new_issue['web_url']}")
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
        logger.info(f"Last bot issue: #{last_issue['iid']} - {last_issue['title']}")
        
        # 2. Check if it's done
        if not is_issue_done(last_issue):
            logger.info("Previous issue still in progress - waiting")
            return False
        
        logger.info(f"Previous issue #{last_issue['iid']} is complete")
        
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
            return False    # 4. Create the new issue
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
