import datetime
from typing import Dict, Any, List

from sqlmodel import select

from ..dal.database import Database
from ..models.orm import Prompt, AppConfig
from ..services.config_service import ConfigService
from ..dal.supabase.service import SupabaseService as DomainSupabaseService
from ..infrastructure.time_network import get_precise_time


class SyncEngine:
    def __init__(self, db: Database, supabase: DomainSupabaseService, config: ConfigService):
        self.db = db
        self.supabase = supabase
        self.config = config

    async def sync(self) -> Dict[str, int]:
        last_sync_str = await self.config.get("last_sync_time")
        if not last_sync_str:
            last_sync_str = "1970-01-01T00:00:00+00:00"
        try:
            last_sync = datetime.datetime.fromisoformat(last_sync_str.replace("Z", "+00:00"))
        except Exception:
            last_sync = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

        pull_count = 0
        insert_local = 0
        update_local = 0
        push_count = 0

        remote_builder = self.supabase.client.table("prompts").select("*").gt("updated_at", last_sync_str)
        remote_resp = await remote_builder.execute()
        remote_rows: List[Dict[str, Any]] = remote_resp.data or []

        async with self.db.get_session() as session:
            async with session.begin():
                for r in remote_rows:
                    pull_count += 1
                    rid = r.get("id")
                    obj: Prompt | None = await session.get(Prompt, rid) if rid else None
                    ru = r.get("updated_at")
                    try:
                        r_updated = datetime.datetime.fromisoformat(str(ru).replace("Z", "+00:00")) if ru else last_sync
                    except Exception:
                        r_updated = last_sync
                    if not obj:
                        created = r.get("created_at")
                        try:
                            cdt = datetime.datetime.fromisoformat(str(created).replace("Z", "+00:00")) if created else get_precise_time()
                        except Exception:
                            cdt = get_precise_time()
                        if isinstance(cdt, datetime.datetime) and cdt.tzinfo is None:
                            cdt = cdt.replace(tzinfo=datetime.timezone.utc)
                        obj = Prompt(
                            id=r.get("id"),
                            name=r.get("name"),
                            content=r.get("content"),
                            created_at=cdt,
                            updated_at=r_updated,
                            is_deleted=bool(r.get("is_deleted", False)),
                            sync_hash=r.get("sync_hash")
                        )
                        session.add(obj)
                        insert_local += 1
                    else:
                        lu = obj.updated_at or last_sync
                        if isinstance(lu, datetime.datetime) and lu.tzinfo is None:
                            lu = lu.replace(tzinfo=datetime.timezone.utc)
                        if isinstance(lu, str):
                            try:
                                lu = datetime.datetime.fromisoformat(lu.replace("Z", "+00:00"))
                            except Exception:
                                lu = last_sync
                        if r_updated > lu:
                            obj.name = r.get("name", obj.name)
                            obj.content = r.get("content")
                            obj.is_deleted = bool(r.get("is_deleted", False))
                            obj.sync_hash = r.get("sync_hash")
                            obj.updated_at = r_updated
                            update_local += 1

        async with self.db.get_session() as session:
            stmt = select(Prompt).where(Prompt.updated_at > last_sync)
            locals_to_push = (await session.execute(stmt)).scalars().all()
            payload = []
            for p in locals_to_push:
                cdt = p.created_at if isinstance(p.created_at, datetime.datetime) else None
                udt = p.updated_at if isinstance(p.updated_at, datetime.datetime) else None
                if isinstance(cdt, datetime.datetime) and cdt.tzinfo is None:
                    cdt = cdt.replace(tzinfo=datetime.timezone.utc)
                if isinstance(udt, datetime.datetime) and udt.tzinfo is None:
                    udt = udt.replace(tzinfo=datetime.timezone.utc)
                payload.append({
                    "id": p.id,
                    "name": p.name,
                    "content": p.content,
                    "created_at": (cdt.isoformat() if cdt else str(p.created_at)),
                    "updated_at": (udt.isoformat() if udt else str(p.updated_at)),
                    "is_deleted": p.is_deleted,
                    "sync_hash": p.sync_hash
                })
            if payload:
                await self.supabase.client.table("prompts").upsert(payload).execute()
                push_count = len(payload)

        now = get_precise_time().isoformat()
        await self.config.set("last_sync_time", now)

        return {
            "pulled": pull_count,
            "inserted_local": insert_local,
            "updated_local": update_local,
            "pushed": push_count,
        }
