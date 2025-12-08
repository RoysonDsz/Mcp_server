mcp = FastApiMCP(
    app,
    name="Room Booking API",
    description=(
        "Use these tools strictly for room operations:\n"
        "- Use get_all_rooms ONLY to fetch currently available rooms.\n"
        "- Use book_room ONLY when booking a room using its ID.\n"
        "Do not use different tools for similar purposes even if they exist.\n"
        "Always request room_id from user before booking.\n"
        "Return meaningful error if ID is invalid."
    ),
    include_operations=[
        "get_all_rooms",
        "book_room"
    ]
)
