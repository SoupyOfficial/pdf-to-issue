#!/usr/bin/env python3
"""
Test Label Parsing for GitHub Bot
=================================

Quick test to verify label parsing from markdown files works correctly.
"""

import pathlib
import sys

# Add the scripts directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from promote_next_github import parse_labels_from_content


def test_label_parsing():
    """Test label parsing with various markdown formats."""
    
    test_cases = [
        # Test case 1: Standard format
        {
            "name": "Standard Labels section",
            "content": """
Title Here

## Overview
Some description

## Labels
foundation, architecture, setup

## Other Section
More content
""",
            "expected": ["foundation", "architecture", "setup"]
        },
        
        # Test case 2: Single label
        {
            "name": "Single label",
            "content": """
Title Here

## Labels  
bug-fix
""",
            "expected": ["bug-fix"]
        },
        
        # Test case 3: Labels with extra spaces
        {
            "name": "Labels with spaces",
            "content": """
Title Here

## Labels
  frontend  ,   backend   ,  api  
""",
            "expected": ["frontend", "backend", "api"]
        },
        
        # Test case 4: Case variations
        {
            "name": "Case variations",
            "content": """
Title Here

### Labels
enhancement, Feature, BUG
""",
            "expected": ["enhancement", "Feature", "BUG"]
        },
        
        # Test case 5: No labels section
        {
            "name": "No labels section",
            "content": """
Title Here

## Overview
Some description

## Tasks
- Task 1
- Task 2
""",
            "expected": []
        },
        
        # Test case 6: Empty labels
        {
            "name": "Empty labels section",
            "content": """
Title Here

## Labels

## Next Section
""",
            "expected": []
        }
    ]
    
    print("🧪 Testing Label Parsing")
    print("=" * 40)
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        result = parse_labels_from_content(test_case["content"])
        expected = test_case["expected"]
        
        if result == expected:
            print(f"   ✅ PASS: {result}")
        else:
            print(f"   ❌ FAIL: Expected {expected}, got {result}")
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    success = test_label_parsing()
    sys.exit(0 if success else 1)
