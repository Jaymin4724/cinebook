from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from app.models import TheatreModel, LayoutModel, ShowModel


class ScreenModel(Base):
    __tablename__ = "screens"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    theatre_id: Mapped[UUID] = mapped_column(ForeignKey("theatres.id"), index=True)
    layout_id: Mapped[UUID] = mapped_column(ForeignKey("layouts.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    theatre: Mapped["TheatreModel"] = relationship(back_populates="screen_list")
    layout: Mapped["LayoutModel"] = relationship(back_populates="screen")
    show_list: Mapped[list["ShowModel"]] = relationship(back_populates="screen")

    async def soft_delete(self, db: AsyncSession):
        """Mark screen as deleted."""
        self.is_active = False
        db.add(self)
        return self
