#!/usr/bin/env python3
"""
Test GitLab API Connection
==========================

Quick test script to validate GitLab API credentials and project access.
"""

import os
import sys
import requests
from pathlib import Path

def test_gitlab_connection():
    """Test GitLab API connection and permissions."""
    
    # Get configuration
    gitlab_url = os.environ.get("GITLAB_URL", "https://gitlab.com")
    gitlab_token = os.environ.get("GITLAB_TOKEN")
    project_id = os.environ.get("PROJECT_ID")
    
    if not gitlab_token:
        print("❌ GITLAB_TOKEN environment variable not set")
        return False
    
    if not project_id:
        print("❌ PROJECT_ID environment variable not set")
        return False
    
    api_base = f"{gitlab_url}/api/v4"
    headers = {"Private-Token": gitlab_token}
    
    print(f"🔗 Testing connection to {gitlab_url}")
    print(f"📋 Project ID: {project_id}")
    
    # Test 1: Basic API access
    try:
        response = requests.get(f"{api_base}/user", headers=headers)
        response.raise_for_status()
        user_info = response.json()
        print(f"✅ API Connection successful")
        print(f"👤 Authenticated as: {user_info.get('name')} (@{user_info.get('username')})")
    except requests.exceptions.RequestException as e:
        print(f"❌ API Connection failed: {e}")
        return False
    
    # Test 2: Project access
    try:
        response = requests.get(f"{api_base}/projects/{project_id}", headers=headers)
        response.raise_for_status()
        project_info = response.json()
        print(f"✅ Project access successful")
        print(f"📁 Project: {project_info.get('name')} ({project_info.get('web_url')})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Project access failed: {e}")
        if e.response and e.response.status_code == 404:
            print("   Project not found or no access permissions")
        return False
    
    # Test 3: Issues API access
    try:
        response = requests.get(
            f"{api_base}/projects/{project_id}/issues",
            headers=headers,
            params={"per_page": 1}
        )
        response.raise_for_status()
        print(f"✅ Issues API access successful")
    except requests.exceptions.RequestException as e:
        print(f"❌ Issues API access failed: {e}")
        return False
    
    # Test 4: Check for existing bot issues
    label = os.environ.get("LABEL", "auto-generated")
    try:
        response = requests.get(
            f"{api_base}/projects/{project_id}/issues",
            headers=headers,
            params={
                "labels": label,
                "scope": "all",
                "per_page": 5
            }
        )
        response.raise_for_status()
        existing_issues = response.json()
        print(f"✅ Found {len(existing_issues)} existing issues with label '{label}'")
        
        if existing_issues:
            print("📋 Recent bot issues:")
            for issue in existing_issues[:3]:
                status = "🟢 Open" if issue["state"] == "opened" else "🔴 Closed"
                print(f"   #{issue['iid']}: {issue['title']} ({status})")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not check existing issues: {e}")
        return False
    
    # Test 5: Check markdown files
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
    
    print("\n🎉 All tests passed! Your GitLab bot setup looks good.")
    return True

def main():
    """Main entry point."""
    print("🧪 GitLab Issue Queue Bot - Connection Test")
    print("=" * 50)
    
    success = test_gitlab_connection()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
