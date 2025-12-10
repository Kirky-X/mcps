import uuid
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from fastapi_users.db import SQLAlchemyUserDatabase

from .models import Base, User
from ..utils.config import load_config
from ..dal.database import Database


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    config = load_config()
    db = Database(config.database)
    engine = db.engine
    if engine is None:
        # Supabase mode: use direct connection string for SQLAlchemy auth tables
        if not config.database.connection_string:
            raise RuntimeError("Auth requires SQLAlchemy engine or a connection_string in Supabase mode")
        engine = create_async_engine(config.database.connection_string, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)) -> AsyncGenerator[SQLAlchemyUserDatabase[User, uuid.UUID], None]:
    yield SQLAlchemyUserDatabase(session, User)
