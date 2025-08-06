#!/usr/bin/env python3
"""
Issue Queue Bot - Promotes one issue at a time
==============================================

Promotes numbered Markdown files from issues/ directory to repository issues,
but only after the previous issue has been closed by a merged PR.

NEW: Enhanced mismatch handling between local file numbers and GitHub issue numbers.
The bot now maintains its own state file to track which files have been processed,
regardless of the GitHub issue numbers they receive. This handles cases where 
repositories already have existing issues/PRs.

ENHANCED: Smart resume capability for bot restarts.
The bot automatically resumes from where it left off by:
1. Syncing local state with GitHub repository on startup
2. Identifying active bot issues and their current workflow state  
3. Determining the appropriate next action (monitor, review, merge, or create new)
4. Continuing seamlessly without manual intervention

Environment Variables Required:
- GITHUB_TOKEN: Personal Access Token with 'repo' scope
- REPO_OWNER: Repository owner (username or organization)
- REPO_NAME: Repository name

Optional Environment Variables:
- GITHUB_URL: API instance URL (default: https://api.github.com)
- LABEL: Bot tracking label to identify bot-created issues (default: auto-generated)
- ASSIGNEES: Additional comma-separated usernames to assign (default: none)
- POLL_INTERVAL: Sleep interval in seconds for continuous mode (default: 900 = 15min)

Note: The bot will also read and apply labels from each issue's "## Labels" section,
creating any labels that don't exist in the repository.

Workflow:
1. Creates issue and assigns to copilot
2. Monitors for associated pull request from Copilot using multiple strategies:
   - Direct issue number references (#123)
   - Time-based correlation (PRs created after issue)
   - [WIP] markers in PR titles
   - File number references in PR content
3. Waits for Copilot to request review
4. Auto-approves and merges the pull request
5. Only then creates the next issue in sequence

Command Line Options:
- --continuous or --daemon: Run in continuous monitoring mode
- --status: Show current processing status and sync state with GitHub
- --resume or --sync: Force a complete state sync with GitHub and show resume plan
- --help: Show this help message

State Management:
The bot maintains a state file (logs/processed_files.json) to track:
- Which files have been processed
- Current processing status
- GitHub issue numbers for correlation
- Completion timestamps
- Resume context for bot restarts

Resume Support:
On startup, the bot automatically:
1. Syncs local state with GitHub repository
2. Identifies any active bot issues and their current workflow state
3. Determines the appropriate next action (monitor, review, merge, or create new)
4. Continues seamlessly from where it left off

Resume Workflow (on bot restart):
1. Sync local state with GitHub repository
2. Identify any open bot issues and their workflow state
3. If active issue found:
   - waiting_for_copilot: Monitor for Copilot to start
   - copilot_working: Monitor for PR creation  
   - pr_ready_for_review: Auto-approve and merge
   - completed: Mark as done and create next issue
4. If no active issues: Create next unprocessed issue
5. Continue normal workflow monitoring

This ensures reliable operation even when GitHub issue numbers don't match
local file numbering due to existing repository history.
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
STATE_FILE = LOG_DIR / "processed_files.json"

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

def get_copilot_agent_info() -> Optional[Dict[str, Any]]:
    """Get Copilot coding agent information from the repository."""
    query = """
    query GetCopilotAgent($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
          nodes {
            login
            __typename
            ... on Bot {
              id
            }
            ... on User {
              id
            }
          }
        }
      }
    }
    """
    
    variables = {
        "owner": REPO_OWNER,
        "name": REPO_NAME
    }
    
    try:
        data = graphql_request(query, variables)
        repository = data.get("repository")
        
        if not repository:
            logger.error(f"Repository {REPO_OWNER}/{REPO_NAME} not found")
            return None
        
        repo_id = repository["id"]
        suggested_actors = repository.get("suggestedActors", {}).get("nodes", [])
        
        # Look for Copilot coding agent
        copilot_agent = None
        for actor in suggested_actors:
            if actor.get("login") == "copilot-swe-agent":
                copilot_agent = actor
                break
        
        if not copilot_agent:
            logger.warning("Copilot coding agent not found in suggested actors")
            logger.debug(f"Available actors: {[(a.get('login'), a.get('__typename')) for a in suggested_actors]}")
            return None
        
        return {
            "repository_id": repo_id,
            "copilot_id": copilot_agent["id"],
            "copilot_login": copilot_agent["login"]
        }
    
    except Exception as e:
        logger.error(f"Failed to get Copilot agent info: {e}")
        return None

def validate_environment():
    """Validate required environment variables and Copilot availability."""
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
    
    # Check Copilot availability
    copilot_info = get_copilot_agent_info()
    if not copilot_info:
        logger.error("Copilot coding agent is not available in this repository")
        logger.error("Please ensure Copilot is enabled for your account and repository")
        sys.exit(1)
    
    logger.info(f"✅ Copilot coding agent available: {copilot_info['copilot_login']}")
    return copilot_info

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

def graphql_request(query: str, variables: Optional[Dict[str, Any]] = None) -> Any:
    """Make a GraphQL request to GitHub."""
    url = f"{GITHUB_URL}/graphql" if GITHUB_URL == "https://api.github.com" else f"{GITHUB_URL}/api/graphql"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "GitHub-Issue-Queue-Bot/1.0"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if "errors" in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        return result.get("data")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"GraphQL request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"GraphQL error details: {error_detail}")
            except:
                logger.error(f"GraphQL error response: {e.response.text}")
        raise

def load_processed_files_state() -> Dict[str, Any]:
    """Load the state of processed files from disk."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"processed_files": [], "last_completed_file": None}
    except Exception as e:
        logger.warning(f"Could not load processed files state: {e}")
        return {"processed_files": [], "last_completed_file": None}

def save_processed_files_state(state: Dict[str, Any]):
    """Save the state of processed files to disk."""
    try:
        STATE_FILE.parent.mkdir(exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        logger.debug(f"Saved processed files state: {len(state.get('processed_files', []))} files tracked")
    except Exception as e:
        logger.warning(f"Could not save processed files state: {e}")

def mark_file_as_processing(filename: str, issue_number: int) -> Dict[str, Any]:
    """Mark a file as currently being processed."""
    state = load_processed_files_state()
    
    # Add or update the file entry
    processed_files = state.get("processed_files", [])
    
    # Remove any existing entry for this file
    processed_files = [f for f in processed_files if f.get("filename") != filename]
    
    # Add new entry
    file_entry = {
        "filename": filename,
        "issue_number": issue_number,
        "status": "processing",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    processed_files.append(file_entry)
    
    state["processed_files"] = processed_files
    save_processed_files_state(state)
    
    return file_entry

def mark_file_as_completed(filename: str):
    """Mark a file as completed."""
    state = load_processed_files_state()
    processed_files = state.get("processed_files", [])
    
    # Find and update the file entry
    for file_entry in processed_files:
        if file_entry.get("filename") == filename:
            file_entry["status"] = "completed"
            file_entry["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            break
    
    state["last_completed_file"] = filename
    save_processed_files_state(state)

def sync_processed_files_with_github() -> Dict[str, Any]:
    """
    Sync our local state with what's actually on GitHub.
    This helps recover if files were processed outside of this system.
    Enhanced with better error handling and progress feedback.
    """
    logger.info("🔄 Syncing processed files state with GitHub...")
    
    try:
        # Get all bot issues from GitHub
        params = {
            "labels": LABEL,
            "state": "all",
            "sort": "created",
            "direction": "asc",  # Oldest first
            "per_page": 100
        }
        
        issues = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues", params=params)
        logger.info(f"📊 Found {len(issues)} bot issues in GitHub repository")
        
        # Load current state
        state = load_processed_files_state()
        processed_files = state.get("processed_files", [])
        
        # Create a map of existing entries
        existing_files = {f.get("filename"): f for f in processed_files}
        
        updated_count = 0
        added_count = 0
        
        # Check each GitHub issue
        for i, issue in enumerate(issues):
            if i % 10 == 0 and i > 0:
                logger.debug(f"Processing issue {i+1}/{len(issues)}...")
                
            file_number = extract_issue_number_from_title(issue["title"])
            if file_number is None:
                logger.debug(f"Could not extract file number from issue title: {issue['title']}")
                continue
            
            # Find corresponding file
            pattern = f"{file_number:03d}-*.md"
            matching_files = list(ISSUES_DIR.glob(pattern)) if ISSUES_DIR.exists() else []
            if not matching_files:
                logger.debug(f"No local file found for issue #{issue['number']} (pattern: {pattern})")
                continue
            
            filename = matching_files[0].name
            
            # Determine if this issue is completed
            is_completed = is_issue_done(issue)
            status = "completed" if is_completed else "processing"
            
            # Update or create entry
            if filename in existing_files:
                # Update existing entry
                entry = existing_files[filename]
                old_status = entry.get("status")
                if old_status != status or entry.get("issue_number") != issue["number"]:
                    logger.info(f"📝 Updating {filename}: status={old_status}->{status}, issue=#{entry.get('issue_number', 'none')}->{issue['number']}")
                    entry["status"] = status
                    entry["issue_number"] = issue["number"]
                    if status == "completed" and "completed_at" not in entry:
                        entry["completed_at"] = issue.get("closed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                    updated_count += 1
            else:
                # Create new entry
                logger.info(f"➕ Adding missing file to state: {filename} (issue #{issue['number']}, status: {status})")
                new_entry = {
                    "filename": filename,
                    "issue_number": issue["number"],
                    "status": status,
                    "created_at": issue["created_at"]
                }
                if status == "completed":
                    new_entry["completed_at"] = issue.get("closed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                
                processed_files.append(new_entry)
                existing_files[filename] = new_entry
                added_count += 1
        
        # Update state and save
        state["processed_files"] = processed_files
        
        # Update last completed file
        completed_files = [f for f in processed_files if f.get("status") == "completed"]
        if completed_files:
            # Sort by file number to find the actual last completed file
            completed_files.sort(key=lambda f: extract_issue_number_from_title(f.get("filename", "")) or 0)
            state["last_completed_file"] = completed_files[-1]["filename"]
        
        save_processed_files_state(state)
        
        completed_count = len([f for f in processed_files if f.get("status") == "completed"])
        processing_count = len([f for f in processed_files if f.get("status") == "processing"])
        
        sync_summary = f"✅ State sync complete: {completed_count} completed, {processing_count} processing"
        if updated_count > 0 or added_count > 0:
            sync_summary += f" (updated: {updated_count}, added: {added_count})"
        logger.info(sync_summary)
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to sync state with GitHub: {e}")
        return load_processed_files_state()

def get_next_unprocessed_file() -> Optional[pathlib.Path]:
    """Get the next file that hasn't been processed yet."""
    if not ISSUES_DIR.exists():
        logger.error(f"Issues directory {ISSUES_DIR} does not exist")
        return None
    
    # Get all markdown files and sort them
    md_files = sorted(ISSUES_DIR.glob("*.md"))
    
    if not md_files:
        logger.info("No markdown files found in issues directory")
        return None
    
    # Sync state with GitHub first to ensure accuracy
    state = sync_processed_files_with_github()
    processed_files = state.get("processed_files", [])
    
    # Get list of processed filenames
    processed_filenames = set()
    currently_processing = None
    
    for file_entry in processed_files:
        filename = file_entry.get("filename")
        status = file_entry.get("status")
        
        if status == "completed":
            processed_filenames.add(filename)
        elif status == "processing":
            currently_processing = filename
    
    # If there's a file currently being processed, return None (wait for it to complete)
    if currently_processing:
        logger.info(f"File {currently_processing} is currently being processed")
        return None
    
    # Find the first unprocessed file
    for file_path in md_files:
        filename = file_path.name
        if filename not in processed_filenames:
            logger.info(f"Found next unprocessed file: {filename}")
            return file_path
    
    logger.info("All files have been processed")
    return None

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

def find_related_prs_for_issue(issue: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Find pull requests related to an issue using multiple strategies.
    This handles cases where GitHub issue numbers don't match local file numbers.
    """
    issue_number = issue["number"]
    issue_created_at = issue["created_at"]
    linked_prs = []
    
    try:
        # Get PRs created after the issue (with some buffer time)
        from datetime import datetime, timedelta

        # Parse ISO datetime string manually to avoid dependency
        def parse_iso_datetime(iso_string):
            # Simple ISO datetime parser for GitHub API format
            # Format: 2023-12-25T10:30:00Z
            try:
                iso_string = iso_string.replace('Z', '+00:00')
                return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            except:
                # Fallback parsing
                import re
                match = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})', iso_string)
                if match:
                    year, month, day, hour, minute, second = map(int, match.groups())
                    return datetime(year, month, day, hour, minute, second)
                return datetime.now()  # Fallback
        
        issue_created = parse_iso_datetime(issue_created_at)
        # Look for PRs created within a reasonable timeframe after issue creation
        
        prs = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls", params={
            "state": "all",
            "sort": "created",
            "direction": "desc",
            "per_page": 50  # Increased to catch more potential matches
        })
        
        for pr in prs:
            pr_created_at = pr["created_at"]
            pr_created = parse_iso_datetime(pr_created_at)
            
            # Skip PRs created before the issue (with 5 minute buffer)
            if pr_created < issue_created - timedelta(minutes=5):
                continue
            
            pr_body = pr.get("body", "") or ""
            pr_title = pr.get("title", "")
            pr_author = pr.get("user", {}).get("login", "")
            
            # Strategy 1: Direct issue number reference
            direct_reference = (
                f"#{issue_number}" in pr_body or f"#{issue_number}" in pr_title or
                f"issue {issue_number}" in pr_body.lower() or 
                f"fixes #{issue_number}" in pr_body.lower() or
                f"closes #{issue_number}" in pr_body.lower()
            )
            
            # Strategy 2: Check for [WIP] marker and Copilot authorship
            wip_marker = "[WIP]" in pr_title.upper() or "[WIP]" in pr_body.upper()
            
            # Strategy 3: Time-based correlation for Copilot PRs
            # If PR is from Copilot and created shortly after issue, it's likely related
            time_diff = pr_created - issue_created
            recent_copilot_pr = (
                pr_author == "copilot-swe-agent" and 
                time_diff <= timedelta(hours=24)  # Within 24 hours
            )
            
            # Strategy 4: Extract file number from issue title and look for it in PR
            file_number = extract_issue_number_from_title(issue["title"])
            file_reference = False
            if file_number is not None:
                file_ref_patterns = [
                    f"{file_number:03d}",  # 001, 002, etc.
                    f"#{file_number}",     # #1, #2, etc.
                    f"issue {file_number}",  # issue 1, issue 2, etc.
                ]
                file_reference = any(pattern in pr_title.lower() or pattern in pr_body.lower() 
                                   for pattern in file_ref_patterns)
            
            # Check if this PR matches any of our strategies
            if pr_author == "copilot-swe-agent" and (
                direct_reference or 
                (wip_marker and recent_copilot_pr) or
                (recent_copilot_pr and file_reference)
            ):
                linked_prs.append(pr)
                logger.debug(f"Found related Copilot PR #{pr['number']} for issue #{issue_number}")
                logger.debug(f"  - Direct reference: {direct_reference}")
                logger.debug(f"  - WIP marker: {wip_marker}")
                logger.debug(f"  - Recent Copilot PR: {recent_copilot_pr}")
                logger.debug(f"  - File reference: {file_reference}")
        
        # Sort by creation time, most recent first
        linked_prs.sort(key=lambda x: x["created_at"], reverse=True)
        
    except Exception as e:
        logger.warning(f"Could not search for related PRs: {e}")
    
    return linked_prs

def wait_for_pr_readiness(pr_number: int, max_wait_minutes: int = 10, check_interval_seconds: int = 30) -> bool:
    """
    Wait for a PR to become ready to merge, checking periodically.
    Useful for waiting for status checks to complete.
    """
    import time
    max_attempts = (max_wait_minutes * 60) // check_interval_seconds
    attempt = 0
    
    logger.info(f"⏳ Waiting up to {max_wait_minutes} minutes for PR #{pr_number} to become ready...")
    
    while attempt < max_attempts:
        try:
            pr_details = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}")
            is_ready, reason = is_pr_ready_to_merge(pr_details)
            
            if is_ready:
                logger.info(f"✅ PR #{pr_number} is now ready: {reason}")
                return True
            
            # Log the current blocking reason
            logger.debug(f"PR #{pr_number} not ready yet (attempt {attempt + 1}/{max_attempts}): {reason}")
            
            # Check if it's worth waiting (not permanently blocked)
            if "conflicts" in reason.lower() or "closed" in reason.lower():
                logger.warning(f"PR #{pr_number} appears permanently blocked: {reason}")
                return False
            
            time.sleep(check_interval_seconds)
            attempt += 1
            
        except Exception as e:
            logger.warning(f"Error checking PR #{pr_number} readiness: {e}")
            time.sleep(check_interval_seconds)
            attempt += 1
    
    logger.warning(f"⏰ Timeout waiting for PR #{pr_number} to become ready after {max_wait_minutes} minutes")
    return False

def retry_operation(func, *args, max_retries: int = 3, delay: int = 5, **kwargs):
    """
    Retry an operation with exponential backoff.
    Useful for handling transient API errors.
    """
    import time
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = delay * (2 ** attempt)
            logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries}): {e}")
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

def get_comprehensive_pr_status(pr_number: int) -> Dict[str, Any]:
    """Get comprehensive status information about a pull request."""
    try:
        # Get basic PR details
        pr_details = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}")
        
        # Get reviews
        reviews = get_pr_reviews(pr_number)
        
        # Get status checks
        status_info = get_pr_status_checks(pr_number)
        
        # Process reviews to get latest state from each reviewer
        review_summary = {}
        latest_reviews = {}
        
        for review in reviews:
            reviewer_login = review["user"]["login"]
            review_state = review["state"]
            submitted_at = review["submitted_at"]
            
            if reviewer_login not in latest_reviews or submitted_at > latest_reviews[reviewer_login]["submitted_at"]:
                latest_reviews[reviewer_login] = review
                review_summary[reviewer_login] = {
                    "state": review_state,
                    "submitted_at": submitted_at,
                    "body": review.get("body", "")[:200] + "..." if len(review.get("body", "")) > 200 else review.get("body", "")
                }
        
        # Count review states
        approved_count = sum(1 for r in review_summary.values() if r["state"] == "APPROVED")
        changes_requested_count = sum(1 for r in review_summary.values() if r["state"] == "CHANGES_REQUESTED")
        pending_count = sum(1 for r in review_summary.values() if r["state"] == "PENDING")
        
        # Check merge readiness
        is_ready, ready_reason = is_pr_ready_to_merge(pr_details)
        
        # Summarize status checks
        status_summary = "unknown"
        check_details = []
        
        if status_info["status"]:
            status_summary = status_info["status"].get("state", "unknown")
            statuses = status_info["status"].get("statuses", [])
            for status in statuses:
                check_details.append({
                    "context": status.get("context", "unknown"),
                    "state": status.get("state", "unknown"),
                    "description": status.get("description", "")
                })
        
        if status_info["check_runs"]:
            check_runs = status_info["check_runs"].get("check_runs", [])
            for check_run in check_runs:
                check_details.append({
                    "context": check_run.get("name", "unknown"),
                    "state": check_run.get("conclusion") or check_run.get("status", "unknown"),
                    "description": check_run.get("output", {}).get("summary", "")[:100]
                })
        
        return {
            "pr_number": pr_number,
            "title": pr_details.get("title", ""),
            "state": pr_details.get("state", ""),
            "draft": pr_details.get("draft", False),
            "mergeable": pr_details.get("mergeable"),
            "mergeable_state": pr_details.get("mergeable_state"),
            "author": pr_details.get("user", {}).get("login", "unknown"),
            "created_at": pr_details.get("created_at", ""),
            "updated_at": pr_details.get("updated_at", ""),
            "review_summary": {
                "approved": approved_count,
                "changes_requested": changes_requested_count,
                "pending": pending_count,
                "reviewers": review_summary
            },
            "status_checks": {
                "overall_state": status_summary,
                "checks": check_details
            },
            "requested_reviewers": [r.get("login", "") for r in pr_details.get("requested_reviewers", [])],
            "requested_teams": [t.get("name", "") for t in pr_details.get("requested_teams", [])],
            "is_ready_to_merge": is_ready,
            "ready_reason": ready_reason,
            "html_url": pr_details.get("html_url", "")
        }
    
    except Exception as e:
        logger.error(f"Could not get comprehensive PR status for #{pr_number}: {e}")
        return {"pr_number": pr_number, "error": str(e)}

def log_pr_monitoring_details(issue: Dict[str, Any]):
    """Log detailed monitoring information for an issue's related PRs."""
    issue_number = issue["number"]
    logger.info(f"📊 Detailed monitoring for issue #{issue_number}")
    
    # Find related PRs
    related_prs = find_related_prs_for_issue(issue)
    
    if not related_prs:
        logger.info(f"   No related PRs found for issue #{issue_number}")
        return
    
    for i, pr in enumerate(related_prs):
        pr_number = pr["number"]
        logger.info(f"   PR #{pr_number} ({pr['state']}) - {pr.get('title', 'No title')[:80]}")
        
        if pr["state"] == "open":
            # Get comprehensive status for open PRs
            status = get_comprehensive_pr_status(pr_number)
            
            if "error" in status:
                logger.error(f"     ❌ Error getting status: {status['error']}")
                continue
            
            logger.info(f"     📋 Draft: {status['draft']}, Mergeable: {status['mergeable']}")
            logger.info(f"     🔍 Reviews: ✅{status['review_summary']['approved']} "
                       f"❌{status['review_summary']['changes_requested']} "
                       f"⏳{status['review_summary']['pending']}")
            
            if status['requested_reviewers']:
                logger.info(f"     👥 Pending reviewers: {', '.join(status['requested_reviewers'])}")
            
            logger.info(f"     🚦 Status: {status['status_checks']['overall_state']}")
            
            for check in status['status_checks']['checks'][:3]:  # Show first 3 checks
                logger.info(f"       - {check['context']}: {check['state']}")
            
            if len(status['status_checks']['checks']) > 3:
                logger.info(f"       ... and {len(status['status_checks']['checks']) - 3} more checks")
            
            logger.info(f"     🎯 Ready to merge: {status['is_ready_to_merge']} - {status['ready_reason']}")
        
        elif pr["state"] == "closed":
            merged = pr.get("merged", False)
            logger.info(f"     ✅ Closed - {'Merged' if merged else 'Not merged'}")

def get_pr_reviews(pr_number: int) -> List[Dict[str, Any]]:
    """Get all reviews for a pull request."""
    try:
        reviews = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/reviews")
        return reviews or []
    except Exception as e:
        logger.warning(f"Could not get reviews for PR #{pr_number}: {e}")
        return []

def get_pr_status_checks(pr_number: int) -> Dict[str, Any]:
    """Get status checks for a pull request."""
    try:
        # Get the PR details to get the head SHA
        pr_details = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}")
        head_sha = pr_details["head"]["sha"]
        
        # Get status checks for the head commit
        status_checks = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/commits/{head_sha}/status")
        
        # Also get check runs (newer format)
        check_runs = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/commits/{head_sha}/check-runs")
        
        return {
            "status": status_checks,
            "check_runs": check_runs,
            "head_sha": head_sha
        }
    except Exception as e:
        logger.warning(f"Could not get status checks for PR #{pr_number}: {e}")
        return {"status": None, "check_runs": None, "head_sha": None}

def is_pr_ready_to_merge(pr_details: Dict[str, Any]) -> tuple[bool, str]:
    """
    Check if a PR is ready to be merged based on comprehensive criteria.
    Returns (is_ready, reason).
    """
    pr_number = pr_details["number"]
    
    # Check if PR is mergeable
    if pr_details.get("mergeable_state") == "blocked":
        return False, "PR is blocked (mergeable_state: blocked)"
    
    if not pr_details.get("mergeable", True):
        return False, "PR is not mergeable (conflicts or other issues)"
    
    # Check if PR is in draft
    if pr_details.get("draft", False):
        return False, "PR is still in draft mode"
    
    # Check for WIP indicators
    pr_title = pr_details.get("title", "").lower()
    if "[wip]" in pr_title or "wip:" in pr_title or "work in progress" in pr_title:
        return False, "PR has WIP (Work in Progress) indicators"
    
    # Get reviews
    reviews = get_pr_reviews(pr_number)
    
    # Check review status
    review_states = {}
    latest_reviews = {}
    
    # Process reviews to get latest state from each reviewer
    for review in reviews:
        reviewer_login = review["user"]["login"]
        review_state = review["state"]
        submitted_at = review["submitted_at"]
        
        if reviewer_login not in latest_reviews or submitted_at > latest_reviews[reviewer_login]["submitted_at"]:
            latest_reviews[reviewer_login] = review
            review_states[reviewer_login] = review_state
    
    # Count review states
    approved_count = sum(1 for state in review_states.values() if state == "APPROVED")
    changes_requested_count = sum(1 for state in review_states.values() if state == "CHANGES_REQUESTED")
    
    if changes_requested_count > 0:
        return False, f"PR has {changes_requested_count} reviews requesting changes"
    
    # Check if review is required (look for requested reviewers)
    requested_reviewers = pr_details.get("requested_reviewers", [])
    requested_teams = pr_details.get("requested_teams", [])
    
    has_pending_reviews = len(requested_reviewers) > 0 or len(requested_teams) > 0
    
    # For bot PRs, we'll be more lenient with review requirements
    pr_author = pr_details.get("user", {}).get("login", "")
    is_bot_pr = pr_author == "copilot-swe-agent"
    
    if is_bot_pr:
        # For bot PRs, we need at least some indication it's ready
        if approved_count == 0 and has_pending_reviews:
            return False, f"Copilot PR has pending review requests ({len(requested_reviewers)} reviewers, {len(requested_teams)} teams)"
        
        # Check status checks
        status_info = get_pr_status_checks(pr_number)
        if status_info["status"]:
            overall_state = status_info["status"].get("state", "pending")
            if overall_state in ["failure", "error"]:
                return False, f"PR has failing status checks (state: {overall_state})"
            elif overall_state == "pending":
                return False, "PR has pending status checks"
        
        # Check check runs (GitHub Actions, etc.)
        if status_info["check_runs"]:
            check_runs = status_info["check_runs"].get("check_runs", [])
            for check_run in check_runs:
                status = check_run.get("status")
                conclusion = check_run.get("conclusion")
                
                if status == "in_progress":
                    return False, f"PR has in-progress check: {check_run.get('name', 'unknown')}"
                elif conclusion in ["failure", "cancelled", "timed_out"]:
                    return False, f"PR has failed check: {check_run.get('name', 'unknown')} ({conclusion})"
        
        return True, "Copilot PR is ready to merge"
    
    # For non-bot PRs, stricter requirements
    if approved_count == 0:
        return False, "PR needs at least one approval"
    
    return True, f"PR is ready to merge ({approved_count} approvals)"

def check_copilot_workflow_status(issue: Dict[str, Any]) -> str:
    """
    Enhanced check of the current status of the Copilot workflow for an issue.
    Returns: 'waiting_for_copilot', 'copilot_working', 'pr_ready_for_review', 'completed'
    """
    issue_number = issue["number"]
    
    # If issue is closed, it's completed
    if issue["state"] == "closed":
        return "completed"
    
    # Check if Copilot is assigned to the issue
    assignees = issue.get("assignees", [])
    copilot_assigned = any(a.get("login") == "copilot-swe-agent" for a in assignees)
    
    if not copilot_assigned:
        logger.debug(f"Copilot not assigned to issue #{issue_number}")
        return "waiting_for_copilot"
    
    # Look for timeline events to understand Copilot's status
    try:
        timeline_events = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}/timeline")
        
        # Look for Copilot-related events
        copilot_started = False
        copilot_finished = False
        eyes_reaction = False
        
        for event in timeline_events:
            event_type = event.get("event")
            actor = event.get("actor", {})
            actor_login = actor.get("login", "")
            
            # Check for eyes reaction from Copilot (indicates acknowledgment)
            if event_type == "subscribed" and actor_login == "copilot-swe-agent":
                eyes_reaction = True
                logger.debug(f"Found Copilot acknowledgment for issue #{issue_number}")
            
            # Check for "Copilot started work" type events
            # These appear as comments or other timeline events
            if event_type in ["commented", "cross-referenced"] and actor_login == "copilot-swe-agent":
                body = event.get("body", "").lower()
                if "started work" in body or "working on" in body:
                    copilot_started = True
                    logger.debug(f"Found Copilot work start event for issue #{issue_number}")
                
                if "finished work" in body or "completed" in body:
                    copilot_finished = True
                    logger.debug(f"Found Copilot work completion event for issue #{issue_number}")
        
        # Use improved PR finding strategy
        linked_prs = find_related_prs_for_issue(issue)
        
        # Determine status based on what we found
        if linked_prs:
            # Check the status of the most recent linked PR
            latest_pr = linked_prs[0]  # Already sorted by creation time
            pr_state = latest_pr["state"]
            pr_number = latest_pr["number"]
            
            logger.debug(f"Found linked PR #{pr_number} in state: {pr_state}")
            
            if pr_state == "closed":
                if latest_pr.get("merged"):
                    return "completed"
                else:
                    logger.warning(f"Copilot PR #{latest_pr['number']} was closed without merging")
                    return "completed"  # Consider it done
            
            elif pr_state == "open":
                # Get detailed PR information
                try:
                    pr_details = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}")
                    
                    # Use comprehensive readiness check
                    is_ready, reason = is_pr_ready_to_merge(pr_details)
                    
                    if is_ready:
                        logger.info(f"✅ Copilot PR #{pr_number} is ready for merge: {reason}")
                        return "pr_ready_for_review"
                    else:
                        logger.debug(f"🔄 Copilot PR #{pr_number} is not ready: {reason}")
                        return "copilot_working"
                        
                except Exception as e:
                    logger.warning(f"Could not check detailed PR status: {e}")
                    # Fallback to basic checks
                    if latest_pr.get("draft", False):
                        logger.debug(f"Copilot PR #{pr_number} is still in draft (fallback)")
                        return "copilot_working"
                    else:
                        logger.info(f"✅ Copilot PR #{pr_number} assumed ready (fallback: non-draft)")
                        return "pr_ready_for_review"
        
        elif copilot_started and not copilot_finished:
            return "copilot_working"
        
        elif eyes_reaction:
            return "copilot_working"  # Copilot acknowledged but no PR yet
        
        else:
            return "waiting_for_copilot"  # Assigned but no activity yet
    
    except Exception as e:
        logger.warning(f"Could not check timeline for issue #{issue_number}: {e}")
        # Fallback to simple assignee check
        if copilot_assigned:
            return "copilot_working"
        else:
            return "waiting_for_copilot"

def auto_approve_and_merge_pr(issue: Dict[str, Any]) -> bool:
    """Enhanced auto-approve and merge the PR associated with an issue."""
    issue_number = issue["number"]
    
    # Use improved PR finding to locate the related PR
    related_prs = find_related_prs_for_issue(issue)
    
    # Find the first open PR
    related_pr = None
    for pr in related_prs:
        if pr["state"] == "open":
            related_pr = pr
            break
    
    if not related_pr:
        logger.error(f"No open Copilot PR found for issue #{issue_number}")
        return False
    
    pr_number = related_pr["number"]
    
    try:
        # Get detailed PR information
        pr_details = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}")
        
        # Double-check if PR is ready to merge
        is_ready, reason = is_pr_ready_to_merge(pr_details)
        if not is_ready:
            logger.warning(f"PR #{pr_number} is not ready to merge: {reason}")
            return False
        
        logger.info(f"PR #{pr_number} is ready to merge: {reason}")
        
        # Check if PR already has approving reviews from us
        existing_reviews = get_pr_reviews(pr_number)
        bot_review = None
        
        for review in existing_reviews:
            reviewer = review.get("user", {}).get("login", "")
            # Check if we've already reviewed this PR
            # Note: This might need adjustment based on the actual bot user
            if reviewer in ["github-actions[bot]", "dependabot[bot]"] or "bot" in reviewer.lower():
                bot_review = review
                break
        
        # 1. Create or update approval review
        if bot_review and bot_review["state"] == "APPROVED":
            logger.info(f"PR #{pr_number} already has bot approval review")
        else:
            review_data = {
                "body": "Auto-approved by GitHub Issue Queue Bot - Copilot implementation completed.\n\nThis PR has been automatically reviewed and meets the following criteria:\n- ✅ All status checks passed\n- ✅ No conflicts detected\n- ✅ Copilot implementation complete\n- ✅ No WIP indicators found",
                "event": "APPROVE"
            }
            
            logger.info(f"Auto-approving Copilot PR #{pr_number}")
            approval_result = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/reviews", 
                           method="POST", json=review_data)
            
            if approval_result:
                logger.info(f"✅ Created approval review #{approval_result.get('id', 'unknown')}")
        
        # Small delay to ensure review is processed
        import time
        time.sleep(2)
        
        # 2. Double-check merge readiness after approval
        updated_pr = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}")
        is_still_ready, updated_reason = is_pr_ready_to_merge(updated_pr)
        
        if not is_still_ready:
            logger.error(f"PR #{pr_number} became not ready after approval: {updated_reason}")
            return False
        
        # 3. Merge the PR using the updated API format
        merge_data = {
            "commit_title": f"Merge PR #{pr_number}: {related_pr['title']}",
            "commit_message": f"Resolves #{issue_number}\n\nAuto-merged by GitHub Issue Queue Bot after Copilot completion.\n\nCopilot has successfully implemented the requested feature/fix.\nAll automated checks have passed.",
            "merge_method": "squash"  # Use squash merge for cleaner history
        }
        
        logger.info(f"Auto-merging Copilot PR #{pr_number}")
        merge_result = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge", 
                                 method="PUT", json=merge_data)
        
        if merge_result:
            merge_sha = merge_result.get("sha", "unknown")
            logger.info(f"✅ Successfully merged Copilot PR #{pr_number}: {merge_result.get('message', 'Success')} (SHA: {merge_sha})")
        else:
            logger.info(f"✅ Successfully merged Copilot PR #{pr_number}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to auto-approve/merge Copilot PR #{pr_number}: {e}")
        
        # Log additional context for debugging
        try:
            error_pr = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}")
            logger.debug(f"PR state at error: mergeable={error_pr.get('mergeable')}, "
                        f"mergeable_state={error_pr.get('mergeable_state')}, "
                        f"draft={error_pr.get('draft')}")
        except:
            pass
        
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

def get_additional_assignee_ids(usernames: List[str]) -> List[str]:
    """Get GitHub usernames for additional assignees (not Copilot)."""
    valid_usernames = []
    logger.debug(f"Validating additional assignees: {usernames}")
    
    for username in usernames:
        logger.debug(f"Checking username: '{username}'")
        
        # Skip Copilot-related usernames as they're handled separately
        if username.lower() in ["copilot", "copilot-swe-agent"]:
            logger.debug(f"Skipping '{username}' - handled separately via GraphQL")
            continue
        
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
            logger.warning(f"Failed to lookup user '{username}': {e}")
    
    logger.debug(f"Final valid additional assignees: {valid_usernames}")
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

def create_issue(file_path: pathlib.Path, copilot_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub issue from a markdown file and assign to Copilot."""
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
        enhancement_labels = ["enhancement"]
        all_labels = [LABEL] + valid_content_labels + enhancement_labels
        
        # Remove duplicates while preserving order
        unique_labels = []
        seen = set()
        for label in all_labels:
            if label.lower() not in seen:
                unique_labels.append(label)
                seen.add(label.lower())
        
        logger.info(f"Issue will be created with labels: {unique_labels}")
        
        # Get additional assignees (non-Copilot)
        additional_assignees = []
        if ASSIGNEES:
            logger.debug(f"Additional ASSIGNEES from environment: {ASSIGNEES}")
            additional_assignees = get_additional_assignee_ids(ASSIGNEES)
            logger.debug(f"Valid additional assignees: {additional_assignees}")
        
        # Create issue using GraphQL with Copilot assignment
        query = """
        mutation CreateIssueWithCopilot($repositoryId: ID!, $title: String!, $body: String!, $assigneeIds: [ID!]!, $labelIds: [ID!]) {
          createIssue(input: {repositoryId: $repositoryId, title: $title, body: $body, assigneeIds: $assigneeIds, labelIds: $labelIds}) {
            issue {
              id
              number
              title
              url
              assignees(first: 10) {
                nodes {
                  login
                  id
                }
              }
              labels(first: 20) {
                nodes {
                  name
                  color
                }
              }
            }
          }
        }
        """
        
        # Get label IDs for GraphQL
        label_ids = []
        if unique_labels:
            try:
                # First, get existing labels to find their IDs
                existing_labels = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/labels")
                label_id_map = {label["name"]: label["node_id"] for label in existing_labels}
                
                for label_name in unique_labels:
                    if label_name in label_id_map:
                        label_ids.append(label_id_map[label_name])
                        logger.debug(f"Found ID for label '{label_name}'")
                    else:
                        logger.warning(f"Could not find ID for label '{label_name}' - it may not exist yet")
            except Exception as e:
                logger.warning(f"Could not get label IDs: {e}")
        
        # Prepare assignee IDs - Copilot first, then additional assignees
        assignee_ids = [copilot_info["copilot_id"]]
        
        # Note: Additional assignees would need their GraphQL IDs, but for now we'll focus on Copilot
        # The GraphQL API requires node IDs, not usernames for additional assignees
        
        variables = {
            "repositoryId": copilot_info["repository_id"],
            "title": title,
            "body": description,
            "assigneeIds": assignee_ids,
            "labelIds": label_ids
        }
        
        logger.info(f"Creating issue with Copilot assignment: {title}")
        logger.debug(f"GraphQL variables: {json.dumps({k: v for k, v in variables.items() if k != 'repositoryId'}, indent=2)}")
        
        try:
            logger.debug("Attempting to create issue with GraphQL...")
            data = graphql_request(query, variables)
            new_issue_data = data["createIssue"]["issue"]
            
            # Convert GraphQL response to REST API format for compatibility
            new_issue = {
                "number": new_issue_data["number"],
                "title": new_issue_data["title"],
                "html_url": new_issue_data["url"],
                "assignees": new_issue_data["assignees"]["nodes"],
                "labels": new_issue_data["labels"]["nodes"],
                "state": "open"
            }
            
            logger.info(f"✅ Created issue #{new_issue['number']}: {new_issue['html_url']}")
            
        except Exception as e:
            logger.error(f"GraphQL issue creation failed: {e}")
            # Fallback to REST API without Copilot assignment
            logger.info("Falling back to REST API issue creation...")
            
            issue_data = {
                "title": title,
                "body": description,
                "labels": unique_labels
            }
            
            if additional_assignees:
                issue_data["assignees"] = additional_assignees
                logger.info(f"Will assign to additional assignees: {additional_assignees}")
            
            new_issue = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues", method="POST", json=issue_data)
            logger.info(f"Created issue #{new_issue['number']}: {new_issue['html_url']}")
            
            # Now try to assign Copilot using GraphQL
            try:
                assign_query = """
                mutation AssignCopilot($assignableId: ID!, $actorIds: [ID!]!) {
                  replaceActorsForAssignable(input: {assignableId: $assignableId, actorIds: $actorIds}) {
                    assignable {
                      ... on Issue {
                        id
                        number
                        assignees(first: 10) {
                          nodes {
                            login
                          }
                        }
                      }
                    }
                  }
                }
                """
                
                # Get the GraphQL ID for the issue
                issue_query = """
                query GetIssueId($owner: String!, $name: String!, $number: Int!) {
                  repository(owner: $owner, name: $name) {
                    issue(number: $number) {
                      id
                    }
                  }
                }
                """
                
                issue_data_result = graphql_request(issue_query, {
                    "owner": REPO_OWNER,
                    "name": REPO_NAME,
                    "number": new_issue["number"]
                })
                
                issue_id = issue_data_result["repository"]["issue"]["id"]
                
                # Assign Copilot
                assign_variables = {
                    "assignableId": issue_id,
                    "actorIds": [copilot_info["copilot_id"]]
                }
                
                logger.info("Assigning Copilot to existing issue...")
                assign_result = graphql_request(assign_query, assign_variables)
                
                if assign_result:
                    assigned_logins = [a["login"] for a in assign_result["replaceActorsForAssignable"]["assignable"]["assignees"]["nodes"]]
                    logger.info(f"✅ Successfully assigned to: {assigned_logins}")
                
            except Exception as assign_error:
                logger.error(f"Failed to assign Copilot after issue creation: {assign_error}")
                logger.warning("Issue created but Copilot assignment failed - manual assignment may be needed")
        
        # Debug: Check actual assignments
        actual_assignees = new_issue.get('assignees', [])
        if actual_assignees:
            assignee_logins = [a.get('login', 'unknown') for a in actual_assignees]
            logger.info(f"✅ Final issue assignees: {assignee_logins}")
        else:
            logger.warning("⚠️ Issue has no assignees")
        
        if content_labels:
            applied_labels = new_issue.get('labels', [])
            applied_label_names = [l.get('name', 'unknown') for l in applied_labels]
            logger.info(f"Applied labels: {applied_label_names}")
        
        # Don't add a comment - Copilot will automatically start working when assigned
        logger.info("✅ Copilot will automatically start working on this issue")
        
        return new_issue
    
    except Exception as e:
        logger.error(f"Failed to create issue from {file_path}: {e}")
        raise

def promote_next_issue(copilot_info: Dict[str, Any]) -> bool:
    """
    Main logic: check if we can promote the next issue through the Copilot workflow.
    Returns True if an issue was created or workflow advanced, False if waiting.
    """
    logger.info("Checking for next issue to promote...")
    
    # Check if we have resume context from startup
    state = load_processed_files_state()
    resume_context = state.get("resume_context")
    
    if resume_context and resume_context.get("active_issue"):
        # We have an active issue from resume - use it instead of searching
        active_issue_info = resume_context["active_issue"]
        resume_action = resume_context.get("resume_action", "analyze_state")
        
        logger.info(f"📋 Resuming with active issue #{active_issue_info['number']}: {active_issue_info['title']}")
        logger.info(f"🎯 Resume action: {resume_action}")
        
        # Get fresh issue data from GitHub
        try:
            last_issue = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues/{active_issue_info['number']}")
        except Exception as e:
            logger.error(f"Could not fetch active issue #{active_issue_info['number']}: {e}")
            # Clear resume context and fall back to normal flow
            if "resume_context" in state:
                del state["resume_context"]
                save_processed_files_state(state)
            last_issue = get_last_bot_issue()
        
        # Clear resume context after first use
        if "resume_context" in state:
            del state["resume_context"]
            save_processed_files_state(state)
    else:
        # Normal flow - get the last bot issue
        last_issue = get_last_bot_issue()
    
    if last_issue:
        logger.info(f"Last bot issue: #{last_issue['number']} - {last_issue['title']}")
        
        # 2. Check the workflow status
        workflow_status = check_copilot_workflow_status(last_issue)
        logger.info(f"Current workflow status: {workflow_status}")
        
        if workflow_status == "waiting_for_copilot":
            logger.info("Issue assigned but Copilot hasn't started working yet...")
            return False
        
        elif workflow_status == "copilot_working":
            logger.info("Copilot is actively working on the issue...")
            # Log detailed monitoring information
            log_pr_monitoring_details(last_issue)
            return False
        
        elif workflow_status == "pr_ready_for_review":
            logger.info("Pull request is ready for review - auto-approving and merging...")
            # Log detailed status before attempting merge
            log_pr_monitoring_details(last_issue)
            success = auto_approve_and_merge_pr(last_issue)
            if success:
                logger.info("Pull request merged successfully - workflow advancing")
                
                # Mark the corresponding file as completed
                try:
                    # Try to extract filename from issue title or find it by file number
                    file_number = extract_issue_number_from_title(last_issue['title'])
                    if file_number is not None:
                        # Look for the file with this number
                        pattern = f"{file_number:03d}-*.md"
                        matching_files = list(ISSUES_DIR.glob(pattern))
                        if matching_files:
                            filename = matching_files[0].name
                            mark_file_as_completed(filename)
                            logger.info(f"Marked file {filename} as completed")
                    
                    # Alternative: check our state for files being processed
                    state = load_processed_files_state()
                    for file_entry in state.get("processed_files", []):
                        if (file_entry.get("issue_number") == last_issue["number"] and 
                            file_entry.get("status") == "processing"):
                            mark_file_as_completed(file_entry["filename"])
                            logger.info(f"Marked file {file_entry['filename']} as completed")
                            break
                            
                except Exception as e:
                    logger.warning(f"Could not mark file as completed: {e}")
                
                return True
            else:
                logger.error("Failed to merge pull request - will retry")
                return False
        
        elif workflow_status == "completed":
            logger.info(f"Previous issue #{last_issue['number']} workflow is complete")
            
            # Mark the corresponding file as completed if not already done
            try:
                file_number = extract_issue_number_from_title(last_issue['title'])
                if file_number is not None:
                    pattern = f"{file_number:03d}-*.md"
                    matching_files = list(ISSUES_DIR.glob(pattern))
                    if matching_files:
                        filename = matching_files[0].name
                        mark_file_as_completed(filename)
                        logger.info(f"Marked file {filename} as completed")
                
                # Alternative: check our state
                state = load_processed_files_state()
                for file_entry in state.get("processed_files", []):
                    if (file_entry.get("issue_number") == last_issue["number"] and 
                        file_entry.get("status") == "processing"):
                        mark_file_as_completed(file_entry["filename"])
                        logger.info(f"Marked file {file_entry['filename']} as completed")
                        break
                        
            except Exception as e:
                logger.warning(f"Could not mark file as completed: {e}")
        else:
            logger.warning(f"Unknown workflow status: {workflow_status}")
            return False
    else:
        logger.info("No previous bot issues found - starting from the beginning")
    
    # 3. Find the next file to process (only if previous workflow is complete or no previous issue)
    if last_issue and workflow_status not in ["completed"]:
        return False
    
    next_file = get_next_unprocessed_file()
    
    if not next_file:
        logger.info("Queue is empty - no more issues to promote")
        return False
    
    # 4. Create the new issue with Copilot assignment
    try:
        new_issue = create_issue(next_file, copilot_info)
        
        # Mark the file as being processed
        mark_file_as_processing(next_file.name, new_issue["number"])
        
        logger.info("✅ New issue created and assigned to Copilot")
        logger.info(f"🤖 Copilot will automatically start working on issue #{new_issue['number']}")
        return True
    except Exception as e:
        logger.error(f"Failed to create issue: {e}")
        return False

def show_status():
    """Enhanced status report with detailed PR monitoring."""
    logger.info("📊 Enhanced Status Report")
    logger.info("=" * 60)
    
    # Sync with GitHub first
    state = sync_processed_files_with_github()
    processed_files = state.get("processed_files", [])
    
    # Show resume context if available
    resume_context = state.get("resume_context")
    if resume_context:
        logger.info("🔄 Resume Context:")
        active_issue = resume_context.get("active_issue")
        if active_issue:
            logger.info(f"  Active Issue: #{active_issue['number']} - {active_issue['title']}")
            logger.info(f"  Workflow Status: {active_issue['workflow_status']}")
            logger.info(f"  Next Action: {resume_context.get('resume_action', 'unknown')}")
        else:
            logger.info(f"  Next Action: {resume_context.get('resume_action', 'unknown')}")
        logger.info("")
    
    # Get all markdown files
    if ISSUES_DIR.exists():
        all_files = sorted(ISSUES_DIR.glob("*.md"))
        logger.info(f"📁 Total files in issues directory: {len(all_files)}")
    else:
        all_files = []
        logger.info("📁 Issues directory not found")
    
    # Count by status
    completed = [f for f in processed_files if f.get("status") == "completed"]
    processing = [f for f in processed_files if f.get("status") == "processing"]
    
    logger.info(f"✅ Completed files: {len(completed)}")
    logger.info(f"🔄 Currently processing: {len(processing)}")
    logger.info(f"⏳ Remaining files: {len(all_files) - len(completed) - len(processing)}")
    logger.info("")
    
    # Show currently processing files with detailed status
    if processing:
        logger.info("🔄 Currently Processing Files (Detailed):")
        for file_entry in processing:
            filename = file_entry.get("filename", "unknown")
            issue_number = file_entry.get("issue_number", "unknown")
            created_at = file_entry.get("created_at", "unknown")
            
            logger.info(f"   📄 {filename}")
            logger.info(f"      GitHub Issue: #{issue_number}")
            logger.info(f"      Created: {created_at}")
            
            # Get the actual issue from GitHub to show current status
            try:
                issue = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}")
                workflow_status = check_copilot_workflow_status(issue)
                logger.info(f"      Workflow Status: {workflow_status}")
                
                # Show detailed PR information
                log_pr_monitoring_details(issue)
                
            except Exception as e:
                logger.warning(f"      ⚠️ Could not get issue status: {e}")
            
            logger.info("")
    
    # Show recently completed files
    if completed:
        logger.info("✅ Recently Completed Files (last 5):")
        recent_completed = sorted(completed, 
                                key=lambda f: f.get("completed_at", ""), 
                                reverse=True)[:5]
        
        for file_entry in recent_completed:
            filename = file_entry.get("filename", "unknown")
            issue_number = file_entry.get("issue_number", "unknown")
            completed_at = file_entry.get("completed_at", "unknown")
            logger.info(f"   ✅ {filename} (Issue #{issue_number}) - Completed: {completed_at}")
        logger.info("")
    
    # Show next file to process
    next_file = None
    try:
        processed_filenames = {f.get("filename") for f in processed_files if f.get("status") in ["completed", "processing"]}
        for file_path in all_files:
            if file_path.name not in processed_filenames:
                next_file = file_path.name
                break
    except Exception as e:
        logger.warning(f"Could not determine next file: {e}")
    
    if next_file:
        logger.info(f"⏭️  Next file to process: {next_file}")
    else:
        logger.info(f"🎉 All files have been processed!")
    
    logger.info("=" * 60)

def resume_bot_state(copilot_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resume bot state by analyzing GitHub repository and updating local state.
    This handles bot restarts by checking:
    1. Active bot issues and their workflow states
    2. Files that should be marked as completed
    3. Files that are currently in progress
    4. What the next action should be
    """
    logger.info("🔄 Resuming bot state from GitHub repository...")
    
    # First sync our state with GitHub
    state = sync_processed_files_with_github()
    
    # Get all bot issues (open and closed) to understand current state
    try:
        params = {
            "labels": LABEL,
            "state": "all",
            "sort": "created",
            "direction": "desc",  # Most recent first
            "per_page": 50
        }
        
        all_bot_issues = api_request(f"/repos/{REPO_OWNER}/{REPO_NAME}/issues", params=params)
        logger.info(f"Found {len(all_bot_issues)} total bot issues in repository")
        
        # Analyze the most recent open bot issue (if any)
        open_issues = [issue for issue in all_bot_issues if issue["state"] == "open"]
        
        if open_issues:
            latest_open_issue = open_issues[0]  # Most recent open issue
            logger.info(f"Latest open bot issue: #{latest_open_issue['number']} - {latest_open_issue['title']}")
            
            # Check its workflow status
            workflow_status = check_copilot_workflow_status(latest_open_issue)
            logger.info(f"Current workflow status: {workflow_status}")
            
            # Find corresponding local file
            file_number = extract_issue_number_from_title(latest_open_issue['title'])
            corresponding_file = None
            
            if file_number is not None:
                pattern = f"{file_number:03d}-*.md"
                matching_files = list(ISSUES_DIR.glob(pattern))
                if matching_files:
                    corresponding_file = matching_files[0].name
            
            # Update local state based on GitHub workflow state
            if corresponding_file:
                processed_files = state.get("processed_files", [])
                
                # Find existing entry or create new one
                file_entry = None
                for entry in processed_files:
                    if entry.get("filename") == corresponding_file:
                        file_entry = entry
                        break
                
                if not file_entry:
                    # Create new entry for this file
                    logger.info(f"Creating state entry for active issue file: {corresponding_file}")
                    file_entry = {
                        "filename": corresponding_file,
                        "issue_number": latest_open_issue["number"],
                        "status": "processing",
                        "created_at": latest_open_issue["created_at"]
                    }
                    processed_files.append(file_entry)
                else:
                    # Update existing entry
                    file_entry["issue_number"] = latest_open_issue["number"]
                    file_entry["status"] = "processing"
                
                state["processed_files"] = processed_files
                save_processed_files_state(state)
                
                logger.info(f"✅ Updated state for active file: {corresponding_file} (Issue #{latest_open_issue['number']})")
            
            # Store current active issue info for resume context
            state["resume_context"] = {
                "active_issue": {
                    "number": latest_open_issue["number"],
                    "title": latest_open_issue["title"],
                    "workflow_status": workflow_status,
                    "file": corresponding_file
                },
                "resume_action": determine_resume_action(workflow_status),
                "resumed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            
        else:
            logger.info("No open bot issues found - ready to start fresh")
            state["resume_context"] = {
                "active_issue": None,
                "resume_action": "create_next",
                "resumed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        
        # Double-check completed issues to ensure accuracy
        completed_issues = [issue for issue in all_bot_issues if issue["state"] == "closed"]
        logger.info(f"Found {len(completed_issues)} completed bot issues")
        
        # Ensure all completed issues are properly marked in our state
        for closed_issue in completed_issues:
            if is_issue_done(closed_issue):
                file_number = extract_issue_number_from_title(closed_issue['title'])
                if file_number is not None:
                    pattern = f"{file_number:03d}-*.md"
                    matching_files = list(ISSUES_DIR.glob(pattern))
                    if matching_files:
                        filename = matching_files[0].name
                        
                        # Check if this file is properly marked as completed
                        processed_files = state.get("processed_files", [])
                        file_entry = None
                        for entry in processed_files:
                            if entry.get("filename") == filename:
                                file_entry = entry
                                break
                        
                        if not file_entry or file_entry.get("status") != "completed":
                            logger.info(f"Marking completed issue file as done: {filename}")
                            mark_file_as_completed(filename)
        
        save_processed_files_state(state)
        
        # Log resume summary
        resume_context = state.get("resume_context", {})
        active_issue = resume_context.get("active_issue")
        resume_action = resume_context.get("resume_action", "unknown")
        
        if active_issue:
            logger.info(f"🎯 Resume Action: {resume_action}")
            logger.info(f"📋 Active Issue: #{active_issue['number']} ({active_issue['workflow_status']})")
        else:
            logger.info(f"🎯 Resume Action: {resume_action}")
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to resume bot state: {e}")
        logger.warning("Continuing with existing local state...")
        return load_processed_files_state()

def determine_resume_action(workflow_status: str) -> str:
    """Determine what action to take based on workflow status."""
    action_map = {
        "waiting_for_copilot": "monitor_copilot",
        "copilot_working": "monitor_copilot", 
        "pr_ready_for_review": "review_and_merge",
        "completed": "create_next"
    }
    return action_map.get(workflow_status, "analyze_state")

def main():
    """Main entry point."""
    # Check for help command
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return
    
    # Check for status command
    if "--status" in sys.argv:
        show_status()
        return
    
    # Check for resume/sync command
    if "--resume" in sys.argv or "--sync" in sys.argv:
        copilot_info = validate_environment()
        logger.info("🔄 Performing complete state sync and resume analysis...")
        resume_state = resume_bot_state(copilot_info)
        show_status()
        logger.info("✅ State sync complete. Use --continuous to start bot with this state.")
        return
    
    copilot_info = validate_environment()
    
    # Resume bot state on startup
    logger.info("🚀 Starting GitHub Issue Queue Bot...")
    resume_state = resume_bot_state(copilot_info)
    
    # Check if we're in continuous mode
    continuous = "--continuous" in sys.argv or "--daemon" in sys.argv
    
    if continuous:
        logger.info(f"🔄 Starting continuous Copilot workflow mode (polling every {POLL_INTERVAL} seconds)")
        logger.info(f"🤖 Copilot coding agent: {copilot_info['copilot_login']}")
        
        while True:
            try:
                activity = promote_next_issue(copilot_info)
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
        logger.info(f"🤖 Copilot coding agent: {copilot_info['copilot_login']}")
        success = promote_next_issue(copilot_info)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
