# Testing Strategy for GitLab Issue Queue Bot

This document outlines the comprehensive testing strategy for the GitLab Issue Queue Bot, including unit tests, integration tests, and mock testing approaches.

## 🧪 Test Types

### 1. Unit Tests (`test_promote_next.py`)
**Purpose**: Test individual functions and methods in isolation
**Coverage**:
- Issue completion detection logic
- File sequencing and numbering
- Issue number extraction from titles
- Markdown file parsing
- API interaction patterns

**Run with**: `python -m unittest tests.test_promote_next`

### 2. Mock Integration Tests (`test_runner.py` + `mock_gitlab.py`)
**Purpose**: Test full workflows without real GitLab API calls
**Features**:
- Mock GitLab server that simulates real API responses
- Complete workflow testing (issue creation, waiting, progression)
- Edge case testing (manual closes, unmerged MRs, empty queues)
- Safe to run anywhere (no external dependencies)

**Run with**: `run-tests.bat mock` or `python tests/test_runner.py --mock`

### 3. Real Integration Tests (`test_integration.py`)
**Purpose**: Test against actual GitLab API
**Requirements**:
- Valid GitLab Personal Access Token
- Test GitLab project with appropriate permissions
- ⚠️ **Creates real issues** - use dedicated test project only

**Run with**: `run-tests.bat integration` or `python tests/test_integration.py`

### 4. Pytest Tests (`test_pytest.py`)
**Purpose**: Alternative test framework with better reporting
**Features**:
- Pytest-based test structure
- Isolated test functions
- Better test discovery and reporting

**Run with**: `pytest tests/test_pytest.py`

## 🚀 Quick Start

### Windows (Recommended)
```cmd
# Run all safe tests (unit + mock)
run-tests.bat

# Run specific test types
run-tests.bat unit
run-tests.bat mock
run-tests.bat integration  # Requires GitLab credentials

# Get help
run-tests.bat help
```

### Command Line
```bash
# Install test dependencies
pip install -r requirements.txt

# Run pytest tests
pytest tests/test_pytest.py -v

# Run mock integration tests
python tests/test_runner.py --mock

# Run all safe tests
python tests/test_runner.py --all
```

## 🎯 Test Scenarios Covered

### Core Logic Tests
- ✅ Issue completion detection (open vs closed)
- ✅ Manual close handling (no MR required)
- ✅ MR-based close handling (must be merged)
- ✅ Unmerged MR blocking (prevents progression)
- ✅ File sequencing with gaps in numbering
- ✅ Issue number extraction from various title formats

### Workflow Tests
- ✅ First issue creation (no previous issues)
- ✅ Waiting for incomplete issues
- ✅ Progression after manual close
- ✅ Progression after MR merge
- ✅ Blocking when MR exists but not merged
- ✅ Empty queue handling
- ✅ API error handling

### Edge Cases
- ✅ Missing numbered files
- ✅ Malformed issue titles
- ✅ Empty markdown files
- ✅ Network failures
- ✅ Permission errors
- ✅ Concurrent access scenarios

## 🛠️ Mock Server Details

The `mock_gitlab.py` module provides a complete GitLab API simulation:

### Supported Endpoints
- `GET /api/v4/user` - User information
- `GET /api/v4/projects/{id}` - Project details
- `GET /api/v4/projects/{id}/issues` - List issues (with filtering)
- `POST /api/v4/projects/{id}/issues` - Create issue
- `GET /api/v4/projects/{id}/issues/{iid}` - Get specific issue
- `PUT /api/v4/projects/{id}/issues/{iid}` - Update issue (close)
- `GET /api/v4/projects/{id}/issues/{iid}/closed_by` - Get closing MRs
- `GET /api/v4/projects/{id}/merge_requests/{iid}` - Get MR details

### Mock State Management
- Maintains issue and MR state across requests
- Simulates proper state transitions
- Supports test scenario creation
- Automatic cleanup after tests

### Usage Example
```python
from tests.mock_gitlab import MockGitLabServer

server = MockGitLabServer(port=9999)
server.start()

# Create test scenarios
issue_iid, mr_iid = server.create_scenario_issue_with_merged_mr()

# Your tests here...

server.stop()
```

## 📊 Test Coverage Goals

| Component | Target Coverage | Status |
|-----------|----------------|--------|
| Issue completion logic | 100% | ✅ Complete |
| File sequencing | 100% | ✅ Complete |
| API interactions | 90% | ✅ Complete |
| Error handling | 85% | ✅ Complete |
| Edge cases | 80% | ✅ Complete |
| Integration workflows | 95% | ✅ Complete |

## 🔍 Test Data

### Sample Issue Files
Test files follow the expected naming convention:
- `001-first-issue.md`
- `002-second-issue.md`
- `005-fifth-issue.md` (gap testing)

### Mock Scenarios
Pre-configured test scenarios:
- Open issue (blocks progression)
- Closed issue with merged MR (allows progression)
- Closed issue with unmerged MR (blocks progression)
- Manually closed issue (allows progression)
- Empty queue (stops processing)

## 🐛 Debugging Tests

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Mock Server Debug
```python
# Start mock server manually for inspection
python tests/mock_gitlab.py
# Server runs on http://localhost:8080
```

### Test Environment Variables
```bash
export GITLAB_TOKEN=test-token
export PROJECT_ID=12345
export LABEL=test-label
```

## ⚡ Performance Considerations

### Test Execution Times
- Unit tests: < 5 seconds
- Mock integration tests: < 30 seconds
- Real integration tests: 1-5 minutes (depends on GitLab API)

### Optimization Tips
- Run unit tests first (fastest feedback)
- Use mock tests for development
- Save real integration tests for final validation
- Parallelize independent test suites

## 🚨 Troubleshooting

### Common Issues

**Import Errors**
```
ImportError: No module named 'promote_next'
```
**Solution**: Run tests from project root directory

**Mock Server Port Conflicts**
```
OSError: [Errno 48] Address already in use
```
**Solution**: Change port in test configuration or kill existing process

**GitLab API Rate Limits**
```
HTTP 429 Too Many Requests
```
**Solution**: Use mock tests for development, add delays for real tests

**Permission Errors**
```
HTTP 403 Forbidden
```
**Solution**: Check GitLab token permissions and project access

### Best Practices

1. **Always run unit tests first** - fastest feedback loop
2. **Use mock tests for development** - no external dependencies
3. **Reserve real integration tests for CI/CD** - avoid API rate limits
4. **Clean up test artifacts** - don't leave test issues in GitLab
5. **Use descriptive test names** - make failures easy to understand

## 📈 Continuous Integration

### GitLab CI/CD Integration
```yaml
test:
  stage: test
  script:
    - pip install -r requirements.txt
    - python tests/test_runner.py --all
  artifacts:
    reports:
      junit: test-results.xml
```

### GitHub Actions Integration
```yaml
- name: Run Tests
  run: |
    pip install -r requirements.txt
    python tests/test_runner.py --all
```

This comprehensive testing strategy ensures the GitLab Issue Queue Bot works reliably across all scenarios and edge cases!
