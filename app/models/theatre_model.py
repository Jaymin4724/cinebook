from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from app.models import TheatreOperatorMapModel, ScreenModel, LayoutModel


class TheatreModel(Base):
    __tablename__ = "theatres"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    theatre_operator_list: Mapped["TheatreOperatorMapModel"] = relationship(
        back_populates="theatre"
    )
    screen_list: Mapped[list["ScreenModel"]] = relationship(back_populates="theatre")
    layout_list: Mapped[list["LayoutModel"]] = relationship(back_populates="theatre")

    async def soft_delete(self, db: AsyncSession):
        """Mark theatre as deleted."""
        self.is_active = False
        db.add(self)
        return self
