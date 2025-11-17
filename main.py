import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Match, HitEvent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Beer Pong API is running"}

# Utility to parse ObjectId safely

def _to_obj_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

# Create a new match
class CreateMatchRequest(BaseModel):
    team_a: str
    team_b: str
    cups_per_side: int = 10

@app.post("/api/matches")
def create_match(payload: CreateMatchRequest):
    match = Match(
        team_a=payload.team_a,
        team_b=payload.team_b,
        cups_per_side=payload.cups_per_side,
        cups_remaining_a=payload.cups_per_side,
        cups_remaining_b=payload.cups_per_side,
    )
    match_id = create_document("match", match)
    return {"id": match_id}

# Get recent matches
@app.get("/api/matches")
def list_matches(limit: int = 20):
    docs = db["match"].find({}).sort("created_at", -1).limit(limit)
    results = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        results.append(d)
    return results

# Get single match
@app.get("/api/matches/{match_id}")
def get_match(match_id: str):
    doc = db["match"].find_one({"_id": _to_obj_id(match_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Match not found")
    doc["id"] = str(doc.pop("_id"))
    return doc

# Record a hit
class HitPayload(BaseModel):
    team: Literal['A', 'B']
    shooter: Optional[str] = None
    cups: int = 1

@app.post("/api/matches/{match_id}/hit")
def record_hit(match_id: str, payload: HitPayload):
    doc = db["match"].find_one({"_id": _to_obj_id(match_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Match not found")
    if doc.get("status") == "finished":
        raise HTTPException(status_code=400, detail="Match already finished")

    # Update cups remaining
    cups_field = "cups_remaining_b" if payload.team == 'A' else "cups_remaining_a"
    new_value = max(0, int(doc.get(cups_field, 0)) - payload.cups)

    # Determine winner if any
    winner = doc.get("winner")
    status = doc.get("status", "ongoing")
    if new_value == 0:
        status = "finished"
        winner = payload.team

    event = HitEvent(team=payload.team, shooter=payload.shooter, cups=payload.cups)

    update = {
        "$set": {cups_field: new_value, "status": status, "winner": winner},
        "$push": {"events": event.model_dump()}
    }
    db["match"].update_one({"_id": _to_obj_id(match_id)}, update)

    return {"ok": True, "status": status, "winner": winner}

# Reset match to start values
@app.post("/api/matches/{match_id}/reset")
def reset_match(match_id: str):
    doc = db["match"].find_one({"_id": _to_obj_id(match_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Match not found")
    cups = int(doc.get("cups_per_side", 10))
    db["match"].update_one(
        {"_id": _to_obj_id(match_id)},
        {"$set": {"cups_remaining_a": cups, "cups_remaining_b": cups, "status": "ongoing", "winner": None, "events": []}}
    )
    return {"ok": True}

# Test endpoint remains
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
