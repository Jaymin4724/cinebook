from app.core.redis_config import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status

from sqlalchemy import select

from app.models import ShowModel, LayoutModel, ScreenModel, BookedSeatMapModel


class RedisSeatLayoutManagement:

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        show_id: str
    ):
        self.db = db
        self.redis = redis
        self.show_id = show_id

    async def generate_show_layout(
        self
    ):

        if not self.redis.get(name=f"show_seat_layout_{self.show_id}") or not self.redis.get(name=f"show_seat_locked_{self.show_id}"):
            self.redis.delete(name=f"show_seat_layout_{self.show_id}")
            self.redis.delete(name=f"show_seat_locked_{self.show_id}")
            return await self.generate_show_layout_from_base()
        return await self.generate_from_existing_layout()


    async def generate_from_existing_layout(
        self
    ):
        
        layout_body = self.redis.get(name=f"show_seat_layout_{self.show_id}")
        locked_seats = self.redis.get(name=f"show_seat_locked_{self.show_id}")

        for seat in locked_seats:
            seat_grid = layout_body["seat_mapping"][seat]

            if layout_body["layout"][seat_grid[0]][seat_grid[1]]["status"] != "Booked":
                layout_body["layout"][seat_grid[0]][seat_grid[1]]["status"] = "Locked"

        return layout_body


    async def generate_show_layout_from_base(
        self
    ):
        
        screen_layout_body = await self.get_screen_layout(
            show_id=self.show_id
        )

        price_dict = await self.get_price_dict(
            show_id=self.show_id
        )

        base_layout = await self.generate_base_layout(
            screen_layout_body=screen_layout_body,
            price_dict=price_dict
        )

        booked_seats_list =  await self.get_booked_seats(
            show_id=self.show_id
        )

        updated_layout = await self.update_booked_seats(
            base_layout=base_layout,
            booked_seats_list=booked_seats_list
        )
        
        with self.redis.pipeline() as pipe:

            pipe.json().set(name=f"show_seat_layout_{self.show_id}",path="$",obj=updated_layout)
            pipe.expire(name=f"show_seat_layout_{self.show_id}",time=600)
            pipe.redis.hset(name=f"show_seat_locked_{self.show_id}",mapping={})
            pipe.expire(name=f"show_seat_locked_{self.show_id}",time=600)

            pipe.execute()

        return updated_layout


    async def update_booked_seats(
        self,
        base_layout: dict,
        booked_seats_list: dict,
    ):
        
        for seats in booked_seats_list:
            seat_grid = base_layout.get("seat_mapping").get(seats)

            base_layout["layout"][seat_grid[0]][seat_grid[1]]["status"] = "Booked"

            total_booked_seats = base_layout.metadata.set_default("booked_seats",0)
            base_layout["metadata"]["booked_seats"] = total_booked_seats + 1

        return base_layout

    
    async def generate_base_layout(
        self,
        screen_layout_body: dict,
        price_dict: dict
    ):
        
        new_layout = screen_layout_body.get("layout")

        if not new_layout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Layout not found"
            )
        
        seat_mapping = screen_layout_body.get("seat_mapping")

        if not seat_mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seat mapping not found"
            )
        
        if not price_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price not found"
            )
        
        metadata = screen_layout_body.get("metadata")

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Metadata not found"
            )
        
        rows = metadata.get("row")
        columns = metadata.get("columm")
        
        if not rows or not columns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rows or Columns not found"
            )
        
        for row in range(0,rows,1):
            for column in range(0,columns,1):

                if new_layout[row][column].get("grid_type") == "seat":

                    seat_category = new_layout[row][column].get("category")

                    price = price_dict.get(seat_category)

                    if price:

                        new_layout[row][column]["price"] = price
                        new_layout[row][column]["status"] = "Available"

        updated_layout = {
            "layout":new_layout,
            "metadata": metadata,
            "category_pricing": price_dict,
            "seat_mapping": seat_mapping
        }

        return updated_layout


    async def get_screen_layout(
        self,
        show_id: str
    ):

        query = select(
            LayoutModel
        ).join(
            ScreenModel, ScreenModel.layout_id == LayoutModel.id
        ).join(
            ShowModel, ShowModel.screen_id == ScreenModel.id
        ).where(
            ShowModel.id == show_id
        )

        result = await self.db.execute(query)

        layout_found = result.scalar_one_or_none()

        if not layout_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Show not found"
            )
        
        layout_body = layout_found.layout

        if not layout_body:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Layout not found"
            )
        
        return layout_body
    
    async def get_price_dict(
        self,
        show_id: str
    ):
        query = select(
            ShowModel
        ).where(
            ShowModel.id == show_id
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()
        
    
    async def get_booked_seats(
        self,
        show_id: str
    ):
        
        query = select(
            BookedSeatMapModel.seats_number
        ).where(
            BookedSeatMapModel.show_id == show_id
        )

        result = await self.db.execute(query)

        return result.scalars()