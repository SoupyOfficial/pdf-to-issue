#!/usr/bin/env python3
"""
Test GitHub API Connection
==========================

Quick test script to validate GitHub API credentials and repository access.
"""

import os
import sys
from pathlib import Path

import requests


def test_github_connection():
    """Test GitHub API connection and permissions."""
    
    # Get configuration
    github_url = os.environ.get("GITHUB_URL", "https://api.github.com")
    github_token = os.environ.get("GITHUB_TOKEN")
    repo_owner = os.environ.get("REPO_OWNER")
    repo_name = os.environ.get("REPO_NAME")
    
    if not github_token:
        print("❌ GITHUB_TOKEN environment variable not set")
        return False
    
    if not repo_owner:
        print("❌ REPO_OWNER environment variable not set")
        return False
    
    if not repo_name:
        print("❌ REPO_NAME environment variable not set")
        return False
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Issue-Queue-Bot/1.0"
    }
    
    print(f"🔗 Testing connection to {github_url}")
    print(f"📋 Repository: {repo_owner}/{repo_name}")
    
    # Test 1: Basic API access
    try:
        response = requests.get(f"{github_url}/user", headers=headers)
        response.raise_for_status()
        user_info = response.json()
        print(f"✅ API Connection successful")
        print(f"👤 Connected as: {user_info['name']} (@{user_info['login']})")
        print(f"🔑 Token scopes: {response.headers.get('X-OAuth-Scopes', 'Not available')}")
    except requests.exceptions.RequestException as e:
        print(f"❌ API connection failed: {e}")
        return False
    
    # Test 2: Repository access
    try:
        response = requests.get(f"{github_url}/repos/{repo_owner}/{repo_name}", headers=headers)
        response.raise_for_status()
        repo_info = response.json()
        print(f"✅ Repository access confirmed")
        print(f"📝 Repository: {repo_info['full_name']} ({'private' if repo_info['private'] else 'public'})")
        print(f"🌟 Stars: {repo_info['stargazers_count']}, Forks: {repo_info['forks_count']}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Repository access failed: {e}")
        if e.response and e.response.status_code == 404:
            print("   Repository not found or no access permission")
        return False
    
    # Test 3: Issues access (read)
    try:
        response = requests.get(f"{github_url}/repos/{repo_owner}/{repo_name}/issues", 
                              headers=headers, params={"per_page": 1})
        response.raise_for_status()
        issues = response.json()
        print(f"✅ Issues read access confirmed")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not read issues: {e}")
        return False
    
    # Test 4: Issues write access (test creation permissions)
    try:
        # We'll check if we can access the issues creation endpoint
        # without actually creating an issue
        response = requests.get(f"{github_url}/repos/{repo_owner}/{repo_name}", headers=headers)
        response.raise_for_status()
        repo_data = response.json()
        
        permissions = repo_data.get("permissions", {})
        if permissions.get("push", False) or permissions.get("admin", False):
            print(f"✅ Issues write access confirmed (push/admin permissions)")
        else:
            print(f"⚠️  Limited permissions - may not be able to create issues")
            print(f"   Current permissions: {permissions}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not check write permissions: {e}")
        return False
    
    # Test 5: Check existing issues with bot label
    try:
        label = os.environ.get("LABEL", "auto-generated")
        response = requests.get(f"{github_url}/repos/{repo_owner}/{repo_name}/issues", 
                              headers=headers, params={"labels": label, "state": "all", "per_page": 5})
        response.raise_for_status()
        bot_issues = response.json()
        
        print(f"🏷️  Found {len(bot_issues)} existing issues with label '{label}'")
        if bot_issues:
            print("📋 Recent bot issues:")
            for issue in bot_issues:
                status = "🟢 Open" if issue["state"] == "open" else "🔴 Closed"
                print(f"   #{issue['number']}: {issue['title']} ({status})")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not check existing issues: {e}")
        return False
    
    # Test 6: Check markdown files
    issues_dir = Path("issues")
    if not issues_dir.exists():
        print(f"⚠️  Issues directory '{issues_dir}' does not exist")
        return False
    
    md_files = sorted(issues_dir.glob("*.md"))
    print(f"📄 Found {len(md_files)} markdown files in issues/")
    
    if md_files:
        print("📋 Available files:")
        for i, file_path in enumerate(md_files[:5]):
            print(f"   {file_path.name}")
            if i == 4 and len(md_files) > 5:
                print(f"   ... and {len(md_files) - 5} more")
    else:
        print("⚠️  No markdown files found - nothing to promote")
    
    print("\n🎉 All tests passed! Your GitHub bot setup looks good.")
    return True

def main():
    """Main entry point."""
    print("🧪 GitHub Issue Queue Bot - Connection Test")
    print("=" * 50)
    
    success = test_github_connection()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
