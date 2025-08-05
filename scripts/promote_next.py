#!/usr/bin/env python3
"""
Issue Queue Bot - Promotes one issue at a time
==============================================

Promotes numbered Markdown files from issues/ directory to repository issues,
but only after the previous issue has been closed by a merged PR.

Environment Variables Required:
- GITHUB_TOKEN: Personal Access Token with 'repo' scope
- REPO_OWNER: Repository owner (username or organization)
- REPO_NAME: Repository name

Optional Environment Variables:
- GITHUB_URL: API instance URL (default: https://api.github.com)
- LABEL: Bot tracking label to identify bot-created issues (default: auto-generated)
- COPILOT_ASSIGNEE: Username for Copilot (default: copilot)
- ASSIGNEES: Additional comma-separated usernames to assign (default: none)
- POLL_INTERVAL: Sleep interval in seconds for continuous mode (default: 900 = 15min)

Note: The bot will also read and apply labels from each issue's "## Labels" section,
creating any labels that don't exist in the repository.

Workflow:
1. Creates issue and assigns to Copilot
2. Monitors for associated pull request from Copilot
3. Waits for Copilot to request review
4. Auto-approves and merges the pull request
5. Only then creates the next issue in sequence
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
COPILOT_ASSIGNEE = os.environ.get("COPILOT_ASSIGNEE", "copilot").strip()  # Default to "copilot" if not set
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
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
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
    Check if an issue is completely done through the full Copilot workflow:
    1. Must be closed
    2. Must have been closed by a merged PR
    3. That PR must have been created by Copilot
    4. That PR must have been approved and merged
    """
    if issue["state"] != "closed":
        logger.debug(f"Issue #{issue['number']} is still open")
        return False
    
    # Get the closing PR for this issue
    closing_pr = get_closing_pr_for_issue(issue["number"])
    
    if not closing_pr:
        logger.info(f"Issue #{issue['number']} was manually closed (no PR) - considering done")
        return True
    
    # Check if the closing PR is merged and went through proper workflow
    is_merged = closing_pr["merged_at"] is not None
    logger.debug(f"Issue #{issue['number']} closed by PR #{closing_pr['number']} (merged: {is_merged})")
    
    return is_merged

def get_closing_pr_for_issue(issue_number: int) -> Optional[Dict[str, Any]]:
    """Find the PR that closed a specific issue."""
    try:
        # Get timeline events for the issue
        timeline_events = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}/timeline")
        
        # Look for events that closed the issue
        for event in timeline_events:
            if event.get("event") == "closed" and event.get("commit_id"):
                commit_sha = event["commit_id"]
                
                # Search for PRs that contain this commit
                prs = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls", params={
                    "state": "all",
                    "sort": "updated",
                    "direction": "desc"
                })
                
                for pr in prs:
                    if pr["merge_commit_sha"] == commit_sha:
                        return pr
        
        return None
    except Exception as e:
        logger.warning(f"Could not determine closing PR for issue #{issue_number}: {e}")
        return None

def check_copilot_workflow_status(issue: Dict[str, Any]) -> str:
    """
    Check the current status of the Copilot workflow for an issue.
    Returns: 'waiting_for_pr', 'pr_in_progress', 'pr_ready_for_review', 'pr_approved', 'completed'
    """
    issue_number = issue["number"]
    issue_title = issue["title"]
    
    # If issue is closed, it's completed
    if issue["state"] == "closed":
        return "completed"
    
    # Look for PRs that reference this issue (multiple detection methods)
    prs = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls", params={
        "state": "all",
        "sort": "updated",
        "direction": "desc",
        "per_page": 50  # Check more PRs
    })
    
    related_pr = None
    for pr in prs:
        # Method 1: Check if PR body or title mentions the issue number
        pr_text = f"{pr['title']} {pr['body'] or ''}".lower()
        if f"#{issue_number}" in pr_text or f"issue {issue_number}" in pr_text:
            related_pr = pr
            logger.debug(f"Found PR #{pr['number']} referencing issue #{issue_number} by number")
            break
        
        # Method 2: Check if PR title matches or contains the issue title
        pr_title_lower = pr['title'].lower()
        issue_title_lower = issue_title.lower()
        
        # Extract the core title (remove number prefix if present)
        core_issue_title = re.sub(r'^\d+[-\s]*', '', issue_title_lower).strip()
        
        if (core_issue_title in pr_title_lower or 
            pr_title_lower in issue_title_lower or
            # Check for similar titles (at least 70% match in words)
            len(set(core_issue_title.split()) & set(pr_title_lower.split())) >= len(core_issue_title.split()) * 0.7):
            related_pr = pr
            logger.debug(f"Found PR #{pr['number']} with matching title for issue #{issue_number}")
            break
    
    if not related_pr:
        logger.debug(f"No PR found for issue #{issue_number} - waiting for Copilot to create PR")
        return "waiting_for_pr"
    
    pr_number = related_pr["number"]
    logger.info(f"Found related PR #{pr_number} ('{related_pr['title']}') for issue #{issue_number}")
    
    # Check PR status
    if related_pr["state"] == "closed":
        if related_pr["merged"]:
            return "completed"
        else:
            logger.warning(f"PR #{pr_number} was closed without merging")
            return "completed"  # Consider it done even if not merged
    
    # PR is still open - check review status
    try:
        reviews = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/reviews")
        
        # Check if there are any reviews
        approved_reviews = [r for r in reviews if r["state"] == "APPROVED"]
        
        if approved_reviews:
            logger.info(f"PR #{pr_number} has been approved - ready to merge")
            return "pr_approved"
        
        # Check if PR is ready for review (has commits and is not draft)
        if related_pr["draft"]:
            logger.debug(f"PR #{pr_number} is still in draft - Copilot is still working")
            return "pr_in_progress"
        
        # Check if there are any review requests
        requested_reviewers = related_pr.get("requested_reviewers", [])
        if requested_reviewers:
            logger.info(f"PR #{pr_number} is ready for review")
            return "pr_ready_for_review"
        
        logger.debug(f"PR #{pr_number} exists but no review requested yet")
        return "pr_in_progress"
        
    except Exception as e:
        logger.warning(f"Could not check review status for PR #{pr_number}: {e}")
        return "pr_in_progress"

def auto_approve_and_merge_pr(issue: Dict[str, Any]) -> bool:
    """Auto-approve and merge the PR associated with an issue."""
    issue_number = issue["number"]
    
    # Find the related PR
    prs = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls", params={
        "state": "open",
        "sort": "updated",
        "direction": "desc"
    })
    
    related_pr = None
    for pr in prs:
        pr_text = f"{pr['title']} {pr['body'] or ''}".lower()
        if f"#{issue_number}" in pr_text or f"issue {issue_number}" in pr_text:
            related_pr = pr
            break
    
    if not related_pr:
        logger.error(f"No open PR found for issue #{issue_number}")
        return False
    
    pr_number = related_pr["number"]
    
    try:
        # 1. Approve the PR
        review_data = {
            "body": "Auto-approved by GitHub Issue Queue Bot - Copilot implementation completed.",
            "event": "APPROVE"
        }
        
        logger.info(f"Auto-approving PR #{pr_number}")
        api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/reviews", 
                   method="POST", json=review_data)
        
        # 2. Merge the PR using the updated API format
        merge_data = {
            "commit_title": f"Merge PR #{pr_number}: {related_pr['title']}",
            "commit_message": f"Resolves #{issue_number}\n\nAuto-merged by GitHub Issue Queue Bot after Copilot completion.",
            "merge_method": "squash"  # Use squash merge for cleaner history
        }
        
        logger.info(f"Auto-merging PR #{pr_number}")
        merge_result = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge", 
                                 method="PUT", json=merge_data)
        
        if merge_result:
            logger.info(f"Successfully merged PR #{pr_number}: {merge_result.get('message', 'Success')}")
        else:
            logger.info(f"Successfully merged PR #{pr_number}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to auto-approve/merge PR #{pr_number}: {e}")
        return False

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
    logger.debug(f"Validating usernames for assignment: {usernames}")
    
    for username in usernames:
        logger.debug(f"Checking username: '{username}'")
        
        if username in _user_id_cache:
            valid_usernames.append(username)
            logger.debug(f"Username '{username}' found in cache")
            continue
        
        try:
            logger.debug(f"Making API request to validate user '{username}'")
            user = api_request(f"/users/{username}")
            if user and user.get("login"):
                _user_id_cache[username] = username
                valid_usernames.append(username)
                logger.debug(f"Successfully validated user '{username}' (ID: {user.get('id', 'unknown')})")
            else:
                logger.warning(f"User '{username}' not found - API returned invalid response")
        except Exception as e:
            # For special accounts like Copilot, GitHub might not have a regular user profile
            # but they can still be assigned to issues
            logger.debug(f"API validation failed for '{username}': {e}")
            error_str = str(e).lower()
            if "404" in error_str and "copilot" in username.lower():
                logger.info(f"Adding '{username}' as assignee (GitHub Copilot may not have a public profile)")
                valid_usernames.append(username)
                _user_id_cache[username] = username
            else:
                logger.warning(f"Failed to lookup user '{username}': {e}")
    
    logger.debug(f"Final valid usernames: {valid_usernames}")
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
                # Handle specific error cases
                if "already_exists" in str(e).lower() or "validation failed" in str(e).lower():
                    logger.debug(f"Label '{label_clean}' already exists or creation failed")
                    # Try to find the existing label
                    for existing_name, existing_clean in existing_labels.items():
                        if existing_clean.lower() == label_clean.lower():
                            valid_labels.append(existing_clean)
                            break
                    else:
                        # Add it anyway, GitHub might accept it
                        valid_labels.append(label_clean)
                else:
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
        
        # Combine bot tracking label with content labels (removed "copilot" label as it was interfering with assignments)
        enhancement_labels = ["enhancement"]  # Labels that help categorize the issue
        all_labels = [LABEL] + valid_content_labels + enhancement_labels
        
        # Remove duplicates while preserving order
        unique_labels = []
        seen = set()
        for label in all_labels:
            if label.lower() not in seen:
                unique_labels.append(label)
                seen.add(label.lower())
        
        logger.info(f"Issue will be created with labels: {unique_labels}")
        
        # Add Copilot as primary assignee, plus any additional assignees
        all_assignees = []
        logger.debug(f"COPILOT_ASSIGNEE from environment: '{COPILOT_ASSIGNEE}'")
        logger.debug(f"Additional ASSIGNEES from environment: {ASSIGNEES}")
        
        if COPILOT_ASSIGNEE:
            all_assignees.append(COPILOT_ASSIGNEE)
            logger.debug(f"Added Copilot assignee: '{COPILOT_ASSIGNEE}'")
        else:
            logger.warning("COPILOT_ASSIGNEE is empty - no Copilot will be assigned")
            
        all_assignees.extend(ASSIGNEES)
        logger.debug(f"All assignees before deduplication: {all_assignees}")
        
        # Remove duplicates while preserving order
        unique_assignees = []
        seen = set()
        for assignee in all_assignees:
            if assignee and assignee.lower() not in seen:
                unique_assignees.append(assignee)
                seen.add(assignee.lower())
        
        logger.debug(f"Unique assignees after deduplication: {unique_assignees}")
        
        # Validate assignees
        valid_assignees = []
        if unique_assignees:
            logger.debug(f"Attempting to validate {len(unique_assignees)} assignees: {unique_assignees}")
            valid_assignees = get_user_ids(unique_assignees)
            logger.debug(f"Validation result: {len(valid_assignees)} valid assignees: {valid_assignees}")
        
        # Prepare issue data according to GitHub API v2022-11-28
        issue_data = {
            "title": title,
            "body": description,  # GitHub API uses 'body' not 'description'
            "labels": unique_labels
        }
        
        # Add assignees if we have valid ones
        if valid_assignees:
            issue_data["assignees"] = valid_assignees
            logger.info(f"Will assign issue to: {valid_assignees}")
        else:
            logger.debug("No assignees specified - issue will be created unassigned")
        
        logger.info(f"Creating issue: {title}")
        logger.debug(f"Issue creation payload: {json.dumps(issue_data, indent=2)}")
        
        # Try to create the issue with proper error handling
        try:
            logger.debug("Attempting to create issue with GitHub API...")
            new_issue = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues", method="POST", json=issue_data)
            logger.debug(f"Issue creation successful. Response ID: {new_issue.get('number', 'unknown')}")
        except Exception as e:
            logger.debug(f"Issue creation failed with error: {e}")
            error_str = str(e).lower()
            if ("assignee" in error_str or "assignees" in error_str) and ("invalid" in error_str or "not found" in error_str):
                logger.warning(f"Assignee validation failed during issue creation: {e}")
                logger.info("Retrying issue creation without assignees")
                # Remove assignees and try again
                issue_data_no_assignees = issue_data.copy()
                issue_data_no_assignees.pop("assignees", None)
                logger.debug(f"Retry payload (no assignees): {json.dumps(issue_data_no_assignees, indent=2)}")
                new_issue = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues", method="POST", json=issue_data_no_assignees)
                logger.info("✅ Issue created successfully without assignees (Copilot can self-assign when starting work)")
            else:
                logger.error(f"Issue creation failed with non-assignee error: {e}")
                raise
        
        logger.info(f"Created issue #{new_issue['number']}: {new_issue['html_url']}")
        
        # Debug: Check actual assignments
        actual_assignees = new_issue.get('assignees', [])
        if actual_assignees:
            assignee_logins = [a.get('login', 'unknown') for a in actual_assignees]
            logger.info(f"✅ Successfully assigned to: {assignee_logins}")
            logger.debug(f"Assignment details: {[{k: v for k, v in a.items() if k in ['login', 'id', 'type']} for a in actual_assignees]}")
        else:
            logger.warning("⚠️ Issue created without any assignees")
            if unique_assignees:
                logger.warning(f"Originally attempted to assign to: {unique_assignees}")
        
        if content_labels:
            applied_labels = new_issue.get('labels', [])
            applied_label_names = [l.get('name', 'unknown') for l in applied_labels]
            logger.info(f"Applied labels: {applied_label_names}")
            logger.debug(f"Label details: {[{k: v for k, v in l.items() if k in ['name', 'color', 'description']} for l in applied_labels]}")
        
        # Add a comment to trigger GitHub Copilot
        try:
            comment_body = (
                "@github-copilot please implement this feature\n\n"
                "🤖 **GitHub Copilot - Please implement this feature**\n\n"
                "This issue has been automatically created by the GitHub Issue Queue Bot. "
                "Please create a pull request to implement the requirements described above.\n\n"
                "**Next Steps:**\n"
                "1. Create a new branch for this feature\n"
                "2. Implement the requirements\n"
                "3. Create a pull request referencing this issue\n"
                "4. Request review when ready\n\n"
                f"Issue tracking label: `{LABEL}`\n\n"
                "/copilot implement"
            )
            
            api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues/{new_issue['number']}/comments",
                       method="POST", json={"body": comment_body})
            logger.info("✅ Added GitHub Copilot trigger comment to issue")
            
        except Exception as e:
            logger.warning(f"Could not add comment to issue: {e}")
        
        return new_issue
    
    except Exception as e:
        logger.error(f"Failed to create issue from {file_path}: {e}")
        raise

def promote_next_issue() -> bool:
    """
    Main logic: check if we can promote the next issue through the full Copilot workflow.
    Returns True if an issue was created or workflow advanced, False if waiting.
    """
    logger.info("Checking for next issue to promote...")
    
    # 1. Get the last bot issue
    last_issue = get_last_bot_issue()
    
    if last_issue:
        logger.info(f"Last bot issue: #{last_issue['number']} - {last_issue['title']}")
        
        # 2. Check the workflow status
        workflow_status = check_copilot_workflow_status(last_issue)
        logger.info(f"Current workflow status: {workflow_status}")
        
        if workflow_status == "waiting_for_pr":
            logger.info("Waiting for Copilot to create pull request...")
            return False
        
        elif workflow_status == "pr_in_progress":
            logger.info("Copilot is still working on the pull request...")
            return False
        
        elif workflow_status == "pr_ready_for_review":
            logger.info("Pull request is ready for review - auto-approving and merging...")
            success = auto_approve_and_merge_pr(last_issue)
            if success:
                logger.info("Pull request merged successfully - workflow advancing")
                return True
            else:
                logger.error("Failed to merge pull request - will retry")
                return False
        
        elif workflow_status == "pr_approved":
            logger.info("Pull request already approved - attempting to merge...")
            success = auto_approve_and_merge_pr(last_issue)
            if success:
                logger.info("Pull request merged successfully - workflow advancing")
                return True
            else:
                logger.error("Failed to merge pull request - will retry")
                return False
        
        elif workflow_status == "completed":
            logger.info(f"Previous issue #{last_issue['number']} workflow is complete")
            
            # Extract the issue number from the title to determine what's next
            issue_number = extract_issue_number_from_title(last_issue['title'])
            if issue_number is None:
                logger.warning(f"Could not extract number from issue title: {last_issue['title']}")
                logger.warning("Assuming this is the first processed issue")
                issue_number = 0
        else:
            logger.warning(f"Unknown workflow status: {workflow_status}")
            return False
    else:
        logger.info("No previous bot issues found - starting from the beginning")
        issue_number = None
    
    # 3. Find the next file to process (only if previous workflow is complete)
    if last_issue and workflow_status != "completed":
        return False
    
    next_file = get_next_file(issue_number)
    
    if not next_file:
        logger.info("Queue is empty - no more issues to promote")
        return False
    
    # 4. Create the new issue
    try:
        new_issue = create_issue(next_file)
        logger.info(f"✅ New issue created and assigned to {COPILOT_ASSIGNEE}")
        logger.info(f"🤖 Waiting for Copilot to begin work on issue #{new_issue['number']}")
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
        logger.info(f"🔄 Starting continuous Copilot workflow mode (polling every {POLL_INTERVAL} seconds)")
        logger.info(f"🤖 Copilot assignee: {COPILOT_ASSIGNEE}")
        
        while True:
            try:
                activity = promote_next_issue()
                if activity:
                    logger.info("📈 Workflow activity detected - continuing monitoring")
                else:
                    logger.info("⏳ No workflow activity - waiting for Copilot")
            except KeyboardInterrupt:
                logger.info("👋 Shutting down gracefully")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            
            logger.info(f"😴 Sleeping for {POLL_INTERVAL} seconds...")
            time.sleep(POLL_INTERVAL)
    else:
        # Single run mode
        logger.info("🚀 Running single Copilot workflow check")
        logger.info(f"🤖 Copilot assignee: {COPILOT_ASSIGNEE}")
        success = promote_next_issue()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
