from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional,Any,Dict


if TYPE_CHECKING:
    from app.models import TheatreModel,ScreenModel


class LayoutModel(Base):
    __tablename__ = "layouts"

    name : Mapped[str] = mapped_column(String(100), nullable=False)
    layout : Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    theatre_id : Mapped[UUID] = mapped_column(ForeignKey("theatres.id"), index=True)

    theatre : Mapped["TheatreModel"] = relationship(back_populates="layout_list")
    screen : Mapped["ScreenModel"] = relationship(back_populates="layout")