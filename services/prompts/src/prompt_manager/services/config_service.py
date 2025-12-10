from typing import Optional
import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..dal.database import Database
from ..dal.supabase.service import SupabaseService as DomainSupabaseService
from ..models.orm import AppConfig


class ConfigService:
    def __init__(self, db: Database, supabase: Optional[DomainSupabaseService] = None):
        self.db = db
        self.supabase = supabase

    async def get(self, key: str) -> Optional[str]:
        if self.db.config.type == "supabase" and self.supabase:
            items = await self.supabase.get_app_config(key)
            return items[0]["value"] if items else None

        async with self.db.get_session() as session:
            stmt = select(AppConfig).where(AppConfig.key == key)
            obj = (await session.execute(stmt)).scalar_one_or_none()
            return obj.value if obj else None

    async def set(self, key: str, value: str) -> bool:
        if self.db.config.type == "supabase" and self.supabase:
            await self.supabase.set_app_config(key, value)
            return True

        async with self.db.get_session() as session:
            async with session.begin():
                stmt = select(AppConfig).where(AppConfig.key == key)
                obj = (await session.execute(stmt)).scalar_one_or_none()
                if obj:
                    obj.value = value
                else:
                    session.add(AppConfig(key=key, value=value))
            return True

    # Convenience accessors for specific keys should be defined by API layer if documented.
