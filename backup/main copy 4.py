from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from fastapi_mcp import FastApiMCP
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

app = FastAPI()

# -------------------------------
# MongoDB Atlas Configuration
# -------------------------------
# Get MongoDB URI from environment
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "room_management")
COLLECTION_NAME = "rooms"

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")

# MongoDB Atlas client with server API version
client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi('1'))
db = client[DATABASE_NAME]
rooms_collection = db[COLLECTION_NAME]

# -------------------------------
# Room Model
# -------------------------------
class Room(BaseModel):
    id: int
    name: str
    capacity: int
    floor: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Conference Room A",
                "capacity": 10,
                "floor": 1
            }
        }


# -------------------------------
# Startup Event - Test Connection & Seed Database
# -------------------------------
@app.on_event("startup")
async def startup_db():
    """Test MongoDB Atlas connection and initialize database"""
    try:
        # Test the connection
        await client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        print(f"📊 Database: {DATABASE_NAME}")
        
        # Create index on id field for faster queries
        await rooms_collection.create_index("id", unique=True)
        
        # Check if collection needs seeding
        count = await rooms_collection.count_documents({})
        
        if count == 0:
            initial_rooms = [
                {"id": 1, "name": "Conference Room A", "capacity": 10, "floor": 1},
                {"id": 2, "name": "Conference Room B", "capacity": 8, "floor": 1},
                {"id": 3, "name": "Board Room", "capacity": 20, "floor": 2},
                {"id": 4, "name": "Training Room", "capacity": 30, "floor": 2},
                {"id": 5, "name": "Meeting Room 1", "capacity": 6, "floor": 3},
                {"id": 6, "name": "Meeting Room 2", "capacity": 6, "floor": 3},
                {"id": 7, "name": "Executive Suite", "capacity": 15, "floor": 4},
                {"id": 8, "name": "Collaboration Space", "capacity": 12, "floor": 1},
            ]
            await rooms_collection.insert_many(initial_rooms)
            print(f"✅ Initialized database with {len(initial_rooms)} rooms")
        else:
            print(f"📊 Database already has {count} rooms")
            
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB Atlas: {e}")
        print("💡 Please check your MONGO_URI in the .env file")
        raise


# -------------------------------
# Shutdown Event
# -------------------------------
@app.on_event("shutdown")
async def shutdown_db():
    """Close MongoDB connection"""
    client.close()
    print("🔌 Closed MongoDB Atlas connection")


# -------------------------------
# Health Check
# -------------------------------
@app.get("/health")
async def health_check():
    """Check if the API and database are healthy"""
    try:
        await client.admin.command('ping')
        room_count = await rooms_collection.count_documents({})
        return {
            "status": "healthy",
            "database": "connected",
            "database_name": DATABASE_NAME,
            "total_rooms": room_count,
            "message": "API is running and MongoDB Atlas is connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )


# -------------------------------
# Create Room
# -------------------------------
@app.post("/rooms", response_model=Room, operation_id="create_rooms", status_code=201)
async def create_room(room: Room):
    """Create a new room"""
    try:
        # Check if room ID already exists
        existing_room = await rooms_collection.find_one({"id": room.id})
        if existing_room:
            raise HTTPException(status_code=400, detail=f"Room with ID {room.id} already exists.")
        
        # Insert the room
        room_dict = room.model_dump()
        result = await rooms_collection.insert_one(room_dict)
        
        if result.inserted_id:
            return room
        else:
            raise HTTPException(status_code=500, detail="Failed to create room")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# -------------------------------
# Get All Rooms
# -------------------------------
@app.get("/rooms", response_model=List[Room], operation_id="get_all_rooms")
async def get_all_rooms(
    floor: Optional[int] = None,
    min_capacity: Optional[int] = None,
    max_capacity: Optional[int] = None
):
    """Get all rooms with optional filtering"""
    try:
        query = {}
        
        # Add filters if provided
        if floor is not None:
            query["floor"] = floor
        
        if min_capacity is not None or max_capacity is not None:
            query["capacity"] = {}
            if min_capacity is not None:
                query["capacity"]["$gte"] = min_capacity
            if max_capacity is not None:
                query["capacity"]["$lte"] = max_capacity
        
        rooms = []
        cursor = rooms_collection.find(query).sort("id", 1)
        
        async for room in cursor:
            # Remove MongoDB's _id field
            room.pop("_id", None)
            rooms.append(Room(**room))
        
        return rooms
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# -------------------------------
# Get Room by ID
# -------------------------------
@app.get("/rooms/{room_id}", response_model=Room, operation_id="get_room_by_id")
async def get_room(room_id: int):
    """Get a specific room by ID"""
    try:
        room = await rooms_collection.find_one({"id": room_id})
        
        if not room:
            raise HTTPException(status_code=404, detail=f"Room with ID {room_id} not found")
        
        # Remove MongoDB's _id field
        room.pop("_id", None)
        return Room(**room)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# -------------------------------
# Update Room
# -------------------------------
@app.put("/rooms/{room_id}", response_model=Room, operation_id="update_room")
async def update_room(room_id: int, room: Room):
    """Update a room by ID"""
    try:
        # Ensure the room_id in path matches the room object
        if room.id != room_id:
            raise HTTPException(
                status_code=400,
                detail="Room ID in path must match room ID in body"
            )
        
        result = await rooms_collection.replace_one(
            {"id": room_id},
            room.model_dump()
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Room with ID {room_id} not found")
        
        return room
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# -------------------------------
# Delete Room
# -------------------------------
@app.delete("/rooms/{room_id}", operation_id="delete_room")
async def delete_room(room_id: int):
    """Delete a room by ID"""
    try:
        result = await rooms_collection.delete_one({"id": room_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Room with ID {room_id} not found")
        
        return {
            "message": f"Room {room_id} deleted successfully",
            "deleted_id": room_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# Initialize FastApiMCP
mcp = FastApiMCP(
    app,
    name="Room Management API",
    description="MCP server for Room Management with MongoDB Atlas",
    include_operations=[
        "get_room_by_id",
        "get_all_rooms",
        "create_rooms",
        "update_room",
        "delete_room"
    ]
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