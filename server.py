import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

from system_control import SystemController, get_system_network_info, send_wol_magic_packet

app = FastAPI(title="Phone-to-Laptop Bridge")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Default configuration
default_config = {
    "server_pin": "",          # Optional password to protect phone dashboard
    "windows_unlock_pin": "",  # Optional saved Windows PIN for one-tap unlock
    "screen_stream_fps": 12,
    "screen_quality": 55,
    "screen_max_width": 1024
}

if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w") as f:
        json.dump(default_config, f, indent=4)

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return default_config

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)

sys_ctrl = SystemController()

# Mount static files
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Phone-to-Laptop Bridge</h1><p>UI loading...</p>")


@app.get("/manifest.json")
async def serve_manifest():
    manifest_file = os.path.join(STATIC_DIR, "manifest.json")
    return FileResponse(manifest_file, media_type="application/manifest+json")


@app.get("/api/info")
async def get_info():
    cfg = load_config()
    net_info = get_system_network_info()
    return {
        "status": "online",
        "system": net_info,
        "screen": {
            "width": sys_ctrl.screen_width,
            "height": sys_ctrl.screen_height
        },
        "has_pin_protection": bool(cfg.get("server_pin")),
        "has_saved_unlock_pin": bool(cfg.get("windows_unlock_pin"))
    }


class ConfigUpdateRequest(BaseModel):
    server_pin: Optional[str] = None
    windows_unlock_pin: Optional[str] = None
    screen_stream_fps: Optional[int] = None
    screen_quality: Optional[int] = None


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    cfg = load_config()
    if req.server_pin is not None:
        cfg["server_pin"] = req.server_pin.strip()
    if req.windows_unlock_pin is not None:
        cfg["windows_unlock_pin"] = req.windows_unlock_pin.strip()
    if req.screen_stream_fps is not None:
        cfg["screen_stream_fps"] = max(1, min(30, req.screen_stream_fps))
    if req.screen_quality is not None:
        cfg["screen_quality"] = max(20, min(95, req.screen_quality))
    save_config(cfg)
    return {"status": "success", "message": "Configuration updated"}


class PowerActionRequest(BaseModel):
    action: str  # 'lock', 'unlock', 'wake', 'sleep', 'restart', 'shutdown', 'cancel'
    pin: Optional[str] = None


@app.post("/api/power")
async def power_control(req: PowerActionRequest):
    action = req.action.lower()
    cfg = load_config()

    if action == "lock":
        sys_ctrl.lock_workstation()
        return {"status": "ok", "message": "Workstation locked"}

    elif action == "wake":
        sys_ctrl.wake_display()
        return {"status": "ok", "message": "Display wake triggered"}

    elif action == "unlock":
        unlock_pin = req.pin or cfg.get("windows_unlock_pin")
        if not unlock_pin:
            raise HTTPException(status_code=400, detail="No PIN provided or configured for unlock")
        sys_ctrl.unlock_with_pin(unlock_pin)
        return {"status": "ok", "message": "Unlock sequence sent"}

    elif action == "sleep":
        # Launch sleep asynchronously with a 1 second delay so the HTTP response finishes
        asyncio.create_task(async_delayed_sleep())
        return {"status": "ok", "message": "Entering sleep mode"}

    elif action == "restart":
        sys_ctrl.restart_pc()
        return {"status": "ok", "message": "Restarting in 3 seconds"}

    elif action == "shutdown":
        sys_ctrl.shutdown_pc()
        return {"status": "ok", "message": "Shutting down in 3 seconds"}

    elif action == "cancel":
        sys_ctrl.cancel_shutdown()
        return {"status": "ok", "message": "Pending shutdown cancelled"}

    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


async def async_delayed_sleep():
    await asyncio.sleep(1.0)
    sys_ctrl.sleep_pc()


class MediaActionRequest(BaseModel):
    action: str  # 'vol_up', 'vol_down', 'mute', 'play_pause', 'next', 'prev'
    steps: Optional[int] = 2


@app.post("/api/media")
async def media_control(req: MediaActionRequest):
    act = req.action.lower()
    if act == "vol_up":
        sys_ctrl.volume_up(req.steps or 2)
    elif act == "vol_down":
        sys_ctrl.volume_down(req.steps or 2)
    elif act == "mute":
        sys_ctrl.volume_mute()
    elif act == "play_pause":
        sys_ctrl.media_play_pause()
    elif act == "next":
        sys_ctrl.media_next()
    elif act == "prev":
        sys_ctrl.media_prev()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown media action: {act}")
    return {"status": "ok"}


@app.post("/api/apps/{app_name}")
async def launch_app(app_name: str):
    success = sys_ctrl.launch_app(app_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Unknown app shortcut: {app_name}")
    return {"status": "ok", "message": f"Launched {app_name}"}


@app.post("/api/wol/send")
async def trigger_wol(mac: Optional[str] = None):
    net_info = get_system_network_info()
    target_mac = mac or net_info.get("mac_address")
    if not target_mac or target_mac == "Unknown":
        raise HTTPException(status_code=400, detail="MAC address unknown")
    send_wol_magic_packet(target_mac)
    return {"status": "ok", "message": f"Magic packet sent to {target_mac}"}


@app.get("/api/screen/shot")
async def get_screenshot(quality: int = 60, width: int = 1024):
    jpeg_bytes = sys_ctrl.capture_screen_jpeg(quality=quality, max_width=width)
    return Response(content=jpeg_bytes, media_type="image/jpeg")


# --- WebSocket for Real-time Touchpad & Keyboard ---
@app.websocket("/ws/input")
async def websocket_input_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            cmd = json.loads(data)
            action_type = cmd.get("type")

            if action_type == "move":
                dx = float(cmd.get("dx", 0))
                dy = float(cmd.get("dy", 0))
                sys_ctrl.move_mouse(dx, dy)

            elif action_type == "click":
                btn = cmd.get("button", "left")
                sys_ctrl.mouse_click(button=btn)

            elif action_type == "dblclick":
                sys_ctrl.mouse_double_click()

            elif action_type == "scroll":
                dy = int(cmd.get("dy", 0))
                sys_ctrl.mouse_scroll(dy)

            elif action_type == "mousedown":
                btn = cmd.get("button", "left")
                sys_ctrl.mouse_down(btn)

            elif action_type == "mouseup":
                btn = cmd.get("button", "left")
                sys_ctrl.mouse_up(btn)

            elif action_type == "key":
                key = cmd.get("key")
                if key:
                    sys_ctrl.key_tap(key)

            elif action_type == "type":
                text = cmd.get("text", "")
                if text:
                    sys_ctrl.type_text(text)

            elif action_type == "hotkey":
                keys = cmd.get("keys", [])
                if keys:
                    sys_ctrl.hotkey(*keys)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Input error: {e}")


# --- WebSocket for Live Screen Stream ---
@app.websocket("/ws/screen")
async def websocket_screen_endpoint(websocket: WebSocket):
    await websocket.accept()
    cfg = load_config()
    fps = cfg.get("screen_stream_fps", 12)
    quality = cfg.get("screen_quality", 55)
    max_width = cfg.get("screen_max_width", 960)
    delay = 1.0 / max(1, fps)

    try:
        while True:
            # Check for client messages (e.g. pause/resume or quality change)
            try:
                # Non-blocking check if client sent a message
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.001)
                cmd = json.loads(msg)
                if "fps" in cmd:
                    fps = max(1, min(30, cmd["fps"]))
                    delay = 1.0 / fps
                if "quality" in cmd:
                    quality = max(20, min(90, cmd["quality"]))
            except asyncio.TimeoutError:
                pass

            jpeg_bytes = sys_ctrl.capture_screen_jpeg(quality=quality, max_width=max_width)
            await websocket.send_bytes(jpeg_bytes)
            await asyncio.sleep(delay)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Screen error: {e}")
