from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.db.session import get_db
from app.core.redis_config import get_redis, Redis


DBDep = Annotated[AsyncSession,Depends(get_db)]
REDISDep = Annotated[Redis,Depends(get_redis)]