import uuid
from sqlalchemy.orm import declarative_base
from fastapi_users import schemas
from fastapi_users.db import SQLAlchemyBaseUserTableUUID


Base = declarative_base()


class User(SQLAlchemyBaseUserTableUUID, Base):
    pass


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
