#!/usr/bin/env python3
"""Create copilot label."""

import os

import requests


def create_copilot_label():
    token = os.getenv('GITHUB_TOKEN', '').strip()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json'
    }
    
    # Create copilot label
    label_data = {
        'name': 'copilot',
        'color': '0366d6',
        'description': 'Issues to be implemented by GitHub Copilot'
    }
    
    response = requests.post('https://api.github.com/repos/SoupyOfficial/pdf-to-issue/labels', headers=headers, json=label_data)
    if response.status_code == 201:
        print('✅ Created copilot label')
    elif response.status_code == 422:
        print('ℹ️ Copilot label already exists')
    else:
        print(f'❌ Failed to create copilot label: {response.status_code}')

if __name__ == "__main__":
    create_copilot_label()
