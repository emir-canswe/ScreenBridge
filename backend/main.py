"""
ScreenBridge - Backend (HTML gömülü versiyon)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import pygetwindow as gw
import json
import asyncio
import os

app = FastAPI(title="ScreenBridge")

LEFT_MONITOR_WIDTH  = 1920
LEFT_MONITOR_HEIGHT = 1080
RIGHT_MONITOR_X     = 1920

IGNORED_TITLES = {
    "", "Program Manager", "Windows Input Experience",
    "ScreenBridge", "Task Switching"
}

# HTML dosyasını oku
def get_html():
    here = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(here, "..", "frontend", "index.html")
    html_path = os.path.normpath(html_path)
    with open(html_path, "r", encoding="utf-8") as f:
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket bağlandı")
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
        print("Bağlantı kesildi")
    except Exception as e:
        print(f"WebSocket hatası: {e}")
    finally:
        if update_task:
            update_task.cancel()

if __name__ == "__main__":
    import uvicorn
    print("🌉 ScreenBridge başlıyor...")
    print("📺 http://localhost:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)