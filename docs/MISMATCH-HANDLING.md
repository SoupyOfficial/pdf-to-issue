# Mismatch Handling: Local File Numbers vs GitHub Issue Numbers

## Problem Statement

When using the Issue Queue Bot on repositories that already have existing issues and pull requests, there's often a mismatch between:

- **Local file numbers**: Files named like `001-feature.md`, `002-bug-fix.md`, etc.
- **GitHub issue numbers**: Issues might be created as #47, #48, etc. if the repo already has 46 issues

This mismatch makes it difficult to track which files have been processed and find related pull requests.

## Solution Overview

The enhanced Issue Queue Bot now implements multiple strategies to handle this mismatch:

### 1. State File Tracking

The bot maintains a state file (`logs/processed_files.json`) that tracks:

```json
{
  "processed_files": [
    {
      "filename": "001-setup-architecture.md",
      "issue_number": 47,
      "status": "completed",
      "created_at": "2023-12-25T10:00:00Z",
      "completed_at": "2023-12-25T15:30:00Z"
    }
  ],
  "last_completed_file": "001-setup-architecture.md"
}
```

### 2. Multi-Strategy PR Detection

When looking for pull requests related to an issue, the bot now uses multiple strategies:

#### Strategy 1: Direct Issue Number Reference
- Looks for `#42`, `fixes #42`, `closes #42` in PR titles/bodies
- Traditional approach that works when PRs explicitly reference the GitHub issue number

#### Strategy 2: [WIP] Marker Detection
- Looks for `[WIP]` markers in PR titles or bodies
- Combined with Copilot authorship and timing correlation
- Useful when Copilot creates work-in-progress PRs

#### Strategy 3: Time-Based Correlation
- Finds PRs created by `copilot-swe-agent` within 24 hours after issue creation
- Helps catch PRs that don't have explicit issue references

#### Strategy 4: File Number Reference
- Extracts the file number (e.g., `001`) from the issue title
- Looks for references to this number in PR titles/bodies
- Matches patterns like `001`, `#1`, `issue 1`

### 3. State Synchronization

The bot can sync its local state with GitHub to recover from any inconsistencies:

- Scans all bot-created issues on GitHub
- Matches them to local files based on file numbers in titles
- Updates the state file with current status
- Handles cases where files were processed outside the bot

## Usage

### Check Current Status

```bash
python scripts/promote_next.py --status
```

This will:
- Sync state with GitHub
- Show completed, processing, and remaining files
- Display the next file to be processed

### Regular Operation

The bot automatically handles mismatches during normal operation:

```bash
# Single run
python scripts/promote_next.py

# Continuous monitoring
python scripts/promote_next.py --continuous
```

### State File Location

The state file is stored at `logs/processed_files.json` and contains:

- `processed_files`: Array of file processing records
- `last_completed_file`: Name of the most recently completed file

## Example Scenarios

### Scenario 1: Fresh Repository
- Local files: `001-feature.md`, `002-bug.md`
- GitHub issues: Created as #1, #2
- **Result**: Direct correlation, traditional matching works

### Scenario 2: Existing Repository
- Local files: `001-feature.md`, `002-bug.md`
- GitHub issues: Created as #47, #48 (existing issues #1-46)
- **Result**: State file tracks the mapping, time-based correlation finds PRs

### Scenario 3: [WIP] Pull Requests
- Copilot creates PR with title: `[WIP] Implementing feature for 001-setup`
- No direct issue number reference in PR
- **Result**: [WIP] marker + file number reference + timing correlation

### Scenario 4: Recovery from Interruption
- Bot was stopped and restarted
- Some files were processed manually
- **Result**: State sync detects existing issues and updates tracking

## Benefits

1. **Reliable Tracking**: Never loses track of which files have been processed
2. **Flexible PR Detection**: Multiple strategies ensure PRs are found even without perfect references
3. **Recovery Capability**: Can sync with existing GitHub state
4. **Repository Compatibility**: Works with repos that have existing issues/PRs
5. **Status Visibility**: Clear reporting of current processing status

## Technical Details

### PR Detection Algorithm

```python
def find_related_prs_for_issue(issue):
    # Get PRs created after the issue
    # For each PR from copilot-swe-agent:
    #   - Check direct issue references
    #   - Check for [WIP] markers
    #   - Check time-based correlation
    #   - Check file number references
    #   - Return matches sorted by creation time
```

### State Management

The state file is automatically created and maintained. It's safe to delete it if you want to start fresh - the bot will resync with GitHub on the next run.

### Error Handling

The bot gracefully handles:
- Missing or corrupted state files
- GitHub API errors during sync
- Edge cases in PR detection
- Time zone differences in timestamps

## Migration from Old Version

If you're upgrading from a previous version:

1. Run `python scripts/promote_next.py --status` to sync existing state
2. The bot will automatically detect and track any issues already created
3. Processing will continue from where it left off

No manual migration is required.
