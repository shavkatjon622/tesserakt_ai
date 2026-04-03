import random
import string
from fastapi import WebSocket
import asyncio


class GameManager:
    def __init__(self):
        # Barcha xonalar RAM da saqlanadi
        self.rooms: dict = {}

    # ── Room ──────────────────────────────────────────────────────────────────

    def create_room(self) -> str:
        code = self._generate_code()
        self.rooms[code] = {
            "host_ws": None,
            "category": None,
            "answer": None,
            "drawing": None,
            "players": {},        # { name: { ws, guess } }
            "ai_guess": None,
            "state": "waiting",   # waiting | drawing | guessing | finished
        }
        return code

    def close_room(self, code: str):
        self.rooms.pop(code, None)

    def set_host(self, code: str, ws: WebSocket):
        if code in self.rooms:
            self.rooms[code]["host_ws"] = ws

    # ── Players ───────────────────────────────────────────────────────────────

    def add_player(self, code: str, name: str, ws: WebSocket) -> bool:
        room = self.rooms.get(code)
        if not room:
            return False
        if room["state"] not in ("waiting", "drawing"):
            return False          # O'yin boshlangan, kira olmaydi
        if name in room["players"]:
            return False          # Ism band
        room["players"][name] = {"ws": ws, "guess": None}
        return True

    def remove_player(self, code: str, name: str):
        room = self.rooms.get(code)
        if room and name in room["players"]:
            del room["players"][name]

    def get_player_list(self, code: str) -> list:
        room = self.rooms.get(code)
        if not room:
            return []
        return [
            {"name": n, "guessed": p["guess"] is not None}
            for n, p in room["players"].items()
        ]

    # ── Broadcast ─────────────────────────────────────────────────────────────

    async def broadcast(self, code: str, payload: dict):
        """Xonadagi barcha (host + players) ga xabar yuboradi"""
        room = self.rooms.get(code)
        if not room:
            return

        targets: list[WebSocket] = []

        host_ws = room.get("host_ws")
        if host_ws:
            targets.append(host_ws)

        for pdata in room["players"].values():
            targets.append(pdata["ws"])

        await asyncio.gather(
            *[self._safe_send(ws, payload) for ws in targets],
            return_exceptions=True,
        )

    async def broadcast_to_players(self, code: str, payload: dict):
        """Faqat playerlarga yuboradi (hostga emas)"""
        room = self.rooms.get(code)
        if not room:
            return
        await asyncio.gather(
            *[self._safe_send(p["ws"], payload) for p in room["players"].values()],
            return_exceptions=True,
        )

    async def send_to_host(self, code: str, payload: dict):
        room = self.rooms.get(code)
        if not room:
            return
        host_ws = room.get("host_ws")
        if host_ws:
            await self._safe_send(host_ws, payload)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    async def _safe_send(ws: WebSocket, payload: dict):
        try:
            await ws.send_json(payload)
        except Exception:
            pass  # Ulanish uzilgan bo'lsa e'tibor berma

    @staticmethod
    def _generate_code(length: int = 6) -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))