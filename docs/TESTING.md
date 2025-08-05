# Testing Strategy for Issue Queue Bot

This document outlines the testing strategy for the Issue Queue Bot, focusing on core functionality and unit tests.

## 🧪 Test Types

### 1. Unit Tests (`test_runner.py`)
**Purpose**: Test individual functions and core logic
**Coverage**:
- Issue file parsing and numbering
- Label extraction from markdown
- Environment variable validation
- File system operations
- Content parsing logic

**Run with**: `python tests/test_runner.py --unit`

### 2. Label Parsing Tests (`test_label_parsing.py`)
**Purpose**: Test label extraction and processing
**Features**:
- Label parsing from various markdown formats
- Edge case handling
- Label validation and formatting

**Run with**: `python tests/test_runner.py --labels`

### 3. Integration Capabilities
**Purpose**: Manual testing against live repository
**Note**: The bot is designed to work with actual repositories. For testing, use a dedicated test repository to avoid interfering with production work.

**Recommended approach**: Create a test repository and run the bot with test environment variables.

## 🚀 Quick Start

### Windows (Recommended)
```cmd
# Run all tests
run-tests.bat

# Run specific test types
run-tests.bat unit
run-tests.bat labels

# Get help
run-tests.bat help
```

### Command Line
```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
python tests/test_runner.py --all

# Run specific test suites
python tests/test_runner.py --unit
python tests/test_runner.py --labels
```

## 🎯 Test Scenarios Covered

### Core Logic Tests
- ✅ Issue file parsing and validation
- ✅ Number extraction from filenames
- ✅ Label parsing from markdown content
- ✅ Environment variable validation
- ✅ File system operations

### Content Processing Tests
- ✅ Markdown content parsing
- ✅ Label extraction from various formats
- ✅ Issue title and description extraction
- ✅ File numbering and sequencing

### Edge Cases
- ✅ Missing files or directories
- ✅ Invalid markdown formats
- ✅ Missing environment variables
- ✅ Empty or malformed label sections

## 📊 Test Coverage Goals

The test suite validates core functionality without requiring external API access:

- **Unit Test Coverage**: Core parsing and validation logic
- **Integration Ready**: Bot can be tested against real repositories
- **Edge Case Handling**: Robust error handling and validation
- **Environment Safety**: Tests use isolated temporary directories

## 🔍 Test Data

Tests use synthetic data created in temporary directories:
- Sample markdown files with various formats
- Test environment variables
- Isolated file system operations

## 🐛 Debugging Tests

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Environment Variables
```bash
export GITHUB_TOKEN=test-token
export REPO_OWNER=test-owner
export REPO_NAME=test-repo
export LABEL=test-label
```

## ⚡ Performance Considerations

### Test Execution Times
- Unit tests: < 5 seconds
- Label parsing tests: < 2 seconds

### Optimization Tips
- Tests run in parallel when possible
- Use temporary directories for isolation
- Clean up resources after each test

## 🚨 Troubleshooting

### Common Issues

**Import Errors**
```
ImportError: No module named 'promote_next'
```
**Solution**: Run tests from project root directory

**Permission Errors**
```
PermissionError: [Errno 13] Permission denied
```
**Solution**: Ensure write permissions in test directory

### Best Practices

1. **Always run from project root** - ensures proper imports
2. **Use isolated test data** - tests create temporary files
3. **Clean test environment** - tests clean up automatically
4. **Run tests before commits** - ensure code quality

## 📈 Continuous Integration

### GitHub Actions Integration
```yaml
- name: Run Tests
  run: |
    pip install -r requirements.txt
    python tests/test_runner.py --all
```

This streamlined testing strategy focuses on core functionality while maintaining reliability and ease of use!
