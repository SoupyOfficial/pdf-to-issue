#!/usr/bin/env python3
"""Check GitHub token permissions."""

import os

import requests


def check_permissions():
    token = os.getenv('GITHUB_TOKEN', '').strip()
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }

    # Check token scopes
    print("Checking GitHub token permissions...")
    response = requests.get('https://api.github.com/user', headers=headers)
    
    if response.status_code == 200:
        scopes = response.headers.get('X-OAuth-Scopes', 'No scopes header')
        print(f'✅ Token scopes: {scopes}')
        
        user_info = response.json()
        print(f'✅ Authenticated as: {user_info["login"]}')
        
        # Check repo info
        repo_response = requests.get('https://api.github.com/repos/SoupyOfficial/pdf-to-issue', headers=headers)
        if repo_response.status_code == 200:
            repo_info = repo_response.json()
            print(f'✅ Repository owner: {repo_info["owner"]["login"]}')
            print(f'✅ Repository is private: {repo_info["private"]}')
            
            permissions = repo_info.get("permissions", {})
            print(f'✅ Your permissions:')
            print(f'   - Admin: {permissions.get("admin", False)}')
            print(f'   - Push: {permissions.get("push", False)}')
            print(f'   - Pull: {permissions.get("pull", False)}')
            
            # Test creating a label (but don't actually create it)
            print("\nTesting label creation permissions...")
            test_label_response = requests.get(
                'https://api.github.com/repos/SoupyOfficial/pdf-to-issue/labels',
                headers=headers
            )
            if test_label_response.status_code == 200:
                print(f'✅ Can read labels (found {len(test_label_response.json())} existing labels)')
            else:
                print(f'❌ Cannot read labels: {test_label_response.status_code}')
                
        else:
            print(f'❌ Repo check failed: {repo_response.status_code}')
            print(f'   Response: {repo_response.text}')
    else:
        print(f'❌ Auth check failed: {response.status_code}')
        print(f'   Response: {response.text}')

if __name__ == "__main__":
    check_permissions()
