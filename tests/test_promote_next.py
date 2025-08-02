#!/usr/bin/env python3
"""
Unit Tests for GitLab Issue Queue Bot
====================================

Comprehensive test suite covering all bot functionality including:
- Issue completion detection logic
- File sequencing and numbering
- API interaction patterns
- Edge case handling
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import pathlib
import tempfile
import shutil
from typing import Dict, Any, List

# Add scripts directory to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent))

# Import the bot module
import promote_next as bot

class TestIssueCompletionDetection(unittest.TestCase):
    """Test the core logic for determining if an issue is complete."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_api = Mock()
        
    @patch('promote_next.api_request')
    def test_open_issue_not_done(self, mock_api):
        """Test that open issues are not considered done."""
        issue = {"state": "opened", "iid": 1}
        
        result = bot.is_issue_done(issue)
        
        self.assertFalse(result)
        # Should not call API for open issues
        mock_api.assert_not_called()

    @patch('promote_next.api_request')
    def test_closed_issue_no_mr_is_done(self, mock_api):
        """Test that manually closed issues (no MR) are considered done."""
        issue = {"state": "closed", "iid": 1}
        
        # Mock empty closed_by response (manual close)
        mock_api.return_value = []
        
        result = bot.is_issue_done(issue)
        
        self.assertTrue(result)
        mock_api.assert_called_once_with(f"/projects/{bot.PROJECT_ID}/issues/1/closed_by")

    @patch('promote_next.api_request')
    def test_closed_issue_merged_mr_is_done(self, mock_api):
        """Test that issues closed by merged MRs are considered done."""
        issue = {"state": "closed", "iid": 1}
        
        # Mock responses
        closed_by_response = [{"iid": 10}]  # MR #10 closed this issue
        mr_response = {"state": "merged", "iid": 10}
        
        mock_api.side_effect = [closed_by_response, mr_response]
        
        result = bot.is_issue_done(issue)
        
        self.assertTrue(result)
        self.assertEqual(mock_api.call_count, 2)

    @patch('promote_next.api_request')
    def test_closed_issue_unmerged_mr_not_done(self, mock_api):
        """Test that issues closed by unmerged MRs are not considered done."""
        issue = {"state": "closed", "iid": 1}
        
        # Mock responses
        closed_by_response = [{"iid": 10}]  # MR #10 closed this issue
        mr_response = {"state": "opened", "iid": 10}  # But MR is still open
        
        mock_api.side_effect = [closed_by_response, mr_response]
        
        result = bot.is_issue_done(issue)
        
        self.assertFalse(result)

class TestFileSequencing(unittest.TestCase):
    """Test file numbering and sequencing logic."""

    def setUp(self):
        """Set up temporary directory with test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_issues_dir = bot.ISSUES_DIR
        bot.ISSUES_DIR = pathlib.Path(self.temp_dir)
        
        # Create test files
        self.test_files = [
            "001-first-issue.md",
            "002-second-issue.md", 
            "003-third-issue.md",
            "005-fifth-issue.md",  # Gap in numbering
            "010-tenth-issue.md"
        ]
        
        for filename in self.test_files:
            filepath = bot.ISSUES_DIR / filename
            filepath.write_text(f"# {filename}\n\nTest content for {filename}")

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
        bot.ISSUES_DIR = self.original_issues_dir

    def test_get_first_file_when_no_previous_issue(self):
        """Test getting the first file when no issues exist yet."""
        result = bot.get_next_file(None)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "001-first-issue.md")

    def test_get_next_sequential_file(self):
        """Test getting the next file in sequence."""
        result = bot.get_next_file(1)  # After issue 1
        
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "002-second-issue.md")

    def test_get_file_with_gap_in_numbering(self):
        """Test handling gaps in file numbering."""
        result = bot.get_next_file(3)  # After issue 3, should skip to 5
        
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "005-fifth-issue.md")

    def test_no_next_file_available(self):
        """Test when no next file is available."""
        result = bot.get_next_file(10)  # After issue 10, no more files
        
        self.assertIsNone(result)

    def test_empty_issues_directory(self):
        """Test behavior with empty issues directory."""
        # Remove all files
        for file in bot.ISSUES_DIR.glob("*.md"):
            file.unlink()
            
        result = bot.get_next_file(None)
        
        self.assertIsNone(result)

class TestIssueNumberExtraction(unittest.TestCase):
    """Test extraction of issue numbers from titles."""

    def test_extract_standard_format(self):
        """Test extraction from standard format: '001-title'."""
        title = "001-setup-authentication-system"
        result = bot.extract_issue_number_from_title(title)
        self.assertEqual(result, 1)

    def test_extract_with_space(self):
        """Test extraction with space: '001 title'."""
        title = "001 Setup Authentication System"
        result = bot.extract_issue_number_from_title(title)
        self.assertEqual(result, 1)

    def test_extract_three_digit_number(self):
        """Test extraction of three-digit numbers."""
        title = "042-answer-to-everything"
        result = bot.extract_issue_number_from_title(title)
        self.assertEqual(result, 42)

    def test_no_number_in_title(self):
        """Test handling titles without numbers."""
        title = "Setup Authentication System"
        result = bot.extract_issue_number_from_title(title)
        self.assertIsNone(result)

    def test_number_in_middle_of_title(self):
        """Test that numbers in the middle are ignored."""
        title = "Setup 2FA Authentication System"
        result = bot.extract_issue_number_from_title(title)
        self.assertIsNone(result)

class TestIssueCreation(unittest.TestCase):
    """Test issue creation from markdown files."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_create_issue_basic_format(self):
        """Test creating issue from basic markdown file."""
        # Create test file
        test_file = pathlib.Path(self.temp_dir) / "001-test-issue.md"
        content = """Setup Authentication System

## Description
Implement user authentication with JWT tokens.

## Tasks
- [ ] Create user model
- [ ] Implement login endpoint
- [ ] Add JWT middleware

## Acceptance Criteria
- [ ] Users can register and login
- [ ] JWT tokens are properly validated
"""
        test_file.write_text(content)
        
        with patch('promote_next.api_request') as mock_api, \
             patch('promote_next.get_user_ids') as mock_get_users:
            
            mock_get_users.return_value = []
            mock_api.return_value = {
                "iid": 42,
                "web_url": "https://gitlab.com/project/issues/42"
            }
            
            result = bot.create_issue(test_file)
            
            # Verify API was called with correct data
            mock_api.assert_called_once()
            call_args = mock_api.call_args
            
            self.assertEqual(call_args[0][0], f"/projects/{bot.PROJECT_ID}/issues")
            self.assertEqual(call_args[1]["method"], "POST")
            
            json_data = call_args[1]["json"]
            self.assertEqual(json_data["title"], "Setup Authentication System")
            self.assertIn("Implement user authentication", json_data["description"])
            self.assertIn(bot.LABEL, json_data["labels"])

    def test_create_issue_empty_file(self):
        """Test handling of empty files."""
        test_file = pathlib.Path(self.temp_dir) / "002-empty.md"
        test_file.write_text("")
        
        with self.assertRaises(ValueError):
            bot.create_issue(test_file)

class TestAPIIntegration(unittest.TestCase):
    """Test API interaction patterns."""

    @patch('promote_next.requests.request')
    def test_api_request_success(self, mock_request):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"test": "data"}
        mock_request.return_value = mock_response
        
        result = bot.api_request("/test")
        
        self.assertEqual(result, {"test": "data"})
        mock_request.assert_called_once()

    @patch('promote_next.requests.request')
    def test_api_request_http_error(self, mock_request):
        """Test API request with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_request.return_value = mock_response
        
        with self.assertRaises(Exception):
            bot.api_request("/test")

class TestMainLogic(unittest.TestCase):
    """Test the main promotion logic."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_issues_dir = bot.ISSUES_DIR
        bot.ISSUES_DIR = pathlib.Path(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)
        bot.ISSUES_DIR = self.original_issues_dir

    @patch('promote_next.get_last_bot_issue')
    @patch('promote_next.create_issue')
    def test_promote_first_issue(self, mock_create, mock_get_last):
        """Test promoting the first issue when none exist."""
        # No previous issues
        mock_get_last.return_value = None
        
        # Create first file
        test_file = bot.ISSUES_DIR / "001-first.md"
        test_file.write_text("First Issue\n\nDescription")
        
        mock_create.return_value = {"iid": 1, "web_url": "http://test"}
        
        result = bot.promote_next_issue()
        
        self.assertTrue(result)
        mock_create.assert_called_once()

    @patch('promote_next.get_last_bot_issue')
    @patch('promote_next.is_issue_done')
    def test_wait_for_incomplete_issue(self, mock_is_done, mock_get_last):
        """Test waiting when previous issue is not complete."""
        # Previous issue exists but not done
        mock_get_last.return_value = {"iid": 1, "title": "001-first", "state": "opened"}
        mock_is_done.return_value = False
        
        result = bot.promote_next_issue()
        
        self.assertFalse(result)

    @patch('promote_next.get_last_bot_issue')
    @patch('promote_next.is_issue_done')
    @patch('promote_next.create_issue')
    def test_promote_next_after_completion(self, mock_create, mock_is_done, mock_get_last):
        """Test promoting next issue after previous is complete."""
        # Previous issue is done
        mock_get_last.return_value = {"iid": 1, "title": "001-first-issue", "state": "closed"}
        mock_is_done.return_value = True
        
        # Create next file
        test_file = bot.ISSUES_DIR / "002-second.md"
        test_file.write_text("Second Issue\n\nDescription")
        
        mock_create.return_value = {"iid": 2, "web_url": "http://test"}
        
        result = bot.promote_next_issue()
        
        self.assertTrue(result)
        mock_create.assert_called_once()

if __name__ == "__main__":
    # Set up test environment variables
    os.environ["GITLAB_TOKEN"] = "test-token"
    os.environ["PROJECT_ID"] = "12345"
    
    unittest.main(verbosity=2)
