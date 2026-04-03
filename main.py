from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from game_manager import GameManager

game_manager = GameManager()

app = FastAPI(
        title="Davinci",
        description="DavinciVSAI",
        version="1.0.0",
        docs_url="/swagger"
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # production da front URL ni yozing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── REST Endpoints ────────────────────────────────────────────────────────────
#todo make swagger for theses threee endpoints
@app.get("/")
async def root():
    return {"status": "ok", "message": "DeviationGame backend ishlayapti"}


@app.post("/room/create")
async def create_room():
    """Host yangi xona yaratadi — room_code qaytaradi"""
    code = game_manager.create_room()
    return {"room_code": code}


@app.get("/room/{code}/exists")
async def room_exists(code: str):
    exists = code.upper() in game_manager.rooms
    return {"exists": exists}


# ─── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/{room_code}/{role}/{name}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    role: str,   # "host" yoki "player"
    name: str,
):
    room_code = room_code.upper()

    if room_code not in game_manager.rooms:
        await websocket.close(code=4004, reason="Xona topilmadi")
        return

    await websocket.accept()

    if role == "host":
        game_manager.set_host(room_code, websocket)
        await websocket.send_json({"event": "host_connected", "room_code": room_code})
    else:
        # Player qo'shiladi
        ok = game_manager.add_player(room_code, name, websocket)
        if not ok:
            await websocket.send_json({"event": "error", "message": "Ism band yoki o'yin boshlangan"})
            await websocket.close()
            return

        # Playerni broadcast — barchaga xabar
        await game_manager.broadcast(room_code, {
            "event": "player_joined",
            "name": name,
            "players": game_manager.get_player_list(room_code),
        })

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            await handle_message(room_code, role, name, websocket, data)

    except WebSocketDisconnect:
        if role == "player":
            game_manager.remove_player(room_code, name)
            await game_manager.broadcast(room_code, {
                "event": "player_left",
                "name": name,
                "players": game_manager.get_player_list(room_code),
            })
        else:
            # Host ketsa xonani yopish
            game_manager.close_room(room_code)


# ─── Message Handler ───────────────────────────────────────────────────────────

async def handle_message(room_code: str, role: str, name: str, ws: WebSocket, data: dict):
    event = data.get("event")
    room = game_manager.rooms.get(room_code)
    if not room:
        return

    # HOST events
    if role == "host":

        if event == "set_category":
            # Host kategoriya va javobni belgilaydi
            room["category"] = data["category"]
            room["answer"] = data["answer"].strip().lower()
            room["state"] = "drawing"
            await ws.send_json({"event": "category_set", "category": data["category"]})

        elif event == "drawing_update":
            # Canvas rasm (base64) ni playerlarga yuborish (agar real-time ko'rish kerak bo'lsa)
            # Hozircha saqlab qo'yamiz, game_start da yuboramiz
            room["drawing"] = data["image"]

        elif event == "start_game":
            # O'yinni boshlash — rasm va kategoriya playerlarga ketadi
            room["drawing"] = data.get("image", room.get("drawing", ""))
            room["state"] = "guessing"

            await game_manager.broadcast(room_code, {
                "event": "game_started",
                "category": room["category"],
                "drawing": room["drawing"],
            })

        elif event == "end_game":
            # Frontend AI taxminini o'zi hisoblab yuboradi
            room["ai_guess"] = data.get("ai_guess", "bilmadim").strip().lower()
            await reveal_results(room_code)

    # PLAYER events
    else:
        if event == "submit_guess":
            guess = data.get("guess", "").strip().lower()
            if name in room["players"]:
                room["players"][name]["guess"] = guess

            # Hamma taxmin qildimi? (ixtiyoriy — auto end)
            all_guessed = all(
                p["guess"] is not None for p in room["players"].values()
            )
            # Hostga xabar — nechta taxmin qildi
            guessed_count = sum(1 for p in room["players"].values() if p["guess"] is not None)
            host_ws = room.get("host_ws")
            if host_ws:
                try:
                    await host_ws.send_json({
                        "event": "guess_update",
                        "guessed": guessed_count,
                        "total": len(room["players"]),
                        "all_done": all_guessed,
                    })
                except Exception:
                    pass


# ─── Reveal Results ────────────────────────────────────────────────────────────

async def reveal_results(room_code: str):
    room = game_manager.rooms.get(room_code)
    if not room:
        return

    answer = room.get("answer", "")
    ai_guess = room.get("ai_guess", "")
    players = room.get("players", {})

    # Har bir o'yinchi natijasi
    results = []
    human_correct = False
    for pname, pdata in players.items():
        guess = pdata.get("guess") or ""
        correct = guess.lower() == answer.lower()
        if correct:
            human_correct = True
        results.append({
            "name": pname,
            "guess": guess,
            "correct": correct,
        })

    ai_correct = ai_guess.lower() == answer.lower()

    # G'olib aniqlash
    if ai_correct and human_correct:
        winner = "draw"          # Durrang
    elif ai_correct:
        winner = "ai"
    elif human_correct:
        winner = "human"
    else:
        winner = "none"

    payload = {
        "event": "game_over",
        "answer": answer,
        "ai_guess": ai_guess,
        "ai_correct": ai_correct,
        "results": results,
        "winner": winner,
    }

    room["state"] = "finished"
    await game_manager.broadcast(room_code, payload)