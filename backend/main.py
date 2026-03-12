"""
ScreenBridge - Backend v2
FastAPI + WebSocket + Kamera takibi
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
import pygetwindow as gw
import json
import asyncio
import os
import time

app = FastAPI(title="ScreenBridge")

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
INDEX_FILE   = os.path.normpath(os.path.join(FRONTEND_DIR, "index.html"))

LEFT_MONITOR_WIDTH  = 1920
LEFT_MONITOR_HEIGHT = 1080
RIGHT_MONITOR_X     = 1920

IGNORED_TITLES = {
    "", "Program Manager", "Windows Input Experience",
    "ScreenBridge", "Task Switching"
}

# Aktif WebSocket bağlantıları
aktif_ws = set()

# Kamera modülü (lazy import)
takipci = None

def get_html():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return f.read()

def get_all_windows():
    windows = []
    try:
        for w in gw.getAllWindows():
            if w.title in IGNORED_TITLES:
                continue
            if w.width <= 0 or w.height <= 0:
                continue
            monitor = "right" if w.left >= RIGHT_MONITOR_X else "left"
            windows.append({
                "title": w.title,
                "left": w.left,
                "top": w.top,
                "width": w.width,
                "height": w.height,
                "monitor": monitor
            })
    except Exception as e:
        print(f"Hata: {e}")
    return windows

def move_window_to_left(title):
    try:
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            return {"success": False, "error": "Pencere bulunamadı"}
        win = matches[0]
        try: win.activate()
        except: pass
        win.moveTo(max(0, (LEFT_MONITOR_WIDTH - win.width) // 2),
                   max(50, (LEFT_MONITOR_HEIGHT - win.height) // 2))
        return {"success": True, "message": f"'{title}' sol monitöre taşındı"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def move_window_to_right(title):
    try:
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            return {"success": False, "error": "Pencere bulunamadı"}
        win = matches[0]
        try: win.activate()
        except: pass
        win.moveTo(RIGHT_MONITOR_X + max(0, (LEFT_MONITOR_WIDTH - win.width) // 2),
                   max(50, (LEFT_MONITOR_HEIGHT - win.height) // 2))
        return {"success": True, "message": f"'{title}' sağ monitöre taşındı"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def ws_broadcast(msg: dict):
    """Tüm bağlı WebSocket istemcilerine mesaj gönder."""
    kapatilacak = set()
    for ws in aktif_ws:
        try:
            await ws.send_text(json.dumps(msg))
        except:
            kapatilacak.add(ws)
    aktif_ws.difference_update(kapatilacak)

def kamera_hareket_callback(yon: str):
    """Kamera hareketi algıladığında çağrılır."""
    global takipci
    if takipci is None or takipci.secili_pencere is None:
        return

    title = takipci.secili_pencere
    if yon == "left":
        result = move_window_to_left(title)
    else:
        result = move_window_to_right(title)

    # WebSocket üzerinden bildir
    loop = asyncio.new_event_loop()
    asyncio.run_coroutine_threadsafe(
        ws_broadcast({"type": "camera_move", "yon": yon, "result": result, "windows": get_all_windows()}),
        asyncio.get_event_loop()
    )

# ── Endpoints ─────────────────────────────────────────────────

@app.get("/")
async def root():
    return HTMLResponse(content=get_html())

@app.get("/api/windows")
async def list_windows():
    return {"windows": get_all_windows()}

@app.post("/api/move/left")
async def move_left(data: dict):
    return move_window_to_left(data.get("title", ""))

@app.post("/api/move/right")
async def move_right(data: dict):
    return move_window_to_right(data.get("title", ""))

@app.post("/api/camera/start")
async def camera_start(data: dict):
    """Kamerayı başlat."""
    global takipci
    try:
        from camera import KalemTakipci
        if takipci and takipci.calisıyor:
            takipci.durdur()
        takipci = KalemTakipci()
        takipci.secili_pencere = data.get("title")
        takipci.baslat(kamera_hareket_callback)
        return {"success": True, "message": "Kamera başlatıldı"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/camera/stop")
async def camera_stop():
    """Kamerayı durdur."""
    global takipci
    if takipci:
        takipci.durdur()
        takipci = None
    return {"success": True}

@app.post("/api/camera/select-color")
async def camera_select_color(data: dict):
    """Tıklanan koordinattaki rengi seç."""
    global takipci
    if not takipci or not takipci.calisıyor:
        return {"success": False, "error": "Kamera çalışmıyor"}
    x = int(data.get("x", 0))
    y = int(data.get("y", 0))
    takipci.renk_sec(x, y)
    return {"success": True, "message": "Renk seçildi, takip başladı!"}

@app.get("/api/camera/frame")
async def camera_frame():
    """Anlık kamera karesi (JPEG)."""
    global takipci
    if not takipci or not takipci.calisıyor:
        return JSONResponse({"error": "Kamera kapalı"}, status_code=404)
    frame = takipci.frame_al()
    if frame is None:
        return JSONResponse({"error": "Frame yok"}, status_code=404)
    return StreamingResponse(iter([frame]), media_type="image/jpeg")

@app.get("/api/camera/status")
async def camera_status():
    global takipci
    if not takipci or not takipci.calisıyor:
        return {"aktif": False}
    return {
        "aktif": True,
        "renk_secildi": takipci.renk_secildi,
        "durum": takipci.durum,
        "secili_pencere": takipci.secili_pencere
    }

# ── WebSocket ─────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    aktif_ws.add(websocket)
    update_task = None
    try:
        await websocket.send_text(json.dumps({"type": "windows", "data": get_all_windows()}))

        async def send_updates():
            while True:
                await asyncio.sleep(2)
                await websocket.send_text(json.dumps({"type": "windows", "data": get_all_windows()}))

        update_task = asyncio.create_task(send_updates())

        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg["action"] == "move_left":
                result = move_window_to_left(msg["title"])
            elif msg["action"] == "move_right":
                result = move_window_to_right(msg["title"])
            else:
                result = {"success": True, "message": "ok"}
            await websocket.send_text(json.dumps({"type": "result", "data": result}))
            await asyncio.sleep(0.3)
            await websocket.send_text(json.dumps({"type": "windows", "data": get_all_windows()}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS hata: {e}")
    finally:
        aktif_ws.discard(websocket)
        if update_task:
            update_task.cancel()

if __name__ == "__main__":
    import uvicorn
    print("🌉 ScreenBridge v2 başlıyor...")
    print("📺 http://localhost:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)