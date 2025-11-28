# API 参考文档

本模块通过 MCP 暴露以下工具。所有错误均返回结构化 JSON：
`{"success": false, "error": {"code", "message", "suggestion", "details"}}`

## 仓库状态与历史
- `git_status(repo_path: str) -> List[str]`
- `git_log(repo_path: str, max_count: int = 10, start_timestamp: Optional[str], end_timestamp: Optional[str]) -> List[Dict]`
- `git_log_recent(repo_path: str, period: str = "24h") -> List[Dict]`
- `git_show(repo_path: str, revision: str) -> Dict`
- `git_diff(repo_path: str, mode: Literal["unstaged","staged","all","commit"] = "all", target: Optional[str], context_lines: int = 3) -> str`

示例：
```python
git_status("/repo")
git_log("/repo", max_count=5)
git_log_recent("/repo", period="7d")
git_show("/repo", "HEAD")
git_diff("/repo", mode="all")
```

## 文件变更操作
- `git_add(repo_path: str, files: List[str]) -> List[str]`
- `git_reset(repo_path: str) -> str`
- `git_commit(repo_path: str, message: str) -> str`
- `git_restore(repo_path: str, files: List[str], staged: bool = False) -> str`

## 分支管理
- `git_branch(repo_path: str, branch_type: Literal["local","remote","all"] = "local", contains: Optional[str], not_contains: Optional[str]) -> List[str]`
- `git_create_branch(repo_path: str, branch_name: str, base_branch: Optional[str]) -> str`
- `git_checkout(repo_path: str, branch_name: str) -> str`

## 暂存区管理
- `git_stash(repo_path: str, message: Optional[str], include_untracked: bool = False) -> str`
- `git_stash_pop(repo_path: str, stash_id: Optional[str]) -> str`
- `git_stash_list(repo_path: str) -> List[str]`

## 远程仓库操作
- `git_remote(repo_path: str, action: Literal["list","add","remove"], name: Optional[str], url: Optional[str])`
- `git_pull(repo_path: str, remote: str = "origin", branch: Optional[str]) -> Dict`
- `git_push(repo_path: str, remote: str = "origin", branch: Optional[str], force: bool = False) -> Any`

## 高级操作
- `git_merge(repo_path: str, source_branch: str, strategy: Optional[str]) -> Dict`
- `git_cherry_pick(repo_path: str, commit_hash: str) -> str`

## 可观测性
- `git_health_check(repo_path: str) -> Dict`

返回示例（健康）：
```json
{
  "status": "healthy",
  "repo_path": "/repo",
  "head_reachable": true,
  "is_empty": false,
  "libgit2_version": "1.7.2",
  "pygit2_version": "1.13.0",
  "repo_stats": {"commits": 12, "branches": 3, "remotes": 1}
}
```

返回示例（错误）：
```json
{
  "success": false,
  "error": {
    "code": "GIT002",
    "message": "Not a git repository: /repo",
    "suggestion": "Run 'git init' or check the repo_path parameter",
    "details": {"os": "Linux", "pygit2_version": "1.13.0"}
  }
}
```
