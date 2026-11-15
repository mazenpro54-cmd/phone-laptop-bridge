# 📱 Phone-to-Laptop Bridge

Control, wake up, unlock, and manage your Windows laptop directly from your phone over your local Wi-Fi.

## ✨ Features
- ⚡ **Wake from Sleep (Wake-on-LAN)**: Broadcasts UDP magic packets to wake the laptop over Wi-Fi/Ethernet.
- 🔓 **One-Tap Unlock**: Automatically wakes the display, lifts the lock screen, and types your Windows PIN.
- 🔒 **Lock, Sleep, Restart, & Shutdown**: Full system power management from your phone.
- 🖱️ **Ultra-Responsive Touchpad**: Touchpad gestures (1-finger move, 1-finger tap left-click, 2-finger tap right-click, 2-finger scroll) and hotkeys (Esc, Win+D, Alt+Tab).
- 🖥️ **Live Desktop Mirroring**: Stream your laptop's screen directly to your phone browser and tap to click.
- 🎵 **Media & Volume Control**: Volume up/down/mute, play/pause, next/prev tracks.
- 🚀 **Quick App Launchers**: Open Browser, Explorer, Task Manager, Notepad, and more with one tap.
- 📱 **Progressive Web App (PWA)**: Works on iOS & Android without installing third-party app store apps—just tap *"Add to Home Screen"*.

---

## 🚀 Quick Start

1. **Start the Bridge**:
   - Double-click `start_bridge.bat`, OR run:
     ```powershell
     cd C:\Users\Mazen\.gemini\antigravity\scratch\phone-laptop-bridge
     venv\Scripts\python.exe run.py
     ```
2. **Connect from your Phone**:
   - Make sure your phone is connected to the same Wi-Fi (or mobile hotspot) as your laptop.
   - Scan the QR code displayed in the terminal, or navigate in Safari/Chrome to:
     `http://<YOUR_LAPTOP_IP>:8000` (e.g. `http://172.20.10.2:8000`)
   - Tap **"Add to Home Screen"** in your phone's browser for full-screen native app mode.

---

## 📡 Wake-on-LAN Setup (Waking When Laptop is Asleep)

1. **Enable Wake on Wi-Fi in Windows**:
   - Press `Win + X` &rarr; **Device Manager**.
   - Expand **Network adapters** &rarr; Right-click your Wi-Fi adapter &rarr; **Properties**.
   - Go to the **Power Management** tab &rarr; Check **"Allow this device to wake the computer"** and **"Only allow a magic packet to wake the computer"**.
   - Under the **Advanced** tab, ensure **Wake on Magic Packet** is set to **Enabled**.

2. **Lid-Closed Operation (Optional)**:
   - In Windows Search, type *"Change what closing the lid does"*.
   - Set *"When I close the lid"* to **Do Nothing** (for Plugged in / Battery).
   - This keeps your laptop awake or accessible even when the lid is closed.

3. **Wake Shortcut on Phone**:
   - Use any free Wake-on-LAN app (such as *Wolow* on iOS or *Wake On Lan* by Aquila on Android), or Apple Shortcuts.
   - Enter your laptop's MAC address (shown in the web app under the **Wake Guide** tab).
