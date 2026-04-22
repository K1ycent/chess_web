import os
import uuid
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (index.html, game.html, client.js)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Simple in-memory matchmaking
waiting_player: Optional[Dict] = None  # {"ws": WebSocket, "username": str}
rooms: Dict[str, List[Dict]] = {}      # room_id -> [{"ws":..., "username":..., "color":...}, ...]


async def send_json_safe(ws: WebSocket, data: dict):
    try:
        await ws.send_json(data)
    except Exception:
        pass


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    global waiting_player, rooms

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "find_match":
                username = data.get("username", "").strip()
                if not username:
                    await send_json_safe(ws, {
                        "type": "error",
                        "message": "Username is required."
                    })
                    continue

                await handle_matchmaking(ws, username)

            elif msg_type == "move":
                room_id = data.get("room_id")
                move = data.get("move")
                if room_id in rooms:
                    for player in rooms[room_id]:
                        if player["ws"] is not ws:
                            await send_json_safe(player["ws"], {
                                "type": "opponent_move",
                                "move": move
                            })

    except WebSocketDisconnect:
        global waiting_player, rooms
        if waiting_player and waiting_player.get("ws") is ws:
            waiting_player = None

        for room_id, players in list(rooms.items()):
            for p in list(players):
                if p["ws"] is ws:
                    players.remove(p)
            if not players:
                del rooms[room_id]


async def handle_matchmaking(ws: WebSocket, username: str):
    global waiting_player, rooms

    if waiting_player is None:
        waiting_player = {"ws": ws, "username": username}
        await send_json_safe(ws, {"type": "searching"})
        return

    opponent = waiting_player
    waiting_player = None

    room_id = str(uuid.uuid4())
    white_player = opponent
    black_player = {"ws": ws, "username": username}

    rooms[room_id] = [
        {"ws": white_player["ws"], "username": white_player["username"], "color": "white"},
        {"ws": black_player["ws"], "username": black_player["username"], "color": "black"},
    ]

    await send_json_safe(white_player["ws"], {
        "type": "match_found",
        "room_id": room_id,
        "your_color": "white",
        "your_username": white_player["username"],
        "opponent_username": black_player["username"],
    })
    await send_json_safe(black_player["ws"], {
        "type": "match_found",
        "room_id": room_id,
        "your_color": "black",
        "your_username": black_player["username"],
        "opponent_username": white_player["username"],
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
