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
    # Handle the nested structure (input['layout']['layout'])
    outer_layout = data_input.get("layout", {})
    metadata = outer_layout.get("metadata")
    layout_grid = outer_layout.get("layout")

    if not metadata or not layout_grid:
        return None

    rows = metadata.get("grid_rows")
    columns = metadata.get("grid_columns")

    if rows is None or columns is None:
        return None

    new_layout = []
    category_set = set()
    seat_mapping = {}
    total_seat = 0
    row_idx_counter = 0  # Counter for theater row labels (A, B, C...)

    for i in range(rows):
        row_list = []
        column_seat_counter = 0
        row_has_seats = False

        # Generate Row Label (e.g., 0 -> A, 1 -> B, 26 -> AA)
        letter_idx = row_idx_counter % 26
        multiplier = (row_idx_counter // 26) + 1
        row_label = chr(65 + letter_idx) * multiplier

        for j in range(columns):
            grid = layout_grid[i][j]
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
                # Map coordinates [row_index, col_index] to unique seat label
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
                # Handle walls or non-seat grid types
                row_list.append(
                    {"grid_type": grid_type, "seat_number": None, "category": None}
                )

        # Only increment the letter counter if this row actually contained seats
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
