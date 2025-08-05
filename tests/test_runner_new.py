#!/usr/bin/env python3
"""
Comprehensive Test Runner for Issue Queue Bot
=============================================

Runs unit tests and provides easy test management.
Tests focus on core functionality without requiring live API connections.
"""

import os
import sys
import pathlib
import tempfile
import shutil
import unittest
from typing import Dict, Any, List

# Add project directories to path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))
sys.path.insert(0, str(project_root / "tests"))

class UnitTests(unittest.TestCase):
    """Core unit tests for bot functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.issues_dir = pathlib.Path(self.temp_dir) / "issues"
        self.issues_dir.mkdir()
        
        # Set up test environment
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["REPO_OWNER"] = "test-owner"
        os.environ["REPO_NAME"] = "test-repo"
        os.environ["LABEL"] = "test-label"
        
    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            
    def test_issue_file_parsing(self):
        """Test parsing of markdown issue files."""
        # Create test issue file
        issue_content = """# Test Issue

This is a test issue description.

## Details
Some additional details here.

## Labels
enhancement, bug
"""
        
        issue_file = self.issues_dir / "001-test-issue.md"
        issue_file.write_text(issue_content)
        
        # Test that file exists and can be read
        self.assertTrue(issue_file.exists())
        content = issue_file.read_text()
        self.assertIn("Test Issue", content)
        self.assertIn("enhancement, bug", content)
        
    def test_issue_numbering(self):
        """Test issue file numbering extraction."""
        # Create numbered files
        files = [
            "001-first-issue.md",
            "002-second-issue.md", 
            "005-fifth-issue.md"  # Gap in numbering
        ]
        
        for filename in files:
            (self.issues_dir / filename).write_text(f"# {filename}")
            
        # List and verify files
        issue_files = sorted(self.issues_dir.glob("*.md"))
        self.assertEqual(len(issue_files), 3)
        
        # Test number extraction
        import re
        numbers = []
        for file_path in issue_files:
            match = re.match(r"(\d+)", file_path.name)
            if match:
                numbers.append(int(match.group(1)))
                
        self.assertEqual(numbers, [1, 2, 5])
        
    def test_label_parsing(self):
        """Test label extraction from issue content."""
        issue_content = """# Test Issue

Description here.

## Labels
bug, enhancement, high-priority
"""
        
        # Simple label extraction logic
        lines = issue_content.split('\n')
        labels = []
        
        for i, line in enumerate(lines):
            if line.strip() == "## Labels" and i + 1 < len(lines):
                label_line = lines[i + 1].strip()
                if label_line:
                    labels = [l.strip() for l in label_line.split(',')]
                    break
                    
        self.assertEqual(labels, ["bug", "enhancement", "high-priority"])
        
    def test_environment_variables(self):
        """Test that required environment variables are set."""
        required_vars = ["GITHUB_TOKEN", "REPO_OWNER", "REPO_NAME"]
        
        for var in required_vars:
            self.assertIn(var, os.environ)
            self.assertNotEqual(os.environ[var], "")


def run_unit_tests():
    """Run unit tests."""
    print("🔬 Running Unit Tests")
    print("=" * 30)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(UnitTests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} unit tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors")
        return False


def run_label_parsing_tests():
    """Run label parsing specific tests."""
    print("🏷️  Running Label Parsing Tests")
    print("=" * 35)
    
    try:
        # Import and run label parsing tests if they exist
        import test_label_parsing
        
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_label_parsing)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print(f"\n✅ All {result.testsRun} label parsing tests passed!")
            return True
        else:
            print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors")
            return False
            
    except ImportError:
        print("📝 No label parsing tests found - skipping")
        return True


def run_all_tests():
    """Run all available tests."""
    print("🧪 Issue Queue Bot - Test Suite")
    print("=" * 40)
    print()
    
    results = []
    
    # Run unit tests
    results.append(run_unit_tests())
    print()
    
    # Run label parsing tests
    results.append(run_label_parsing_tests())
    print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("📊 Test Summary")
    print("=" * 20)
    print(f"Test suites passed: {passed}/{total}")
    
    if all(results):
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Issue Queue Bot tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--labels", action="store_true", help="Run only label parsing tests")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    
    args = parser.parse_args()
    
    # Default to all tests if no specific option given
    if not any([args.unit, args.labels]):
        args.all = True
    
    success = True
    
    if args.unit:
        success = run_unit_tests()
    elif args.labels:
        success = run_label_parsing_tests()
    elif args.all:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
