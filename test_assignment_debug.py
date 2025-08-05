#!/usr/bin/env python3
"""
Test script to demonstrate the new debug logging for Copilot assignment.
This shows how the assignment debugging will work without needing real credentials.
"""

import os
import sys
import logging
from pathlib import Path

# Add the scripts directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

# Import the functions we want to test
from promote_next_github import get_user_ids, COPILOT_ASSIGNEE, ASSIGNEES

# Set up logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_assignment_debug():
    """Test the assignment debug functionality."""
    print("🔍 Testing Assignment Debug Logging")
    print("=" * 50)
    
    print(f"COPILOT_ASSIGNEE from environment: '{COPILOT_ASSIGNEE}'")
    print(f"ASSIGNEES from environment: {ASSIGNEES}")
    print()
    
    # Test case 1: Empty assignees
    print("Test 1: Empty assignees list")
    result = get_user_ids([])
    print(f"Result: {result}")
    print()
    
    # Test case 2: Copilot assignee
    print("Test 2: Copilot assignee")
    result = get_user_ids(["copilot"])
    print(f"Result: {result}")
    print()
    
    # Test case 3: Mixed assignees
    print("Test 3: Mixed assignees")
    result = get_user_ids(["copilot", "nonexistent-user-12345", "github-actions[bot]"])
    print(f"Result: {result}")
    print()
    
    # Simulate the assignment logic from create_issue
    print("Test 4: Complete assignment flow simulation")
    all_assignees = []
    
    print(f"COPILOT_ASSIGNEE from environment: '{COPILOT_ASSIGNEE}'")
    print(f"Additional ASSIGNEES from environment: {ASSIGNEES}")
    
    if COPILOT_ASSIGNEE:
        all_assignees.append(COPILOT_ASSIGNEE)
        print(f"Added Copilot assignee: '{COPILOT_ASSIGNEE}'")
    else:
        print("COPILOT_ASSIGNEE is empty - no Copilot will be assigned")
        
    all_assignees.extend(ASSIGNEES)
    print(f"All assignees before deduplication: {all_assignees}")
    
    # Remove duplicates while preserving order
    unique_assignees = []
    seen = set()
    for assignee in all_assignees:
        if assignee and assignee.lower() not in seen:
            unique_assignees.append(assignee)
            seen.add(assignee.lower())
    
    print(f"Unique assignees after deduplication: {unique_assignees}")
    
    if unique_assignees:
        print(f"Attempting to validate {len(unique_assignees)} assignees: {unique_assignees}")
        valid_assignees = get_user_ids(unique_assignees)
        print(f"Validation result: {len(valid_assignees)} valid assignees: {valid_assignees}")
        
        if valid_assignees:
            print(f"✅ Would assign issue to: {valid_assignees}")
        else:
            print("⚠️ No valid assignees found - issue would be created without assignees")
    else:
        print("No assignees specified - issue would be created unassigned")

if __name__ == "__main__":
    test_assignment_debug()
