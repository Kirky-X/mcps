# MCP Git Module

A robust Model Context Protocol (MCP) server implementation for Git operations, built on top of `pygit2` (libgit2 bindings). This module provides AI agents with comprehensive capabilities to interact with Git repositories safely and efficiently.

## ✨ Features

*   **Standardized Interface**: Provides unified Git operation capabilities via the MCP protocol.
*   **Zero Dependency Hassle**: Intelligent `libgit2` installation strategy adapting to multiple platforms (Linux, macOS, Windows).
*   **Production-Grade Quality**: Comprehensive error handling, logging, and observability.

## 🛠️ Available Tools

The module exposes the following tools to MCP clients, strictly adhering to the PRD specifications:

### 1. Repository Status & History
*   `git_status(repo_path)`: Check workspace status.
*   `git_log(repo_path, max_count=10, start_timestamp=None, end_timestamp=None)`: View commit history.
*   `git_log_recent(repo_path, period="24h")`: View recent commits (shortcut).
*   `git_show(repo_path, revision)`: View commit details.

### 2. File Operations
*   `git_diff(repo_path, mode="all", target=None, context_lines=3)`: View differences.
*   `git_add(repo_path, files)`: Stage files.
*   `git_reset(repo_path)`: Unstage files (reset staging area).
*   `git_commit(repo_path, message)`: Commit changes.
*   `git_restore(repo_path, files, staged=False)`: Restore files to specific state.

### 3. Branch Management
*   `git_branch(repo_path, branch_type="local", contains=None, not_contains=None)`: List branches.
*   `git_create_branch(repo_path, branch_name, base_branch=None)`: Create a branch.
*   `git_checkout(repo_path, branch_name)`: Switch branches.

### 4. Stash Management
*   `git_stash(repo_path, message=None, include_untracked=False)`: Stash current changes.
*   `git_stash_pop(repo_path, stash_id=None)`: Restore stashed changes.
*   `git_stash_list(repo_path)`: List all stashes.

### 5. Remote Operations
*   `git_remote(repo_path, action, name=None, url=None)`: Manage remote repositories.
*   `git_pull(repo_path, remote="origin", branch=None)`: Pull updates.
*   `git_push(repo_path, remote="origin", branch=None, force=False)`: Push to remote.

### 6. Advanced Operations
*   `git_merge(repo_path, source_branch, strategy=None)`: Merge branches.
*   `git_cherry_pick(repo_path, commit_hash)`: Cherry-pick commits.

### 7. Observability
*   `git_health_check(repo_path)`: Verify repository health and system info.

## 🚀 Installation

This project uses `uv` for dependency management.

```bash
# Install directly from source
uv pip install .
```

### System Requirements
*   Python 3.10+
*   Supported OS: Ubuntu 20.04+, macOS 11+, Windows 10+
*   Git 2.20+

### Libgit2 Installation Strategy (Fallback Chain)
The module attempts to install `libgit2` in the following order:
1.  **UV Automatic Installation**: `uv pip install pygit2`
2.  **System Package Manager**: `apt-get`, `dnf`, `brew`, or `vcpkg`
3.  **Source Compilation**: Build from source using `cmake`

## ⚙️ Configuration

### MCP Client Config
Add the following to your MCP client configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-git": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "git+https://github.com/Kirky-X/mcps.git#subdirectory=services/git",
        "mcp-git"
      ]
    }
  }
}
```

### Runtime Arguments
The server accepts the following command-line arguments:

*   `--debug`: Enable debug logging (shows libgit2 installation process, Git command details, performance stats).
*   `--skip-libgit2-install`: Skip dependency installation (for advanced users).
*   `--log-file <path>`: Specify log output file.

Example usage:
```bash
uv run mcp-git --debug
uv run mcp-git --skip-libgit2-install
uv run mcp-git --log-file /var/log/mcp-git.log
```

Logging behavior:
- By default, logs go to stdout at INFO level; `--debug` enables verbose timing and installer details.
- When `--log-file` is provided, logs also write to the specified file using format: `timestamp level logger: message`.

## ⚠️ Error Handling

The module uses standardized error codes:

*   `GIT001`: **REPO_NOT_FOUND** - Repository path does not exist
*   `GIT002`: **NOT_A_REPOSITORY** - Path is not a Git repository
*   `GIT003`: **LIBGIT2_MISSING** - libgit2 not installed
*   `GIT004`: **PERMISSION_DENIED** - Insufficient permissions
*   `GIT005`: **MERGE_CONFLICT** - Merge conflict detected
*   `GIT006`: **INVALID_BRANCH** - Branch does not exist
*   `GIT007`: **DETACHED_HEAD** - HEAD is in detached state
*   `GIT008`: **NOTHING_TO_COMMIT** - No content to commit
*   `GIT009`: **NETWORK_ERROR** - Network error (pull/push failed)
*   `GIT010`: **AUTHENTICATION_FAILED** - Authentication failed

Errors are returned in a structured JSON format:
```json
{
  "success": false,
  "error": {
    "code": "GIT002",
    "message": "Not a git repository: /home/user/project",
    "suggestion": "Run 'git init' in this directory or verify the repo_path parameter",
    "details": { ... }
  }
}
```

## 🧑‍💻 Development

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd services/git

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest tests

# Run unit tests only
pytest tests/unit

# Run integration tests
pytest tests/integration
```

## 🔍 Troubleshooting

**`ImportError: libgit2` or `ModuleNotFoundError`**
Ensure `pygit2` is correctly installed. The module tries to handle this, but on some systems, you might need to install `libgit2` manually:
*   Ubuntu: `sudo apt-get install libgit2-dev`
*   macOS: `brew install libgit2`

**Permission Errors**
Ensure the agent has read/write permissions for the `repo_path` provided in tool calls.
