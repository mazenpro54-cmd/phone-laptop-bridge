import ctypes
import os
import subprocess
import time
import socket
import io
import mss
from PIL import Image
import pyautogui

# Disable PyAutoGUI fail-safe delay to ensure real-time trackpad responsiveness
pyautogui.PAUSE = 0.001
pyautogui.FAILSAFE = False

# Windows Virtual-Key Codes for Media & System
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_SPACE = 0x20
VK_RETURN = 0x0D
VK_SHIFT = 0x10

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_MOVE = 0x0001

user32 = ctypes.windll.user32


def press_media_key(vk_code: int):
    """Simulates a Windows media key press using user32.keybd_event."""
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.01)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


class SystemController:
    def __init__(self):
        self._sct = mss.MSS()
        self.screen_width, self.screen_height = pyautogui.size()

    # --- Power & Lock Functions ---
    def lock_workstation(self):
        """Locks the Windows workstation."""
        return user32.LockWorkStation() != 0

    def wake_display(self):
        """Wakes the display by simulating mouse movement and a key pulse."""
        user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
        time.sleep(0.02)
        user32.mouse_event(MOUSEEVENTF_MOVE, -1, 0, 0, 0)
        user32.keybd_event(VK_SHIFT, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        return True

    def unlock_with_pin(self, pin: str):
        """
        Wakes display, dismisses the Windows lock screen,
        and inputs the configured PIN / password.
        """
        self.wake_display()
        time.sleep(0.3)
        # Press Space / Enter to lift lock screen cover to expose PIN input
        user32.keybd_event(VK_SPACE, 0, 0, 0)
        user32.keybd_event(VK_SPACE, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.5)
        # Type the pin using pyautogui
        pyautogui.write(pin, interval=0.03)
        time.sleep(0.1)
        # Submit
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
        return True

    def sleep_pc(self):
        """Puts PC to sleep (Standby)."""
        subprocess.run(
            ["powershell", "-Command", "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState([System.Windows.Forms.PowerState]::Suspend, $false, $false)"],
            shell=True
        )
        return True

    def restart_pc(self):
        """Restarts the PC."""
        subprocess.run(["shutdown", "/r", "/t", "3"], shell=True)
        return True

    def shutdown_pc(self):
        """Shuts down the PC."""
        subprocess.run(["shutdown", "/s", "/t", "3"], shell=True)
        return True

    def cancel_shutdown(self):
        """Cancels a pending shutdown or restart."""
        subprocess.run(["shutdown", "/a"], shell=True)
        return True

    # --- Media & Volume Controls ---
    def volume_up(self, steps=2):
        for _ in range(steps):
            press_media_key(VK_VOLUME_UP)
        return True

    def volume_down(self, steps=2):
        for _ in range(steps):
            press_media_key(VK_VOLUME_DOWN)
        return True

    def volume_mute(self):
        press_media_key(VK_VOLUME_MUTE)
        return True

    def media_play_pause(self):
        press_media_key(VK_MEDIA_PLAY_PAUSE)
        return True

    def media_next(self):
        press_media_key(VK_MEDIA_NEXT_TRACK)
        return True

    def media_prev(self):
        press_media_key(VK_MEDIA_PREV_TRACK)
        return True

    # --- Mouse & Trackpad Emulation ---
    def move_mouse(self, dx: float, dy: float):
        """Moves mouse relative to current position."""
        pyautogui.moveRel(dx, dy)

    def mouse_click(self, button="left"):
        """Performs mouse click ('left', 'right', 'middle')."""
        pyautogui.click(button=button)

    def mouse_double_click(self):
        pyautogui.doubleClick()

    def mouse_down(self, button="left"):
        pyautogui.mouseDown(button=button)

    def mouse_up(self, button="left"):
        pyautogui.mouseUp(button=button)

    def mouse_scroll(self, clicks: int):
        """Scrolls vertically (positive = up, negative = down)."""
        pyautogui.scroll(clicks)

    # --- Keyboard Emulation ---
    def key_tap(self, key: str):
        """Taps a special key (e.g. 'enter', 'esc', 'backspace', 'tab')."""
        pyautogui.press(key)

    def type_text(self, text: str):
        """Types string of text."""
        pyautogui.write(text, interval=0.01)

    def hotkey(self, *keys):
        """Executes hotkey combination, e.g. ('win', 'd') or ('alt', 'tab')."""
        pyautogui.hotkey(*keys)

    # --- Quick App Launching ---
    def launch_app(self, app_name: str):
        apps = {
            "browser": "start https://www.google.com",
            "explorer": "explorer",
            "taskmgr": "taskmgr",
            "notepad": "notepad",
            "cmd": "start cmd",
            "terminal": "wt",
            "calculator": "calc",
            "settings": "start ms-settings:",
        }
        cmd = apps.get(app_name.lower())
        if cmd:
            subprocess.Popen(cmd, shell=True)
            return True
        return False

    # --- Screen Capture (JPEG) ---
    def capture_screen_jpeg(self, quality=60, max_width=1024):
        """
        Captures primary monitor and returns JPEG bytes.
        Optimized for real-time streaming with resizing and quality tuning.
        Falls back to a status image if the screen is locked/sleeping.
        """
        try:
            with mss.MSS() as sct:
                monitor = sct.monitors[1]
                raw_screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", raw_screenshot.size, raw_screenshot.bgra, "raw", "BGRX")
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.BILINEAR)
        except Exception:
            # When Windows is locked or display is powered off, generate a clean placeholder
            from PIL import ImageDraw
            img = Image.new("RGB", (max_width, int(max_width * 9 / 16)), "#0f172a")
            draw = ImageDraw.Draw(img)
            draw.text((max_width // 4, img.height // 2 - 10), "Desktop is Locked or Screen is Off", fill="#94a3b8")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=False)
        return buffer.getvalue()


# Helper to get network and WoL info
def get_system_network_info():
    hostname = socket.gethostname()
    local_ips = []
    try:
        # Determine preferred outbound IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
    except Exception:
        primary_ip = "127.0.0.1"

    # Get MAC Address via PowerShell or uuid
    mac_address = "Unknown"
    try:
        output = subprocess.check_output(
            ["powershell", "-Command", "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceAlias -match 'Wi-Fi|Ethernet' } | Select-Object -ExpandProperty MacAddress"],
            text=True
        ).strip().splitlines()
        if output:
            mac_address = output[0].strip()
    except Exception:
        pass

    return {
        "hostname": hostname,
        "primary_ip": primary_ip,
        "mac_address": mac_address,
        "broadcast_ip": "255.255.255.255",
        "wol_port": 9
    }


def send_wol_magic_packet(mac_address: str, broadcast_ip="255.255.255.255", port=9):
    """Sends a Wake-on-LAN magic packet."""
    cleaned_mac = mac_address.replace(":", "").replace("-", "")
    if len(cleaned_mac) != 12:
        raise ValueError("Invalid MAC address length")
    hw_addr = bytes.fromhex(cleaned_mac)
    magic_packet = b"\xff" * 6 + hw_addr * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, port))
    return True
