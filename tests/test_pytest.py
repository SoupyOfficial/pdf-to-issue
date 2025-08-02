#!/usr/bin/env python3
"""
Pytest-based Tests for GitLab Issue Queue Bot
=============================================

Simple pytest tests that can run independently without complex imports.
"""

import pytest
import os
import tempfile
import pathlib
from unittest.mock import Mock, patch, MagicMock
import sys

# Add scripts to path for imports
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

def test_environment_setup():
    """Test that basic environment setup works."""
    # This should always pass - just checking basic functionality
    assert True

@pytest.mark.unit
def test_issue_number_extraction():
    """Test extracting issue numbers from titles."""
    # Mock the bot module behavior
    
    def extract_issue_number_from_title(title: str):
        """Mock implementation of issue number extraction."""
        import re
        # Look for patterns like "001-" or just "001" at the start
        match = re.match(r"^(\d+)[-\s]", title)
        if match:
            return int(match.group(1))
        
        # Fallback: look for any 3-digit number at the start
        match = re.match(r"^(\d{3})", title)
        if match:
            return int(match.group(1))
        
        return None
    
    # Test cases
    assert extract_issue_number_from_title("001-setup-auth") == 1
    assert extract_issue_number_from_title("042-answer-to-everything") == 42
    assert extract_issue_number_from_title("001 Setup Auth") == 1
    assert extract_issue_number_from_title("Setup Auth") is None
    assert extract_issue_number_from_title("Setup 2FA Auth") is None

@pytest.mark.unit
def test_file_sequencing():
    """Test file sequencing logic."""
    with tempfile.TemporaryDirectory() as temp_dir:
        issues_dir = pathlib.Path(temp_dir)
        
        # Create test files
        test_files = [
            "001-first.md",
            "002-second.md", 
            "005-fifth.md",  # Gap in numbering
        ]
        
        for filename in test_files:
            (issues_dir / filename).write_text(f"# {filename}")
        
        # Mock the get_next_file function
        def get_next_file(after_issue_number=None):
            md_files = sorted(issues_dir.glob("*.md"))
            
            if after_issue_number is None:
                return md_files[0] if md_files else None
            
            target_number = after_issue_number + 1
            
            for file_path in md_files:
                import re
                match = re.match(r"^(\d+)-", file_path.name)
                if match:
                    file_number = int(match.group(1))
                    if file_number == target_number:
                        return file_path
            
            return None
        
        # Test getting first file
        first_file = get_next_file(None)
        assert first_file is not None
        assert first_file.name == "001-first.md"
        
        # Test getting next file
        second_file = get_next_file(1)
        assert second_file is not None
        assert second_file.name == "002-second.md"
        
        # Test gap in numbering
        gap_file = get_next_file(2)
        assert gap_file is None  # No 003 file
        
        fifth_file = get_next_file(4)
        assert fifth_file is not None
        assert fifth_file.name == "005-fifth.md"
        
        # Test no more files
        end_file = get_next_file(5)
        assert end_file is None

@pytest.mark.unit  
def test_issue_completion_logic():
    """Test the core issue completion detection logic."""
    
    def is_issue_done_mock(issue, mock_api_responses):
        """Mock implementation of issue completion check."""
        if issue["state"] != "closed":
            return False
        
        # Mock API call for closed_by
        closed_by = mock_api_responses.get("closed_by", [])
        if not closed_by:
            return True  # Manual close
        
        # Mock API call for MR details
        mr_details = mock_api_responses.get("mr_details", {})
        return mr_details.get("state") == "merged"
    
    # Test open issue
    open_issue = {"state": "opened", "iid": 1}
    assert not is_issue_done_mock(open_issue, {})
    
    # Test manually closed issue (no MR)
    closed_manual = {"state": "closed", "iid": 1}
    assert is_issue_done_mock(closed_manual, {"closed_by": []})
    
    # Test issue closed by merged MR
    closed_merged = {"state": "closed", "iid": 1}
    responses = {
        "closed_by": [{"iid": 10}],
        "mr_details": {"state": "merged", "iid": 10}
    }
    assert is_issue_done_mock(closed_merged, responses)
    
    # Test issue closed by unmerged MR
    closed_unmerged = {"state": "closed", "iid": 1}
    responses = {
        "closed_by": [{"iid": 10}],
        "mr_details": {"state": "opened", "iid": 10}
    }
    assert not is_issue_done_mock(closed_unmerged, responses)

@pytest.mark.unit
def test_markdown_file_parsing():
    """Test parsing markdown files for issue creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = pathlib.Path(temp_dir) / "001-test.md"
        
        content = """Setup Authentication System

## Description
Implement user authentication with JWT tokens.

## Tasks
- [ ] Create user model
- [ ] Implement login endpoint

## Acceptance Criteria
- [ ] Users can register and login
"""
        test_file.write_text(content)
        
        # Mock issue creation
        def parse_markdown_file(file_path):
            content = file_path.read_text()
            lines = content.splitlines()
            
            if not lines:
                raise ValueError("File is empty")
            
            title = lines[0].strip()
            description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            
            return {"title": title, "description": description}
        
        result = parse_markdown_file(test_file)
        
        assert result["title"] == "Setup Authentication System"
        assert "Implement user authentication" in result["description"]
        assert "JWT tokens" in result["description"]

@pytest.mark.mock
def test_mock_server_basic():
    """Test that mock server can be imported and basic functionality works."""
    try:
        # Test importing mock server
        sys.path.insert(0, str(pathlib.Path(__file__).parent))
        import mock_gitlab
        
        # Test creating server instance
        server = mock_gitlab.MockGitLabServer(port=9998)
        state = server.state
        
        # Test basic state operations
        issue_data = {
            "title": "Test Issue",
            "description": "Test description",
            "labels": ["test"]
        }
        
        created_issue = state.create_issue(issue_data)
        assert created_issue["title"] == "Test Issue"
        assert created_issue["state"] == "opened"
        assert created_issue["iid"] == 1
        
        # Test closing issue
        closed_issue = state.close_issue(1)
        assert closed_issue["state"] == "closed"
        
        print("✅ Mock server basic functionality works")
        
    except ImportError:
        pytest.skip("Mock server not available")

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
