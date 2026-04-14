def polish_seat_layout(layout: dict) -> dict | None:
    """Validate and format raw seat layout data."""
    metadata = layout.get("metadata")
    layout = layout.get("layout")

    if not metadata or not layout:
        return None

    rows = metadata.get("grid_rows")
    columns = metadata.get("grid_columns")

    if not rows or not columns:
        return None

    new_layout = []
    category_set = set()
    seat_mapping = {}
    total_seat = 0
    row_number = 0

    for i in range(0, rows, 1):

        row_list = []
        column_number = 0

        letter_number = row_number % 26
        multiplier = (row_number // 26) + 1
        base_char_asci = 65

        seat_row = chr(base_char_asci + letter_number) * multiplier

        for j in range(0, columns, 1):

            grid = layout[i][j]

            if not grid:
                return None

            grid_type = grid.get("grid_type")
            category = grid.get("category")

            if grid_type not in ("seat", "wall"):
                return None

            if grid_type == "seat":
                seat_number = seat_row + str(column_number + 1)
                column_number += 1

                total_seat += 1
                seat_mapping[seat_number] = [i, j]
                row_list.append(
                    {
                        "grid_type": grid_type,
                        "seat_number": seat_number,
                        "category": category.lower(),
                    }
                )

                if category is not None:
                    if category.lower() not in category_set:
                        category_set.add(category)
                else:
                    return None

            else:
                row_list.append(
                    {"grid_type": grid_type, "seat_number": None, "category": None}
                )

        if column_number > 1:
            row_number += 1

        new_layout.append(row_list)

    return create_new_layout(
        new_layout=new_layout,
        category_set=category_set,
        seat_mapping=seat_mapping,
        rows=rows,
        columns=columns,
        total_seat=total_seat,
    )


def create_new_layout(
    new_layout: list,
    category_set: set,
    seat_mapping: dict,
    rows: int,
    columns: int,
    total_seat: int,
):
    """Build final seat layout structure with metadata."""
    new_seat_layout = {}

    new_seat_layout["layout"] = new_layout
    new_seat_layout["category"] = list(category_set)
    new_seat_layout["seat_mapping"] = seat_mapping
    new_seat_layout["metadata"] = {
        "row": rows,
        "column": columns,
        "total_seats": total_seat,
    }

    return new_seat_layout
