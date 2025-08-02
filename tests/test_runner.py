#!/usr/bin/env python3
"""
Comprehensive Test Runner for GitLab Issue Queue Bot
===================================================

Runs unit tests, mock integration tests, and provides easy test management.
This test runner can work without real GitLab credentials using the mock server.
"""

import os
import sys
import pathlib
import tempfile
import shutil
import time
import unittest
from typing import Dict, Any, List

# Add project directories to path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))
sys.path.insert(0, str(project_root / "tests"))

# Import test modules and dependencies
try:
    import promote_next as bot
    import mock_gitlab
    from mock_gitlab import MockGitLabServer
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)

class MockIntegrationTest:
    """Integration tests using mock GitLab server."""
    
    def __init__(self):
        self.server = MockGitLabServer(port=9999)
        self.temp_dir = None
        self.original_settings = {}
        
    def setup(self):
        """Set up test environment with mock server."""
        # Start mock server
        self.server.start()
        time.sleep(0.1)  # Give server time to start
        
        # Override bot settings to use mock server
        self.original_settings = {
            'GITLAB_API': bot.GITLAB_API,
            'PROJECT_ID': bot.PROJECT_ID,
            'LABEL': bot.LABEL,
            'ISSUES_DIR': bot.ISSUES_DIR
        }
        
        # Configure bot for mock server
        bot.GITLAB_API = "http://localhost:9999/api/v4"
        bot.PROJECT_ID = "12345"
        bot.LABEL = "test-label"
        
        # Create temporary issues directory
        self.temp_dir = tempfile.mkdtemp()
        bot.ISSUES_DIR = pathlib.Path(self.temp_dir)
        
        # Set environment variables
        os.environ["GITLAB_TOKEN"] = "mock-token"
        os.environ["PROJECT_ID"] = "12345"
        
        print(f"🔧 Mock test environment set up (temp dir: {self.temp_dir})")
    
    def teardown(self):
        """Clean up test environment."""
        # Stop server
        self.server.stop()
        
        # Restore settings
        for key, value in self.original_settings.items():
            setattr(bot, key, value)
        
        # Clean up temp directory
        if self.temp_dir and pathlib.Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
        
        print("🧹 Mock test environment cleaned up")
    
    def create_test_files(self, count: int = 3):
        """Create test markdown files."""
        for i in range(1, count + 1):
            filename = f"{i:03d}-mock-test-issue-{i}.md"
            filepath = bot.ISSUES_DIR / filename
            
            content = f"""Mock Test Issue {i}

## Description
This is a mock integration test issue number {i}.

## Tasks
- [ ] Mock task 1
- [ ] Mock task 2

## Acceptance Criteria
- [ ] Mock criterion 1
- [ ] Mock criterion 2

## Labels
mock, test, integration
"""
            filepath.write_text(content)
        
        print(f"📄 Created {count} mock test files")
    
    def test_first_issue_creation(self) -> bool:
        """Test creating the first issue."""
        print("\n🆕 Testing first issue creation with mock server...")
        
        try:
            # Create test files
            self.create_test_files(2)
            
            # Should have no existing issues
            last_issue = bot.get_last_bot_issue()
            if last_issue:
                print(f"⚠️  Unexpected existing issue: {last_issue}")
            
            # Promote first issue
            success = bot.promote_next_issue()
            
            if success:
                # Check if issue was created
                last_issue = bot.get_last_bot_issue()
                if last_issue:
                    print(f"✅ Successfully created issue #{last_issue['iid']}: {last_issue['title']}")
                    return True
                else:
                    print("❌ Promotion reported success but no issue found")
                    return False
            else:
                print("❌ First issue promotion failed")
                return False
                
        except Exception as e:
            print(f"❌ Error in first issue test: {e}")
            return False
    
    def test_waiting_for_open_issue(self) -> bool:
        """Test that bot waits when issue is still open."""
        print("\n⏳ Testing waiting for open issue...")
        
        try:
            # Get the last issue (should be open)
            last_issue = bot.get_last_bot_issue()
            if not last_issue:
                print("❌ No existing issue to test waiting")
                return False
            
            if last_issue['state'] != 'opened':
                print(f"⚠️  Issue is not open (state: {last_issue['state']}), skipping test")
                return True
            
            # Try to promote next - should fail because previous is open
            success = bot.promote_next_issue()
            
            if not success:
                print("✅ Bot correctly waited for open issue")
                return True
            else:
                print("❌ Bot should have waited but promoted anyway")
                return False
                
        except Exception as e:
            print(f"❌ Error in waiting test: {e}")
            return False
    
    def test_manual_close_progression(self) -> bool:
        """Test progression after manual close."""
        print("\n👤 Testing progression after manual close...")
        
        try:
            # Get last issue
            last_issue = bot.get_last_bot_issue()
            if not last_issue:
                print("❌ No issue to close manually")
                return False
            
            issue_iid = last_issue['iid']
            
            # Manually close the issue (no MR)
            self.server.state.close_issue(issue_iid)
            print(f"🔒 Manually closed issue #{issue_iid}")
            
            # Now bot should be able to promote next issue
            success = bot.promote_next_issue()
            
            if success:
                new_issue = bot.get_last_bot_issue()
                if new_issue['iid'] != issue_iid:
                    print(f"✅ Next issue created after manual close: #{new_issue['iid']}")
                    return True
                else:
                    print("❌ Same issue returned, no progression")
                    return False
            else:
                print("❌ Bot should have promoted after manual close")
                return False
                
        except Exception as e:
            print(f"❌ Error in manual close test: {e}")
            return False
    
    def test_merged_mr_progression(self) -> bool:
        """Test progression after MR merge."""
        print("\n🔀 Testing progression after MR merge...")
        
        try:
            # Create a scenario: issue closed by MR, then merge the MR
            issue_iid, mr_iid = self.server.create_scenario_issue_with_merged_mr()
            print(f"📋 Created test scenario: issue #{issue_iid} closed by merged MR !{mr_iid}")
            
            # Bot should be able to promote next issue
            success = bot.promote_next_issue()
            
            if success:
                print("✅ Next issue promoted after MR merge")
                return True
            else:
                print("❌ Bot should have promoted after MR merge")
                return False
                
        except Exception as e:
            print(f"❌ Error in MR merge test: {e}")
            return False
    
    def test_unmerged_mr_blocking(self) -> bool:
        """Test that unmerged MRs block progression."""
        print("\n🚫 Testing unmerged MR blocking...")
        
        try:
            # Reset and create scenario: issue closed by unmerged MR
            self.server.reset()
            issue_iid, mr_iid = self.server.create_scenario_issue_with_unmerged_mr()
            print(f"📋 Created test scenario: issue #{issue_iid} closed by unmerged MR !{mr_iid}")
            
            # Create test files for potential promotion
            self.create_test_files(1)
            
            # Bot should NOT be able to promote (MR not merged)
            success = bot.promote_next_issue()
            
            if not success:
                print("✅ Bot correctly blocked by unmerged MR")
                return True
            else:
                print("❌ Bot should have been blocked by unmerged MR")
                return False
                
        except Exception as e:
            print(f"❌ Error in unmerged MR test: {e}")
            return False
    
    def test_empty_queue(self) -> bool:
        """Test behavior with empty queue."""
        print("\n📭 Testing empty queue handling...")
        
        try:
            # Remove all test files
            for file in bot.ISSUES_DIR.glob("*.md"):
                file.unlink()
            
            # Bot should return False (queue empty)
            success = bot.promote_next_issue()
            
            if not success:
                print("✅ Bot correctly detected empty queue")
                return True
            else:
                print("❌ Bot should have detected empty queue")
                return False
                
        except Exception as e:
            print(f"❌ Error in empty queue test: {e}")
            return False
    
    def run_all_tests(self):
        """Run all mock integration tests."""
        print("🧪 Running Mock Integration Tests")
        print("=" * 50)
        
        try:
            self.setup()
            
            tests = [
                ("First Issue Creation", self.test_first_issue_creation),
                ("Waiting for Open Issue", self.test_waiting_for_open_issue),
                ("Manual Close Progression", self.test_manual_close_progression),
                ("Merged MR Progression", self.test_merged_mr_progression),
                ("Unmerged MR Blocking", self.test_unmerged_mr_blocking),
                ("Empty Queue Handling", self.test_empty_queue),
            ]
            
            results = []
            
            for test_name, test_func in tests:
                print(f"\n{'=' * 20} {test_name} {'=' * 20}")
                try:
                    result = test_func()
                    results.append((test_name, result))
                    status = "✅ PASS" if result else "❌ FAIL"
                    print(f"\n{status}: {test_name}")
                except Exception as e:
                    results.append((test_name, False))
                    print(f"\n❌ ERROR: {test_name} - {e}")
            
            # Print summary
            self._print_test_summary(results, "Mock Integration Tests")
            
            passed = sum(1 for _, result in results if result)
            return passed == len(results)
            
        finally:
            self.teardown()
    
    def _print_test_summary(self, results: List[tuple], test_type: str):
        """Print test summary."""
        print(f"\n{'=' * 50}")
        print(f"🎯 {test_type.upper()} SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print(f"🎉 All {test_type.lower()} passed!")
        else:
            print(f"💥 Some {test_type.lower()} failed!")

def run_unit_tests():
    """Run unit tests."""
    print("🔬 Running Unit Tests")
    print("=" * 50)
    
    # Set up minimal environment for unit tests
    os.environ["GITLAB_TOKEN"] = "test-token"
    os.environ["PROJECT_ID"] = "12345"
    
    # Discover and run unit tests
    test_dir = pathlib.Path(__file__).parent
    loader = unittest.TestLoader()
    
    try:
        suite = loader.discover(str(test_dir), pattern='test_*.py')
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print("\n🎉 All unit tests passed!")
            return True
        else:
            print(f"\n💥 Unit tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
            return False
    except Exception as e:
        print(f"❌ Error running unit tests: {e}")
        return False

def main():
    """Main test runner."""
    print("🚀 GitLab Issue Queue Bot - Comprehensive Test Suite")
    print("=" * 60)
    
    # Parse command line arguments
    run_unit = "--unit" in sys.argv or "--all" in sys.argv
    run_mock = "--mock" in sys.argv or "--all" in sys.argv
    run_all = "--all" in sys.argv or (not run_unit and not run_mock)
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python test_runner.py [options]")
        print("Options:")
        print("  --unit     Run unit tests only")
        print("  --mock     Run mock integration tests only")
        print("  --all      Run all tests (default)")
        print("  --help     Show this help message")
        return
    
    results = []
    
    # Run unit tests
    if run_unit or run_all:
        try:
            unit_success = run_unit_tests()
            results.append(("Unit Tests", unit_success))
        except Exception as e:
            print(f"❌ Unit test execution failed: {e}")
            results.append(("Unit Tests", False))
    
    # Run mock integration tests
    if run_mock or run_all:
        try:
            mock_tester = MockIntegrationTest()
            mock_success = mock_tester.run_all_tests()
            results.append(("Mock Integration Tests", mock_success))
        except Exception as e:
            print(f"❌ Mock integration test execution failed: {e}")
            results.append(("Mock Integration Tests", False))
    
    # Print overall summary
    if results:
        print(f"\n{'=' * 60}")
        print("🏆 OVERALL TEST SUMMARY")
        print("=" * 60)
        
        for test_type, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_type}")
        
        all_passed = all(success for _, success in results)
        
        if all_passed:
            print("\n🎉 All test suites passed! Bot is ready for deployment.")
        else:
            print("\n💥 Some test suites failed. Please fix issues before deploying.")
        
        sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
