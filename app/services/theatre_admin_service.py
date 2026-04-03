from sqlalchemy.ext.asyncio import AsyncSession


class TheatreAdminService:
    
    def __init__(
        self, 
        db: AsyncSession
    ):
        self.db = db