# Launch Configuration Guide

This document explains how the VS Code launch configurations work in this project.

## Overview

The `.vscode/launch.json` file contains debug/run configurations that you can use from VS Code's Run and Debug panel (Ctrl+Shift+D).

## Environment Management

### .env File (Recommended for AshTrail)
For your AshTrail project, we've set up a `.env` file that contains your default configuration:
```bash
GITHUB_TOKEN=your_token_here
REPO_OWNER=SoupyOfficial
REPO_NAME=AshTrail
# ... other settings
```

Configurations with `"envFile": "${workspaceFolder}\\.env"` will automatically load these settings.

### Input Variables (For Custom/Other Projects)
The `inputs` section at the bottom of `launch.json` defines variables that can be used in configurations:

- `${input:githubToken}` - Prompts for GitHub token
- `${input:repoOwner}` - Prompts for repository owner
- `${input:repoName}` - Prompts for repository name
- etc.

## Configuration Types

### AshTrail Configurations (Use .env)
These configurations are pre-configured for your AshTrail project:
- **🧰 Test GitHub Connection (AshTrail)** - Tests connection using .env settings
- **🤖 Run GitHub Bot (Single - AshTrail)** - Runs bot once for AshTrail
- **🤖 Run GitHub Bot (Continuous - AshTrail)** - Runs bot continuously for AshTrail

### Custom Configurations (Use Input Prompts)
These configurations prompt you for values, useful for other projects:
- **🧰 Test GitHub Connection (Custom)** - Prompts for all settings
- **🤖 Run GitHub Bot (Single - Custom)** - Prompts for all settings
- **🤖 Run GitHub Bot (Continuous - Custom)** - Prompts for all settings

### Test Configurations
These use the .env file for consistency:
- **🧪 Run All Tests (Safe)** - Runs all tests
- **🔬 Run Unit Tests Only** - Runs unit tests only
- **🎭 Run Mock Integration Tests** - Runs mock integration tests

## Security

- Your `.env` file is ignored by git (see `.gitignore`)
- Use VS Code's `"password": true` input type for sensitive prompts
- The `.env` file keeps your tokens local and secure

## How Input Variables Work

When you run a configuration that uses `${input:variableName}`, VS Code:
1. Looks up the variable in the `inputs` section
2. Prompts you based on the input type:
   - `promptString` - Text input box
   - `pickString` - Dropdown selection
   - `password: true` - Hidden text input

### Input Types in This Project:

```jsonc
{
  "id": "githubToken",
  "type": "promptString",
  "password": true,  // Hides the input
  "description": "GitHub Personal Access Token"
}
```

```jsonc
{
  "id": "githubUrl",
  "type": "pickString",
  "options": [
    {"label": "GitHub.com", "value": "https://api.github.com"},
    {"label": "GitHub Enterprise", "value": "${input:customGithubUrl}"}
  ],
  "default": "https://api.github.com"
}
```

## Usage Recommendations

1. **For AshTrail development**: Use the configurations ending with "(AshTrail)"
2. **For other projects**: Use the configurations ending with "(Custom)"
3. **For testing**: All test configurations use your .env settings automatically

## Adding New Configurations

To add a new configuration:

1. **For AshTrail**: Add `"envFile": "${workspaceFolder}\\.env"`
2. **For custom projects**: Use `${input:...}` variables
3. **Add new input variables** to the `inputs` section if needed

Example:
```jsonc
{
  "name": "My New AshTrail Task",
  "type": "debugpy",
  "request": "launch",
  "program": "${workspaceFolder}\\scripts\\my_script.py",
  "envFile": "${workspaceFolder}\\.env"
}
```
