from enum import Enum
from typing import Any, Dict, Optional

class GitErrorCode(Enum):
    REPO_NOT_FOUND = "GIT001"
    NOT_A_REPOSITORY = "GIT002"
    LIBGIT2_MISSING = "GIT003"
    PERMISSION_DENIED = "GIT004"
    MERGE_CONFLICT = "GIT005"
    INVALID_BRANCH = "GIT006"
    DETACHED_HEAD = "GIT007"
    NOTHING_TO_COMMIT = "GIT008"
    NETWORK_ERROR = "GIT009"
    AUTHENTICATION_FAILED = "GIT010"
    INVALID_PARAMETER = "GIT011"
    OPERATION_FAILED = "GIT012"

class GitError(Exception):
    def __init__(
        self, 
        code: GitErrorCode, 
        message: str, 
        suggestion: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "suggestion": self.suggestion,
                "details": self.details
            }
        }
