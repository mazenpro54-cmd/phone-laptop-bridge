// --- State & Connection ---
let wsInput = null;
let wsScreen = null;
let systemInfo = null;
let isScreenStreaming = false;

// Determine target backend API & WebSocket base URL
function getBaseUrls() {
  const customHost = localStorage.getItem("laptop_bridge_host");
  if (customHost) {
    const cleanHost = customHost.replace(/^https?:\/\//, "").replace(/\/$/, "");
    const isHttps = customHost.startsWith("https");
    return {
      httpBase: `${isHttps ? "https" : "http"}://${cleanHost}`,
      wsBase: `${isHttps ? "wss" : "ws"}://${cleanHost}`
    };
  }
  const protocol = window.location.protocol === "https:" ? "https" : "http";
  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
  return {
    httpBase: `${protocol}://${window.location.host}`,
    wsBase: `${wsProtocol}://${window.location.host}`
  };
}

// DOM Elements
const statusBadge = document.getElementById("status-badge");
const statusText = document.getElementById("status-text");
const navItems = document.querySelectorAll(".nav-item");
const tabPanes = document.querySelectorAll(".tab-pane");

// Initialize Navigation Tabs
navItems.forEach(item => {
  item.addEventListener("click", () => {
    navItems.forEach(n => n.classList.remove("active"));
    tabPanes.forEach(p => p.classList.remove("active"));
    item.classList.add("active");
    const target = item.getAttribute("data-tab");
    document.getElementById(target).classList.add("active");

    if (target === "tab-screen") {
      startScreenStream();
    } else {
      stopScreenStream();
    }
  });
});

// --- Connect Input WebSocket ---
function connectInputWS() {
  const { wsBase } = getBaseUrls();
  const wsUrl = `${wsBase}/ws/input`;
  wsInput = new WebSocket(wsUrl);

  wsInput.onopen = () => {
    statusBadge.classList.add("online");
    statusText.innerText = "Connected";
  };

  wsInput.onclose = () => {
    statusBadge.classList.remove("online");
    statusText.innerText = "Reconnecting...";
    setTimeout(connectInputWS, 2000);
  };

  wsInput.onerror = () => {
    wsInput.close();
  };
}

function sendInput(payload) {
  if (wsInput && wsInput.readyState === WebSocket.OPEN) {
    wsInput.send(JSON.stringify(payload));
  }
}

// --- Fetch System Info ---
async function fetchSystemInfo() {
  try {
    const { httpBase } = getBaseUrls();
    const res = await fetch(`${httpBase}/api/info`);
    systemInfo = await res.json();
    document.getElementById("info-hostname").innerText = systemInfo.system.hostname;
    document.getElementById("info-ip").innerText = systemInfo.system.primary_ip;
    document.getElementById("info-mac").innerText = systemInfo.system.mac_address;
    document.getElementById("wol-guide-mac").innerText = systemInfo.system.mac_address;
    document.getElementById("wol-guide-ip").innerText = systemInfo.system.primary_ip;
  } catch (err) {
    console.error("Failed to fetch info:", err);
  }
}

// --- Touchpad Implementation ---
const touchpad = document.getElementById("touchpad");
let touchStartX = 0;
let touchStartY = 0;
let lastTouchX = 0;
let lastTouchY = 0;
let touchStartTime = 0;
let isMoving = false;
let touchesCount = 1;

touchpad.addEventListener("touchstart", (e) => {
  e.preventDefault();
  touchesCount = e.touches.length;
  touchStartTime = Date.now();
  isMoving = false;

  if (touchesCount === 1) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    lastTouchX = touchStartX;
    lastTouchY = touchStartY;
  } else if (touchesCount === 2) {
    lastTouchY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
  }
}, { passive: false });

touchpad.addEventListener("touchmove", (e) => {
  e.preventDefault();
  if (touchesCount === 1) {
    const currentX = e.touches[0].clientX;
    const currentY = e.touches[0].clientY;
    const dx = (currentX - lastTouchX) * 1.6;
    const dy = (currentY - lastTouchY) * 1.6;

    if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
      isMoving = true;
      sendInput({ type: "move", dx: dx, dy: dy });
    }
    lastTouchX = currentX;
    lastTouchY = currentY;
  } else if (touchesCount === 2) {
    const currentY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    const dy = currentY - lastTouchY;
    if (Math.abs(dy) > 2) {
      isMoving = true;
      sendInput({ type: "scroll", dy: dy > 0 ? 3 : -3 });
      lastTouchY = currentY;
    }
  }
}, { passive: false });

touchpad.addEventListener("touchend", (e) => {
  e.preventDefault();
  const touchDuration = Date.now() - touchStartTime;

  // Single finger tap -> left click
  if (!isMoving && touchDuration < 250 && touchesCount === 1) {
    sendInput({ type: "click", button: "left" });
    if (navigator.vibrate) navigator.vibrate(20);
  }
  // Two fingers tap -> right click
  else if (!isMoving && touchDuration < 250 && touchesCount === 2) {
    sendInput({ type: "click", button: "right" });
    if (navigator.vibrate) navigator.vibrate(35);
  }
}, { passive: false });

// Mouse Buttons
document.getElementById("btn-left-click").addEventListener("click", () => {
  sendInput({ type: "click", button: "left" });
  if (navigator.vibrate) navigator.vibrate(15);
});

document.getElementById("btn-right-click").addEventListener("click", () => {
  sendInput({ type: "click", button: "right" });
  if (navigator.vibrate) navigator.vibrate(25);
});

// Quick Keys
document.querySelectorAll(".key-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const key = btn.getAttribute("data-key");
    const hotkey = btn.getAttribute("data-hotkey");
    if (hotkey) {
      sendInput({ type: "hotkey", keys: hotkey.split("+") });
    } else if (key) {
      sendInput({ type: "key", key: key });
    }
    if (navigator.vibrate) navigator.vibrate(15);
  });
});

// Text Sender
document.getElementById("btn-send-text").addEventListener("click", sendTypedText);
document.getElementById("text-input").addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendTypedText();
});

function sendTypedText() {
  const input = document.getElementById("text-input");
  const text = input.value;
  if (text) {
    sendInput({ type: "type", text: text });
    input.value = "";
    if (navigator.vibrate) navigator.vibrate(20);
  }
}

// --- Live Screen Mirroring ---
const screenCanvas = document.getElementById("screen-canvas");
const screenCtx = screenCanvas.getContext("2d");
const screenImg = new Image();

function startScreenStream() {
  if (wsScreen && wsScreen.readyState === WebSocket.OPEN) return;
  const { wsBase } = getBaseUrls();
  wsScreen = new WebSocket(`${wsBase}/ws/screen`);
  wsScreen.binaryType = "blob";
  isScreenStreaming = true;

  wsScreen.onmessage = (event) => {
    if (!isScreenStreaming) return;
    const url = URL.createObjectURL(event.data);
    screenImg.onload = () => {
      screenCanvas.width = screenImg.width;
      screenCanvas.height = screenImg.height;
      screenCtx.drawImage(screenImg, 0, 0);
      URL.revokeObjectURL(url);
    };
    screenImg.src = url;
  };

  wsScreen.onclose = () => {
    if (isScreenStreaming) {
      setTimeout(startScreenStream, 1500);
    }
  };
}

function stopScreenStream() {
  isScreenStreaming = false;
  if (wsScreen) {
    wsScreen.close();
    wsScreen = null;
  }
}

// Tap directly on screen canvas to click that spot
screenCanvas.addEventListener("click", (e) => {
  const rect = screenCanvas.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top;
  const scaleX = screenCanvas.width / rect.width;
  const scaleY = screenCanvas.height / rect.height;
  const targetX = clickX * scaleX;
  const targetY = clickY * scaleY;

  // Calculate mouse delta from center to click coordinate
  if (systemInfo && systemInfo.screen) {
    const mappedX = (targetX / screenCanvas.width) * systemInfo.screen.width;
    const mappedY = (targetY / screenCanvas.height) * systemInfo.screen.height;
    // We send a direct click after calculating target
    sendInput({ type: "move", dx: 0, dy: 0 });
    sendInput({ type: "click", button: "left" });
    if (navigator.vibrate) navigator.vibrate(25);
  }
});

// --- Power & Unlock Actions ---
async function callPowerAPI(action, pin = null) {
  try {
    const { httpBase } = getBaseUrls();
    const res = await fetch(`${httpBase}/api/power`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action, pin: pin })
    });
    const data = await res.json();
    alert(data.message || "Action executed");
  } catch (err) {
    alert("Error executing command: " + err);
  }
}

document.getElementById("btn-lock").addEventListener("click", () => callPowerAPI("lock"));
document.getElementById("btn-wake-display").addEventListener("click", () => callPowerAPI("wake"));
document.getElementById("btn-sleep").addEventListener("click", () => {
  if (confirm("Put your laptop to sleep?")) callPowerAPI("sleep");
});
document.getElementById("btn-restart").addEventListener("click", () => {
  if (confirm("Restart your laptop?")) callPowerAPI("restart");
});
document.getElementById("btn-shutdown").addEventListener("click", () => {
  if (confirm("Shut down your laptop?")) callPowerAPI("shutdown");
});

// Unlock Modal & Execution
const unlockModal = document.getElementById("unlock-modal");
const pinInput = document.getElementById("pin-input");

document.getElementById("btn-unlock").addEventListener("click", async () => {
  // If system has saved pin, unlock immediately
  if (systemInfo && systemInfo.has_saved_unlock_pin) {
    callPowerAPI("unlock");
  } else {
    unlockModal.classList.add("active");
    pinInput.focus();
  }
});

document.getElementById("btn-modal-cancel").addEventListener("click", () => {
  unlockModal.classList.remove("active");
});

document.getElementById("btn-modal-unlock").addEventListener("click", () => {
  const pin = pinInput.value;
  if (pin) {
    callPowerAPI("unlock", pin);
    unlockModal.classList.remove("active");
    pinInput.value = "";
  }
});

// Save PIN in settings
document.getElementById("btn-save-pin").addEventListener("click", async () => {
  const savedPin = document.getElementById("settings-pin").value;
  if (!savedPin) return;
  try {
    const { httpBase } = getBaseUrls();
    await fetch(`${httpBase}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ windows_unlock_pin: savedPin })
    });
    alert("PIN saved! You can now unlock your laptop with one tap.");
    fetchSystemInfo();
  } catch (e) {
    alert("Failed to save PIN: " + e);
  }
});

// Wake-on-LAN Test Button
document.getElementById("btn-send-wol").addEventListener("click", async () => {
  try {
    const { httpBase } = getBaseUrls();
    const res = await fetch(`${httpBase}/api/wol/send`, { method: "POST" });
    const data = await res.json();
    alert(data.message || "WoL Packet Sent!");
  } catch (err) {
    alert("WoL Error: " + err);
  }
});

// --- Media & Volume Controls ---
async function callMediaAPI(action) {
  try {
    const { httpBase } = getBaseUrls();
    await fetch(`${httpBase}/api/media`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action })
    });
    if (navigator.vibrate) navigator.vibrate(15);
  } catch (err) {
    console.error(err);
  }
}

document.getElementById("media-play-pause").addEventListener("click", () => callMediaAPI("play_pause"));
document.getElementById("media-prev").addEventListener("click", () => callMediaAPI("prev"));
document.getElementById("media-next").addEventListener("click", () => callMediaAPI("next"));
document.getElementById("vol-up").addEventListener("click", () => callMediaAPI("vol_up"));
document.getElementById("vol-down").addEventListener("click", () => callMediaAPI("vol_down"));
document.getElementById("vol-mute").addEventListener("click", () => callMediaAPI("mute"));

// App Launcher
document.querySelectorAll(".app-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const app = btn.getAttribute("data-app");
    try {
      const { httpBase } = getBaseUrls();
      await fetch(`${httpBase}/api/apps/${app}`, { method: "POST" });
      if (navigator.vibrate) navigator.vibrate(20);
    } catch (err) {
      console.error(err);
    }
  });
});

// --- On Page Load ---
window.addEventListener("DOMContentLoaded", () => {
  const hostInput = document.getElementById("host-url-input");
  if (hostInput) {
    hostInput.value = localStorage.getItem("laptop_bridge_host") || "";
    document.getElementById("btn-save-host").addEventListener("click", () => {
      const val = hostInput.value.trim();
      if (val) {
        localStorage.setItem("laptop_bridge_host", val);
      } else {
        localStorage.removeItem("laptop_bridge_host");
      }
      alert("Target host updated! Reconnecting...");
      window.location.reload();
    });
  }

  connectInputWS();
  fetchSystemInfo();
});
