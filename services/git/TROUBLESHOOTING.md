# 故障排查

## 常见问题（≥10）

1. `ModuleNotFoundError: pygit2`
   - 解决：运行 `uv pip install pygit2` 或参考 INSTALL.md 安装 libgit2。
2. `ImportError: libgit2`
   - 解决：确认系统安装了 `libgit2` 并设置 `LD_LIBRARY_PATH` 指向其 `lib` 目录。
3. `Permission denied` 在安装或运行时
   - 解决：使用 `sudo` 执行系统包安装；确保对 `repo_path` 有读写权限。
4. `NOT_A_REPOSITORY` 错误
   - 解决：在目录内执行 `git init` 或确认路径指向已有仓库。
5. 拉取/推送网络错误（`NETWORK_ERROR`）
   - 解决：检查代理/网络连通；验证远程地址和凭据。
6. `AUTHENTICATION_FAILED`
   - 解决：配置凭据（如 SSH key 或 HTTPS token）；验证远程 URL 协议。
7. 合并冲突（`MERGE_CONFLICT`）
   - 解决：手动解决冲突后提交；必要时执行 `git merge --abort`。
8. `DETACHED_HEAD` 状态
   - 解决：创建分支并切换：`git checkout -b <branch>`。
9. `NOTHING_TO_COMMIT`
   - 解决：确保有变更被暂存或工作区存在修改；使用 `git_add`。
10. `INVALID_BRANCH`
    - 解决：确认分支存在；使用 `git_branch` 列出分支或先创建。
11. `git_stash_list` 为空但预期有项
    - 解决：确认存在 `refs/stash`；新仓库需先产生 stash；升级 pygit2。
12. 日志未写入文件
    - 解决：使用 `--log-file <path>` 启用文件日志，并检查路径可写。

## 诊断建议
- 启用 `--debug` 获取安装流程与性能耗时日志。
- 收集系统信息：OS 版本、Python 版本、`pygit2`/`libgit2` 版本。
- 使用 `git_health_check(repo_path)` 获取仓库统计与版本信息。

