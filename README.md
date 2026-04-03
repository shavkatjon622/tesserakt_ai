# DeviationGame — Backend

## O'rnatish

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# .env faylida ANTHROPIC_API_KEY ni to'ldiring
```

## Local ishlatish

```bash
uvicorn main:app --reload --port 8000
```

## Deploy (Railway / Render / VPS)

### Railway
```bash
railway login
railway init
railway up
# Environment: ANTHROPIC_API_KEY ni Railway dashboard da qo'shing
```

### Render
- `render.yaml` orqali yoki manual:
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### VPS (Ubuntu)
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
# WebSocket uchun workers=1 bo'lishi kerak (RAM shared bo'lishi uchun)
```

---

## WebSocket Events — Frontend uchun

### Host yuboradi:
| Event | Ma'lumotlar |
|-------|------------|
| `set_category` | `{ category, answer }` |
| `drawing_update` | `{ image: "base64..." }` |
| `start_game` | `{ image: "base64..." }` |
| `end_game` | `{}` |

### Player yuboradi:
| Event | Ma'lumotlar |
|-------|------------|
| `submit_guess` | `{ guess: "mushuk" }` |

### Server → Barchaga:
| Event | Ma'lumotlar |
|-------|------------|
| `player_joined` | `{ name, players[] }` |
| `player_left` | `{ name, players[] }` |
| `game_started` | `{ category, drawing }` |
| `game_over` | `{ answer, ai_guess, ai_correct, results[], winner }` |

### Server → Faqat Host:
| Event | Ma'lumotlar |
|-------|------------|
| `guess_update` | `{ guessed, total, all_done }` |

---

## WebSocket URL Format

```
Host:   ws://localhost:8000/ws/{ROOM_CODE}/host/HostName
Player: ws://localhost:8000/ws/{ROOM_CODE}/player/PlayerName
```

## REST Endpoints

```
POST /room/create          → { room_code: "ABC123" }
GET  /room/{code}/exists   → { exists: true/false }
```