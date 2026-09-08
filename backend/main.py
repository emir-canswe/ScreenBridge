"""
ScreenBridge - Backend v2
FastAPI + WebSocket + Kamera takibi + Dinamik Monitör Yönetimi
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
import pygetwindow as gw
import json
import asyncio
import os
import sys
import time

# Proje dizinini sys.path'e ekle (doğrudan veya kök dizinden çalıştırmada import hatasını önler)
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
INDEX_FILE   = os.path.normpath(os.path.join(FRONTEND_DIR, "index.html"))

IGNORED_TITLES = {
    "", "Program Manager", "Windows Input Experience",
    "ScreenBridge", "Task Switching"
}

app = FastAPI(title="ScreenBridge")

# Aktif WebSocket bağlantıları
aktif_ws = set()

# Kamera modülü (lazy import)
takipci = None

# Ana asyncio olay döngüsü referansı (arka plan thread'lerinden ws_broadcast yapabilmek için)
main_loop = None

@app.on_event("startup")
async def on_startup():
    global main_loop
    main_loop = asyncio.get_running_loop()


def get_html():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ScreenBridge Frontend index.html dosyası bulunamadı</h1>"


def get_monitors():
    """Windows API (ctypes) ile bağlı monitörlerin koordinatlarını dinamik olarak al."""
    monitors = []
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        def _monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            r = lprcMonitor.contents
            monitors.append({
                "left": int(r.left),
                "top": int(r.top),
                "right": int(r.right),
                "bottom": int(r.bottom),
                "width": int(r.right - r.left),
                "height": int(r.bottom - r.top)
            })
            return 1

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM
        )
        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_monitor_enum_proc), 0)
    except Exception as e:
        print(f"Monitör algılama uyarısı: {e}")

    # Soldan sağa X eksenine göre sırala
    monitors.sort(key=lambda m: m["left"])

    if not monitors:
        # Fallback standart çözünürlük
        monitors = [
            {"left": 0, "top": 0, "right": 1920, "bottom": 1080, "width": 1920, "height": 1080},
            {"left": 1920, "top": 0, "right": 3840, "bottom": 1080, "width": 1920, "height": 1080}
        ]
    elif len(monitors) == 1:
        # Tek monitör varsa sağ monitör alanını yanına konumlandır
        m0 = monitors[0]
        monitors.append({
            "left": m0["right"],
            "top": m0["top"],
            "right": m0["right"] + m0["width"],
            "bottom": m0["bottom"],
            "width": m0["width"],
            "height": m0["height"]
        })
    return monitors


def get_monitor_boundary():
    monitors = get_monitors()
    right_x = monitors[1]["left"]
    return monitors, right_x


def get_all_windows():
    windows = []
    try:
        monitors, right_x = get_monitor_boundary()
        for w in gw.getAllWindows():
            if not w.title or w.title.strip() in IGNORED_TITLES:
                continue
            if w.width <= 0 or w.height <= 0:
                continue
            monitor = "right" if w.left >= right_x else "left"
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


def restore_if_needed(win):
    """Pencere tam ekran veya simge durumundaysa taşıma öncesi geri yükle."""
    try:
        if getattr(win, "isMaximized", False) or getattr(win, "isMinimized", False):
            win.restore()
            time.sleep(0.05)
    except Exception:
        pass


def move_window_to_left(title):
    try:
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            return {"success": False, "error": f"'{title}' başlıklı pencere bulunamadı"}
        win = matches[0]
        restore_if_needed(win)
        try:
            win.activate()
        except Exception:
            pass

        monitors, _ = get_monitor_boundary()
        m = monitors[0]
        target_x = m["left"] + max(0, (m["width"] - win.width) // 2)
        target_y = m["top"] + max(50, (m["height"] - win.height) // 2)
        win.moveTo(target_x, target_y)
        return {"success": True, "message": f"'{title}' sol monitöre taşındı"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def move_window_to_right(title):
    try:
        matches = gw.getWindowsWithTitle(title)
        if not matches:
            return {"success": False, "error": f"'{title}' başlıklı pencere bulunamadı"}
        win = matches[0]
        restore_if_needed(win)
        try:
            win.activate()
        except Exception:
            pass

        monitors, _ = get_monitor_boundary()
        m = monitors[1] if len(monitors) > 1 else monitors[0]
        target_x = m["left"] + max(0, (m["width"] - win.width) // 2)
        target_y = m["top"] + max(50, (m["height"] - win.height) // 2)
        win.moveTo(target_x, target_y)
        return {"success": True, "message": f"'{title}' sağ monitöre taşındı"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def ws_broadcast(msg: dict):
    """Tüm bağlı WebSocket istemcilerine mesaj gönder."""
    kapatilacak = set()
    for ws in list(aktif_ws):
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            kapatilacak.add(ws)
    aktif_ws.difference_update(kapatilacak)


def kamera_hareket_callback(yon: str):
    """Kamera hareketi algıladığında arka plan OpenCV thread'inden çağrılır."""
    global takipci, main_loop
    if takipci is None or takipci.secili_pencere is None:
        return

    title = takipci.secili_pencere
    if yon == "left":
        result = move_window_to_left(title)
    else:
        result = move_window_to_right(title)

    # WebSocket üzerinden ana asyncio döngüsüne güvenli bildirim yap
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            ws_broadcast({
                "type": "camera_move",
                "yon": yon,
                "result": result,
                "windows": get_all_windows()
            }),
            main_loop
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
        try:
            from camera import KalemTakipci
        except ImportError:
            from backend.camera import KalemTakipci

        if takipci and takipci.calisiyor:
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
    if not takipci or not takipci.calisiyor:
        return {"success": False, "error": "Kamera çalışmıyor"}
    x = int(data.get("x", 0))
    y = int(data.get("y", 0))
    takipci.renk_sec(x, y)
    return {"success": True, "message": "Renk seçildi, takip başladı!"}


@app.get("/api/camera/frame")
async def camera_frame():
    """Anlık kamera karesi (JPEG)."""
    global takipci
    if not takipci or not takipci.calisiyor:
        return JSONResponse({"error": "Kamera kapalı"}, status_code=404)
    frame = takipci.frame_al()
    if frame is None:
        return JSONResponse({"error": "Frame yok"}, status_code=404)
    return StreamingResponse(iter([frame]), media_type="image/jpeg")


@app.get("/api/camera/status")
async def camera_status():
    global takipci
    if not takipci or not takipci.calisiyor:
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
            if msg.get("action") == "move_left":
                result = move_window_to_left(msg.get("title", ""))
            elif msg.get("action") == "move_right":
                result = move_window_to_right(msg.get("title", ""))
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