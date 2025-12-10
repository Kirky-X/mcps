import os
import uuid
from typing import Optional

from fastapi import Request
from fastapi_users import BaseUserManager, UUIDIDMixin

from .models import User


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = os.getenv("FASTAPI_USERS_RESET_SECRET", "CHANGE_ME_RESET_SECRET")
    verification_token_secret = os.getenv("FASTAPI_USERS_VERIFY_SECRET", "CHANGE_ME_VERIFY_SECRET")

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        pass

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        pass

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        pass
