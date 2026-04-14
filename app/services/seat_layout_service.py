from app.core.redis_config import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select
from app.models import ShowModel, LayoutModel, ScreenModel, BookedSeatMapModel


class SeatLayoutService:
    """Handle seat layout generation and updates for shows."""

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def generate_show_layout(self, show_id: str) -> dict:
        """Generate or fetch seat layout for a show."""
        layout_exists = await self.redis.json().get(name=f"show_seat_layout_{show_id}")
        if not layout_exists:
            await self.redis.delete(f"show_seat_layout_{show_id}")
            await self.redis.delete(f"show_seat_locked_{show_id}")
            return await self.generate_show_layout_from_base(show_id)
        return await self.generate_from_existing_layout(show_id)

    async def generate_from_existing_layout(self, show_id: str) -> dict:
        """Update existing layout with locked seats."""
        layout_body = await self._get_redis_json(f"show_seat_layout_{show_id}")
        locked_seats = await self.redis.hgetall(f"show_seat_locked_{show_id}")

        if not locked_seats:
            return layout_body

        for seat in locked_seats:
            seat_grid = layout_body["seat_mapping"].get(seat)
            if seat_grid:
                row_idx, col_idx = seat_grid
                seat_status = layout_body["layout"][row_idx][col_idx]["status"]
                if seat_status != "Booked":
                    layout_body["layout"][row_idx][col_idx]["status"] = "Locked"

        return layout_body

    async def generate_show_layout_from_base(self, show_id: str) -> dict:
        """Generate seat layout from base data and store in Redis."""
        screen_layout_body = await self.get_screen_layout(show_id=show_id)
        price_dict = await self.get_price_dict(show_id=show_id)

        base_layout = await self.generate_base_layout(screen_layout_body, price_dict)
        booked_seats_list = await self.get_booked_seats(show_id=show_id)
        updated_layout = await self.update_booked_seats(base_layout, booked_seats_list)

        async with self.redis.pipeline() as pipe:
            pipe.json().set(
                name=f"show_seat_layout_{show_id}", path="$", obj=updated_layout
            )
            pipe.expire(name=f"show_seat_layout_{show_id}", time=6000)
            await pipe.execute()

        return updated_layout

    async def update_booked_seats(
        self, base_layout: dict, booked_seats_list: list
    ) -> dict:
        """Mark booked seats in layout."""
        layout = base_layout.copy()
        seat_mapping = layout.get("seat_mapping", {})
        total_booked = 0

        for seat in booked_seats_list:
            seat_grid = seat_mapping.get(seat)
            if seat_grid:
                row_idx, col_idx = seat_grid
                seat_info = layout["layout"][row_idx][col_idx]
                if seat_info["status"] != "Booked":
                    seat_info["status"] = "Booked"
                    total_booked += 1

        layout["metadata"]["booked_seats"] = total_booked
        return layout

    async def generate_base_layout(
        self, screen_layout_body: dict, price_dict: dict
    ) -> dict:
        """Build base layout with pricing and availability."""
        layout = screen_layout_body.get("layout")
        seat_mapping = screen_layout_body.get("seat_mapping")
        metadata = screen_layout_body.get("metadata")

        self._validate_presence(layout, "Layout")
        self._validate_presence(seat_mapping, "Seat mapping")
        self._validate_presence(price_dict, "Price")
        self._validate_presence(metadata, "Metadata")

        rows = metadata.get("row")
        columns = metadata.get("column")
        if rows is None or columns is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rows or Columns not found",
            )

        for row in range(rows):
            for col in range(columns):
                cell = layout[row][col]
                if cell.get("grid_type") == "seat":
                    category = cell.get("category")
                    price = price_dict.get(category)
                    if price is not None:
                        cell["price"] = price
                        cell["status"] = "Available"

        return {
            "layout": layout,
            "metadata": metadata,
            "category_pricing": price_dict,
            "seat_mapping": seat_mapping,
        }

    async def get_screen_layout(self, show_id: str) -> dict:
        """Fetch screen layout for a show."""
        query = (
            select(LayoutModel)
            .join(ScreenModel, ScreenModel.layout_id == LayoutModel.id)
            .join(ShowModel, ShowModel.screen_id == ScreenModel.id)
            .where(ShowModel.id == show_id)
        )
        result = await self.db.execute(query)
        layout_obj = result.scalar_one_or_none()
        if not layout_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Show not found"
            )
        layout_body = layout_obj.layout
        if not layout_body:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found"
            )
        return layout_body

    async def get_price_dict(self, show_id: str) -> dict:
        """Fetch pricing details for a show."""
        query = select(ShowModel).where(ShowModel.id == show_id)
        result = await self.db.execute(query)
        show_obj = result.scalar_one_or_none()
        if not show_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Price category not found"
            )
        return show_obj.category_pricing

    async def get_booked_seats(self, show_id: str) -> list:
        """Fetch booked seats for a show."""
        query = select(BookedSeatMapModel.seats_number).where(
            BookedSeatMapModel.show_id == show_id
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_redis_json(self, key: str) -> dict:
        """Fetch JSON data from Redis."""
        data = await self.redis.json().get(name=key)
        if data is None:
            return {}
        return data

    def _validate_presence(self, value, name: str):
        """Validate required data presence."""
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found"
            )
