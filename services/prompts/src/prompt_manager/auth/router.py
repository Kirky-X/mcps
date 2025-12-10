import os
import uuid

from fastapi import APIRouter, Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from .models import User, UserRead, UserCreate, UserUpdate
from .manager import UserManager
from .deps import get_user_db, get_async_session


SECRET = os.getenv("FASTAPI_USERS_JWT_SECRET", "CHANGE_ME_JWT_SECRET")


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


async def get_user_manager(user_db = Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])


router = APIRouter(prefix="/auth")


router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["auth"]
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    tags=["auth"]
)

router.include_router(
    fastapi_users.get_reset_password_router(),
    tags=["auth"]
)

router.include_router(
    fastapi_users.get_verify_router(UserRead),
    tags=["auth"]
)


current_active_user = fastapi_users.current_user(active=True)
