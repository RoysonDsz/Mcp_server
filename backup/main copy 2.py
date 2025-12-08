from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from fastapi_mcp import FastApiMCP

app = FastAPI()

# -------------------------------
# Room Model
# -------------------------------
class Room(BaseModel):
    id: int
    name: str
    capacity: int
    floor: Optional[int] = None


rooms_db: List[Room] = [
    Room(id=1, name="Conference Room A", capacity=10, floor=1),
    Room(id=2, name="Conference Room B", capacity=8, floor=1),
]


# -------------------------------
# Create Room
# -------------------------------
@app.post("/rooms", response_model=Room, operation_id="create_rooms")
def create_room(room: Room):
    """Create a new room"""
    # Check if room already exists
    for r in rooms_db:
        if r.id == room.id:
            raise HTTPException(status_code=400, detail="Room ID already exists.")
    
    rooms_db.append(room)
    return room


# -------------------------------
# Get All Rooms
# -------------------------------
@app.get("/rooms", response_model=List[Room], operation_id="get_all_rooms")
def get_all_rooms():
    """Get all rooms"""
    return rooms_db


# -------------------------------
# Get Room by ID
# -------------------------------
@app.get("/rooms/{room_id}", response_model=Room, operation_id="get_room_by_id")
def get_room(room_id: int):
    """Get a specific room by ID"""
    for room in rooms_db:
        if room.id == room_id:
            return room

    raise HTTPException(status_code=404, detail="Room not found")

# Initialize FastApiMCP with base_url
mcp = FastApiMCP(
    app,
    name="Room Management API",
    description="MCP server for Room Management",
    include_operations=["get_room_by_id","get_all_rooms","create_rooms"]
    
)

mcp.mount()

def main():
    import uvicorn
    uvicorn.run(
        "main:app",    
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()