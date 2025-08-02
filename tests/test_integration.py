#!/usr/bin/env python3
"""
Integration Tests for GitLab Issue Queue Bot
===========================================

Full end-to-end testing with real GitLab API calls (using test project).
These tests require actual GitLab credentials and should be run against
a dedicated test project.
"""

import os
import sys
import pathlib
import tempfile
import shutil
import time
import json
from typing import Dict, Any, List

# Add scripts directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import promote_next as bot
import test_gitlab

class GitLabIntegrationTest:
    """Integration test runner for GitLab bot functionality."""

    def __init__(self):
        """Initialize integration test environment."""
        self.temp_dir = None
        self.original_issues_dir = None
        self.test_label = f"integration-test-{int(time.time())}"
        self.created_issues = []
        
        # Validate environment
        if not os.environ.get("GITLAB_TOKEN") or not os.environ.get("PROJECT_ID"):
            raise ValueError("GITLAB_TOKEN and PROJECT_ID must be set for integration tests")
        
        # Override label to avoid conflicts
        self.original_label = bot.LABEL
        bot.LABEL = self.test_label
        
        print(f"🧪 Running integration tests with label: {self.test_label}")

    def setup(self):
        """Set up test environment."""
        # Create temporary issues directory
        self.temp_dir = tempfile.mkdtemp()
        self.original_issues_dir = bot.ISSUES_DIR
        bot.ISSUES_DIR = pathlib.Path(self.temp_dir)
        
        print(f"📁 Created test directory: {self.temp_dir}")

    def teardown(self):
        """Clean up test environment."""
        # Restore original settings
        if self.original_issues_dir:
            bot.ISSUES_DIR = self.original_issues_dir
        bot.LABEL = self.original_label
        
        # Clean up temporary directory
        if self.temp_dir and pathlib.Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            
        # Clean up created issues (close them)
        print(f"🧹 Cleaning up {len(self.created_issues)} test issues...")
        for issue_iid in self.created_issues:
            try:
                # Close the issue
                bot.api_request(
                    f"/projects/{bot.PROJECT_ID}/issues/{issue_iid}",
                    method="PUT",
                    json={"state_event": "close"}
                )
                print(f"✅ Closed test issue #{issue_iid}")
            except Exception as e:
                print(f"⚠️  Failed to close issue #{issue_iid}: {e}")

    def create_test_files(self, count: int = 3):
        """Create test markdown files."""
        for i in range(1, count + 1):
            filename = f"{i:03d}-test-issue-{i}.md"
            filepath = bot.ISSUES_DIR / filename
            
            content = f"""Test Issue {i}

## Description
This is integration test issue number {i}.

## Tasks
- [ ] Task 1 for issue {i}
- [ ] Task 2 for issue {i}
- [ ] Task 3 for issue {i}

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Labels
test, integration, issue-{i}

## Test Metadata
Created for integration testing at {time.strftime('%Y-%m-%d %H:%M:%S')}
Temporary label: {self.test_label}
"""
            filepath.write_text(content)
            print(f"📄 Created test file: {filename}")

    def test_connection(self) -> bool:
        """Test basic GitLab connection."""
        print("\n🔌 Testing GitLab connection...")
        try:
            # Test basic API access
            user_info = bot.api_request("/user")
            print(f"✅ Connected as: {user_info['name']} (@{user_info['username']})")
            
            # Test project access
            project_info = bot.api_request(f"/projects/{bot.PROJECT_ID}")
            print(f"✅ Project access: {project_info['name']}")
            
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

    def test_first_issue_creation(self) -> bool:
        """Test creating the first issue when none exist."""
        print("\n🆕 Testing first issue creation...")
        
        try:
            # Ensure no existing bot issues
            existing = bot.get_last_bot_issue()
            if existing:
                print(f"⚠️  Found existing issue #{existing['iid']}, continuing anyway...")
            
            # Create test files
            self.create_test_files(2)
            
            # Promote next issue
            success = bot.promote_next_issue()
            
            if success:
                # Find the created issue
                last_issue = bot.get_last_bot_issue()
                if last_issue:
                    self.created_issues.append(last_issue['iid'])
                    print(f"✅ Created issue #{last_issue['iid']}: {last_issue['web_url']}")
                    return True
                else:
                    print("❌ Issue creation reported success but no issue found")
                    return False
            else:
                print("❌ Issue creation returned False")
                return False
                
        except Exception as e:
            print(f"❌ First issue creation failed: {e}")
            return False

    def test_waiting_for_completion(self) -> bool:
        """Test that bot waits when previous issue is incomplete."""
        print("\n⏳ Testing waiting for issue completion...")
        
        try:
            last_issue = bot.get_last_bot_issue()
            if not last_issue:
                print("❌ No previous issue found to test waiting")
                return False
            
            # Issue should be open, so bot should wait
            if last_issue['state'] == 'opened':
                success = bot.promote_next_issue()
                if not success:
                    print("✅ Bot correctly waited for issue completion")
                    return True
                else:
                    print("❌ Bot should have waited but created issue anyway")
                    return False
            else:
                print(f"⚠️  Issue #{last_issue['iid']} is already closed, can't test waiting")
                return True  # Skip this test
                
        except Exception as e:
            print(f"❌ Waiting test failed: {e}")
            return False

    def test_manual_close_handling(self) -> bool:
        """Test handling of manually closed issues."""
        print("\n👤 Testing manual close handling...")
        
        try:
            last_issue = bot.get_last_bot_issue()
            if not last_issue:
                print("❌ No issue found to close manually")
                return False
            
            issue_iid = last_issue['iid']
            
            # Manually close the issue (without MR)
            bot.api_request(
                f"/projects/{bot.PROJECT_ID}/issues/{issue_iid}",
                method="PUT",
                json={"state_event": "close"}
            )
            print(f"✅ Manually closed issue #{issue_iid}")
            
            # Wait a moment for GitLab to process
            time.sleep(2)
            
            # Try to promote next issue - should succeed
            success = bot.promote_next_issue()
            
            if success:
                new_issue = bot.get_last_bot_issue()
                if new_issue and new_issue['iid'] != issue_iid:
                    self.created_issues.append(new_issue['iid'])
                    print(f"✅ Next issue created after manual close: #{new_issue['iid']}")
                    return True
                else:
                    print("❌ No new issue created after manual close")
                    return False
            else:
                print("❌ Bot should have created next issue after manual close")
                return False
                
        except Exception as e:
            print(f"❌ Manual close test failed: {e}")
            return False

    def test_queue_completion(self) -> bool:
        """Test behavior when queue is empty."""
        print("\n🏁 Testing queue completion...")
        
        try:
            # Remove all test files to simulate empty queue
            for file in bot.ISSUES_DIR.glob("*.md"):
                file.unlink()
            
            # Try to promote - should return False (queue empty)
            success = bot.promote_next_issue()
            
            if not success:
                print("✅ Bot correctly detected empty queue")
                return True
            else:
                print("❌ Bot should have detected empty queue")
                return False
                
        except Exception as e:
            print(f"❌ Queue completion test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        print("🚀 Starting GitLab Integration Tests")
        print("=" * 50)
        
        try:
            self.setup()
            
            tests = [
                ("Connection Test", self.test_connection),
                ("First Issue Creation", self.test_first_issue_creation),
                ("Waiting for Completion", self.test_waiting_for_completion),
                ("Manual Close Handling", self.test_manual_close_handling),
                ("Queue Completion", self.test_queue_completion),
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
            print(f"\n{'=' * 50}")
            print("🎯 INTEGRATION TEST SUMMARY")
            print("=" * 50)
            
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            for test_name, result in results:
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status}: {test_name}")
            
            print(f"\nTotal: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 All integration tests passed!")
                return True
            else:
                print("💥 Some integration tests failed!")
                return False
                
        finally:
            self.teardown()

def main():
    """Main entry point for integration tests."""
    # Check environment
    missing_vars = []
    if not os.environ.get("GITLAB_TOKEN"):
        missing_vars.append("GITLAB_TOKEN")
    if not os.environ.get("PROJECT_ID"):
        missing_vars.append("PROJECT_ID")
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables and try again.")
        sys.exit(1)
    
    # Warn about using real GitLab project
    print("⚠️  WARNING: Integration tests will create and modify real GitLab issues!")
    print(f"Project ID: {os.environ.get('PROJECT_ID')}")
    print("Make sure you're using a test project, not production!")
    
    response = input("\nContinue with integration tests? [y/N]: ")
    if response.lower() != 'y':
        print("Integration tests cancelled.")
        sys.exit(0)
    
    # Run tests
    test_runner = GitLabIntegrationTest()
    success = test_runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
