def create_new_layout(
    new_layout, category_set, seat_mapping, rows, columns, total_seat
):
    """Build final seat layout structure with metadata."""
    return {
        "layout": new_layout,
        "category": sorted(list(category_set)),
        "seat_mapping": seat_mapping,
        "metadata": {
            "row": rows,
            "column": columns,
            "total_seats": total_seat,
        },
    }


def polish_seat_layout(data_input: dict) -> dict | None:
    """Validate and format raw seat layout data with unique seat numbering."""
    # Corrected: 'layout' is the list of rows, 'metadata' is a sibling key
    layout_grid = data_input.get("layout")
    metadata = data_input.get("metadata")

    if not metadata or not isinstance(layout_grid, list):
        return None

    rows = metadata.get("grid_rows")
    columns = metadata.get("grid_columns")

    if rows is None or columns is None:
        return None

    new_layout = []
    category_set = set()
    seat_mapping = {}
    total_seat = 0
    row_idx_counter = 0

    for i in range(rows):
        row_list = []
        column_seat_counter = 0
        row_has_seats = False

        # Generate Row Label (e.g., 0 -> A, 1 -> B)
        letter_idx = row_idx_counter % 26
        multiplier = (row_idx_counter // 26) + 1
        row_label = chr(65 + letter_idx) * multiplier

        for j in range(columns):
            # Safety check for index existence
            try:
                grid = layout_grid[i][j]
            except (IndexError, TypeError):
                row_list.append(None)
                continue

            if not grid:
                row_list.append(None)
                continue

            grid_type = grid.get("grid_type")
            category = grid.get("category")

            if grid_type == "seat":
                row_has_seats = True
                column_seat_counter += 1
                seat_number = f"{row_label}{column_seat_counter}"

                total_seat += 1
                seat_mapping[seat_number] = [i, j]

                cat_lower = category.lower() if category else "standard"
                category_set.add(cat_lower)

                row_list.append(
                    {
                        "grid_type": "seat",
                        "seat_number": seat_number,
                        "category": cat_lower,
                    }
                )
            else:
                row_list.append(
                    {"grid_type": grid_type, "seat_number": None, "category": None}
                )

        if row_has_seats:
            row_idx_counter += 1

        new_layout.append(row_list)

    return create_new_layout(
        new_layout=new_layout,
        category_set=category_set,
        seat_mapping=seat_mapping,
        rows=rows,
        columns=columns,
        total_seat=total_seat,
    )
