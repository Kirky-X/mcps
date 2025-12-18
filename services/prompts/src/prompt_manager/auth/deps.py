import os
import uuid
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

from fastapi_users.db import SQLAlchemyUserDatabase

from .models import Base, User
from ..utils.config import load_config
from ..dal.database import Database


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    # Check if we're in test mode and use test database
    if os.environ.get("PROMPT_MANAGER_CONFIG_PATH"):
        # Test mode: use the test config
        from ..utils.config import load_config as load_test_config
        config = load_test_config()
        
        # Override database path if specified in environment
        if os.environ.get("PROMPT_MANAGER_DB_PATH"):
            config.database.path = os.environ["PROMPT_MANAGER_DB_PATH"]
            
        from ..dal.database import Database
        
        # Use singleton pattern to ensure we use the same engine instance
        engine_key = f"test_engine_{config.database.path}"
        if not hasattr(Database, engine_key):
            print(f"DEBUG: Creating new test engine for path: {config.database.path}")
            db = Database(config.database)
            setattr(Database, engine_key, db.engine)
        engine = getattr(Database, engine_key)
        print(f"DEBUG: Using test engine for path: {config.database.path}")
    else:
        # Normal mode: use default config
        config = load_config()
        db = Database(config.database)
        engine = db.engine
    
    if engine is None:
        # Supabase mode: use direct connection string for SQLAlchemy auth tables
        if not config.database.connection_string:
            raise RuntimeError("Auth requires SQLAlchemy engine or a connection_string in Supabase mode")
        # Create engine with connection string
        engine = create_async_engine(
            config.database.connection_string, 
            echo=False
        )
    
    # Set up event listener to configure search path for PostgreSQL
    if config.database.type in ["postgres", "supabase"]:
        @event.listens_for(engine.sync_engine, "connect")
        def set_search_path(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("SET search_path TO prompts, public")
            cursor.close()
    
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)) -> AsyncGenerator[SQLAlchemyUserDatabase[User, uuid.UUID], None]:
    yield SQLAlchemyUserDatabase(session, User)
