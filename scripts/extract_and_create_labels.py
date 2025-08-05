#!/usr/bin/env python3
"""
Extract labels from all markdown issues and create them in GitHub repository.
This script reads all markdown files in the issues/ directory, extracts labels,
and creates them in the specified GitHub repository if they don't already exist.
"""

import argparse
import os
import re
from pathlib import Path
from typing import List, Set, Tuple

import requests


def extract_labels_from_markdown(file_path: str) -> Set[str]:
    """
    Extract labels from a markdown file.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Set of labels found in the file
    """
    labels = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for labels section (both ## Labels and ### Labels)
        label_pattern = r'^(?:## Labels|### Labels)\s*\n(.+)$'
        match = re.search(label_pattern, content, re.MULTILINE)
        
        if match:
            labels_line = match.group(1).strip()
            # Split by comma and clean up each label
            for label in labels_line.split(','):
                label = label.strip()
                # Filter out invalid labels (corrupted ones with numbers/special chars)
                if label and is_valid_label(label):
                    labels.add(label)
                    
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        
    return labels


def is_valid_label(label: str) -> bool:
    """
    Check if a label is valid (not corrupted).
    
    Args:
        label: The label to validate
        
    Returns:
        True if the label is valid, False otherwise
    """
    # Filter out labels that look like corrupted data
    if re.match(r'^\d+/\d+', label):  # Labels starting with numbers like "264/878"
        return False
    if '?' in label and 'Issue' in label:  # Labels like "291/878? Issue 35 generated.refactor"
        return False
    if label.startswith('RUNNING'):  # Labels like "RUNNING INDE X"
        return False
    if len(label) > 50:  # Very long labels are likely corrupted
        return False
    if label.startswith('264/878-') or label.startswith('283/878-'):
        return False
    
    return True


def get_all_labels_from_issues(issues_dir: str) -> Set[str]:
    """
    Extract all unique labels from all markdown files in the issues directory.
    
    Args:
        issues_dir: Path to the issues directory
        
    Returns:
        Set of all unique labels found
    """
    all_labels = set()
    issues_path = Path(issues_dir)
    
    if not issues_path.exists():
        print(f"Error: Issues directory '{issues_dir}' does not exist")
        return all_labels
        
    # Find all markdown files
    md_files = list(issues_path.glob('*.md'))
    print(f"Found {len(md_files)} markdown files in {issues_dir}")
    
    for md_file in md_files:
        labels = extract_labels_from_markdown(str(md_file))
        if labels:
            print(f"  {md_file.name}: {', '.join(sorted(labels))}")
            all_labels.update(labels)
        else:
            print(f"  {md_file.name}: No labels found")
    
    return all_labels


def get_existing_labels(repo_owner: str, repo_name: str, token: str, github_url: str) -> Set[str]:
    """
    Get existing labels from the GitHub repository.
    
    Args:
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name
        token: GitHub personal access token
        github_url: GitHub API URL
        
    Returns:
        Set of existing label names
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    api_url = f"{github_url}/repos/{repo_owner}/{repo_name}/labels"
    
    try:
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            labels = response.json()
            existing_labels = {label['name'] for label in labels}
            print(f"Found {len(existing_labels)} existing labels in repository")
            return existing_labels
        else:
            print(f"Failed to get existing labels: {response.status_code}")
            print(f"Response: {response.text}")
            return set()
            
    except Exception as e:
        print(f"Error getting existing labels: {e}")
        return set()


def create_label(repo_owner: str, repo_name: str, token: str, github_url: str, 
                name: str, color: str = "d73a4a", description: str = "") -> bool:
    """
    Create a single label in the GitHub repository.
    
    Args:
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name
        token: GitHub personal access token
        github_url: GitHub API URL
        name: Label name
        color: Label color (hex code without #)
        description: Label description
        
    Returns:
        True if successful, False otherwise
    """
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    label_data = {
        "name": name,
        "color": color,
        "description": description
    }
    
    api_url = f"{github_url}/repos/{repo_owner}/{repo_name}/labels"
    
    try:
        response = requests.post(api_url, headers=headers, json=label_data)
        
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


def get_label_color_and_description(label_name: str) -> Tuple[str, str]:
    """
    Get appropriate color and description for a label based on its name.
    
    Args:
        label_name: Name of the label
        
    Returns:
        Tuple of (color, description)
    """
    # Define color mappings for common label types
    color_mappings = {
        # Architecture and foundation
        'architecture': ('1f77b4', 'Architecture and design related'),
        'foundation': ('ff7f0e', 'Foundation and core infrastructure'),
        'setup': ('2ca02c', 'Initial setup and configuration'),
        
        # UI/UX
        'ui': ('d62728', 'User interface components'),
        'ux': ('9467bd', 'User experience improvements'),
        'frontend': ('e377c2', 'Frontend development'),
        
        # Data and backend
        'data': ('8c564b', 'Data layer and persistence'),
        'backend': ('17becf', 'Backend development'),
        'database': ('bcbd22', 'Database related'),
        'firestore': ('7f7f7f', 'Firestore database'),
        'firebase': ('ff9800', 'Firebase services'),
        
        # Features
        'feature': ('00d4aa', 'New feature'),
        'feature-request': ('00d4aa', 'Feature request'),
        'enhancement': ('a2eeef', 'Enhancement to existing feature'),
        
        # Analytics and visualization
        'analytics': ('0366d6', 'Analytics and data analysis'),
        'charts': ('5319e7', 'Charts and visualization'),
        'visualization': ('5319e7', 'Data visualization'),
        'data-visualization': ('5319e7', 'Data visualization'),
        
        # Performance and testing
        'performance': ('fbca04', 'Performance optimization'),
        'testing': ('6f42c1', 'Testing and quality assurance'),
        
        # Sync and offline
        'sync': ('f9d0c4', 'Data synchronization'),
        'offline': ('c5def5', 'Offline functionality'),
        'offline-support': ('c5def5', 'Offline functionality support'),
        
        # Special categories
        'auto-generated': ('000000', 'Issues created by automation'),
        'bug': ('d73a4a', 'Something isn\'t working'),
        'documentation': ('0075ca', 'Improvements or additions to documentation'),
        
        # User experience
        'logging': ('bfd4f2', 'Logging functionality'),
        'export': ('d4c5f9', 'Data export features'),
        'tagging': ('c2e0c6', 'Tagging system'),
        'insights': ('fef2c0', 'User insights and intelligence'),
        'personalization': ('ffaaa5', 'Personalization features'),
    }
    
    # Check for exact matches first
    if label_name.lower() in color_mappings:
        return color_mappings[label_name.lower()]
    
    # Check for partial matches
    for key, (color, desc) in color_mappings.items():
        if key in label_name.lower():
            return color, f"{desc} (auto-detected)"
    
    # Default color and description
    return 'd73a4a', f"Label: {label_name}"


def main():
    """Main function to extract labels and create them in GitHub."""
    parser = argparse.ArgumentParser(
        description="Extract labels from markdown issues and create them in GitHub repository"
    )
    parser.add_argument(
        '--repo', '-r',
        help='Repository in format "owner/repo" (e.g., "SoupyOfficial/pdf-to-issue")'
    )
    parser.add_argument(
        '--repos',
        nargs='+',
        help='Multiple repositories in format "owner/repo" (alternative to --repo)'
    )
    parser.add_argument(
        '--token', '-t',
        help='GitHub personal access token (or set GITHUB_TOKEN env var)'
    )
    parser.add_argument(
        '--issues-dir', '-d',
        default='issues',
        help='Directory containing markdown issue files (default: issues)'
    )
    parser.add_argument(
        '--github-url',
        default='https://api.github.com',
        help='GitHub API URL (default: https://api.github.com)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without actually creating labels'
    )
    
    args = parser.parse_args()
    
    # Get token from argument or environment
    token = args.token or os.getenv('GITHUB_TOKEN', '').strip()
    if not token:
        print("Error: GitHub token is required. Use --token or set GITHUB_TOKEN environment variable")
        return 1
    
    # Determine which repositories to process
    repositories = []
    if args.repos:
        repositories = args.repos
    elif args.repo:
        repositories = [args.repo]
    else:
        print("Error: Either --repo or --repos must be specified")
        return 1
    
    # Process each repository
    total_success = 0
    for repo in repositories:
        try:
            repo_owner, repo_name = repo.split('/', 1)
        except ValueError:
            print(f"Error: Repository '{repo}' must be in format 'owner/repo'")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing repository: {repo_owner}/{repo_name}")
        print(f"Issues directory: {args.issues_dir}")
        print(f"GitHub URL: {args.github_url}")
        print(f"Dry run: {args.dry_run}")
        print("-" * 50)
        
        # Extract all labels from markdown files (only once for all repos)
        if not repositories or repo == repositories[0]:  # Only do this for the first repo
            print("1. Extracting labels from markdown files...")
            all_labels = get_all_labels_from_issues(args.issues_dir)
            
            if not all_labels:
                print("No labels found in markdown files")
                continue
            
            print(f"\nFound {len(all_labels)} unique labels:")
            for label in sorted(all_labels):
                print(f"  - {label}")
        
        print("\n" + "-" * 50)
        
        # Get existing labels from repository
        print("2. Getting existing labels from repository...")
        existing_labels = get_existing_labels(repo_owner, repo_name, token, args.github_url)
        
        # Determine which labels need to be created
        labels_to_create = all_labels - existing_labels
        
        if not labels_to_create:
            print("All labels already exist in the repository!")
            continue
        
        print(f"\nNeed to create {len(labels_to_create)} new labels:")
        for label in sorted(labels_to_create):
            color, description = get_label_color_and_description(label)
            print(f"  - {label} (#{color}) - {description}")
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN: No labels were actually created for {repo}")
            continue
        
        print("\n" + "-" * 50)
        
        # Create the new labels
        print("3. Creating new labels...")
        success_count = 0
        
        for label in sorted(labels_to_create):
            color, description = get_label_color_and_description(label)
            if create_label(repo_owner, repo_name, token, args.github_url, label, color, description):
                success_count += 1
        
        print(f"\n🎉 Created {success_count}/{len(labels_to_create)} labels successfully for {repo}!")
        total_success += success_count
        
        if success_count < len(labels_to_create):
            print("Some labels failed to create. Check the output above for details.")
    
    if args.dry_run:
        print(f"\n🔍 DRY RUN COMPLETE: Processed {len(repositories)} repositories")
        return 0
    
    print(f"\n🎊 COMPLETE: Successfully created {total_success} labels across {len(repositories)} repositories!")
    return 0


if __name__ == "__main__":
    exit(main())
