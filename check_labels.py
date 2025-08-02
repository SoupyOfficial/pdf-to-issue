#!/usr/bin/env python3
"""Check existing labels in the GitHub repository."""

import os

import requests


def check_labels():
    token = os.getenv('GITHUB_TOKEN', '').strip()
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json'
    }

    print("Checking existing labels in repository...")
    response = requests.get('https://api.github.com/repos/SoupyOfficial/pdf-to-issue/labels', headers=headers)
    
    if response.status_code == 200:
        labels = response.json()
        print(f'Found {len(labels)} existing labels:')
        for label in labels:
            print(f'  - "{label["name"]}" (#{label["color"]})')
    else:
        print(f'Failed to get labels: {response.status_code}')
        print(f'Response: {response.text}')

if __name__ == "__main__":
    check_labels()
