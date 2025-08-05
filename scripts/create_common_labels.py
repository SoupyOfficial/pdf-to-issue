#!/usr/bin/env python3
"""Create common labels for the pdf-to-issue project."""

import os

import requests


def create_label(name, color, description=""):
    """Create a single label."""
    token = os.getenv('GITHUB_TOKEN', '').strip()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json'
    }
    
    label_data = {
        "name": name,
        "color": color,
        "description": description
    }
    
    try:
        response = requests.post(
            'https://api.github.com/repos/SoupyOfficial/pdf-to-issue/labels',
            headers=headers,
            json=label_data
        )
        
        if response.status_code == 201:
            print(f"✅ Created label: {name}")
            return True
        elif response.status_code == 422:
            print(f"⚠️  Label already exists: {name}")
            return True
        else:
            print(f"❌ Failed to create label '{name}': {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating label '{name}': {e}")
        return False

def main():
    """Create common project labels."""
    labels = [
        ("architecture", "1f77b4", "Architecture and design related"),
        ("foundation", "ff7f0e", "Foundation and core infrastructure"),
        ("setup", "2ca02c", "Initial setup and configuration"),
        ("ui", "d62728", "User interface and presentation layer"),
        ("data", "9467bd", "Data layer and persistence"),
        ("testing", "8c564b", "Testing and quality assurance"),
        ("performance", "e377c2", "Performance optimization"),
        ("sync", "7f7f7f", "Data synchronization"),
        ("charts", "bcbd22", "Charts and visualization"),
        ("offline", "17becf", "Offline functionality"),
        ("auto-generated", "000000", "Issues created by the GitHub bot")
    ]
    
    print("Creating common project labels...")
    success_count = 0
    
    for name, color, description in labels:
        if create_label(name, color, description):
            success_count += 1
    
    print(f"\nCompleted: {success_count}/{len(labels)} labels processed")

if __name__ == "__main__":
    main()
