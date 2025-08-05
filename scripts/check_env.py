#!/usr/bin/env python3
"""
Environment Setup Checker
========================

Verifies that your .env file is properly configured for the AshTrail project.
"""

import os
import pathlib


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = pathlib.Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found!")
        print("Please create .env file using .env.github.example as a template.")
        return False
    
    # Read .env file
    env_vars = {}
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False
    
    # Check required variables
    required_vars = {
        'GITHUB_TOKEN': 'GitHub Personal Access Token',
        'REPO_OWNER': 'Repository Owner (SoupyOfficial)',
        'REPO_NAME': 'Repository Name (AshTrail)',
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if var not in env_vars or not env_vars[var] or env_vars[var] == f'your_{var.lower()}_here':
            missing_vars.append(f"  {var}: {description}")
    
    if missing_vars:
        print("❌ Missing or incomplete required variables in .env:")
        for var in missing_vars:
            print(var)
        return False
    
    # Check token format
    github_token = env_vars.get('GITHUB_TOKEN', '')
    if not github_token.startswith(('ghp_', 'github_pat_')):
        print("⚠️  Warning: GITHUB_TOKEN doesn't look like a valid GitHub token")
        print("   Expected format: ghp_... or github_pat_...")
    
    print("✅ .env file looks good!")
    print(f"   Repository: {env_vars['REPO_OWNER']}/{env_vars['REPO_NAME']}")
    print(f"   Token: {github_token[:12]}...")
    
    return True

def main():
    print("AshTrail Environment Setup Checker")
    print("=" * 40)
    
    if check_env_file():
        print("\n🚀 You're ready to use the AshTrail launch configurations!")
        print("   Use the configurations ending with '(AshTrail)' in VS Code's debugger.")
    else:
        print(f"\n📝 To fix this:")
        print(f"1. Copy .env.github.example to .env")
        print(f"2. Edit .env with your actual values")
        print(f"3. Run this script again to verify")

if __name__ == '__main__':
    main()
