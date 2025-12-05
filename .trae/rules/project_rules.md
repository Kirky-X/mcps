---
alwaysApply: true
---

1. Use Python 3.12 as the main Python version for the project.

2. Use `uv` as the package management tool for the project.

3. All dependencies are declared in `pyproject.toml`.

4. Develop strictly according to the requirements in the `documents/prd.md`. After completing each task, it is necessary to conduct a check to ensure that there is no excessive development and that the implementation is fully in accordance with the document requirements definition.

5. Develop strictly according to the tasks in the document `docs/task.md`. After completing a task, it is necessary to mark it.

6. Each task requires a corresponding test case, which should be located in the `tests/` directory.

7. Strictly adhere to the principle of test driven development, and write test cases for each functional module before implementing the functionality.

8. For each library, it is necessary to use the `context7` MCP tool to query the latest version of the library before use, ensuring the use of the latest features and bug fixes.

9. For each development task, `sequential thinking` should be used to ensure the completion and quality of the task.

10. Before each commit, it is necessary to run the test suite to ensure that all tests pass.

11. Clear warnings in a timely manner, and resolve them before committing.

12. The environment required for deploying tests using Docker, such as the database PostgreSQL.

13. Strictly use `mcp-git` for Git operations.

# 项目规则补充：Git Push 凭据设置
- 指定密钥路径：`export SSH_KEY_PATH=~/.ssh/id_ed25519`
- 若使用 HTTPS 远程，请确保凭据助手已配置：`git config --global credential.helper store`
