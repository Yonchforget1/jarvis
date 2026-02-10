/**
 * JARVIS Desktop Application
 *
 * Electron wrapper for the Jarvis web UI at localhost:3000.
 * Features: system tray, window state persistence, auto-start with Windows.
 */

const { app, BrowserWindow, Tray, Menu, nativeImage, shell, dialog } = require("electron");
const path = require("path");
const { initTray } = require("./tray");

// Persistent settings
let store;
async function getStore() {
  if (!store) {
    const { default: Store } = await import("electron-store");
    store = new Store({
      defaults: {
        windowBounds: { width: 1280, height: 860, x: undefined, y: undefined },
        autoStart: false,
        minimizeToTray: true,
        startMinimized: false,
        serverUrl: "http://localhost:3000",
      },
    });
  }
  return store;
}

let mainWindow = null;
let tray = null;
let isQuitting = false;

const JARVIS_URL_DEFAULT = "http://localhost:3000";

function getServerUrl(settings) {
  return settings.get("serverUrl") || JARVIS_URL_DEFAULT;
}

async function createWindow() {
  const settings = await getStore();
  const bounds = settings.get("windowBounds");

  mainWindow = new BrowserWindow({
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    minWidth: 480,
    minHeight: 600,
    title: "JARVIS",
    icon: path.join(__dirname, "icons", "icon.png"),
    backgroundColor: "#1a1a2e",
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: true,
    },
  });

  // Save window bounds on resize/move
  const saveBounds = () => {
    if (mainWindow && !mainWindow.isMinimized() && !mainWindow.isMaximized()) {
      settings.set("windowBounds", mainWindow.getBounds());
    }
  };
  mainWindow.on("resize", saveBounds);
  mainWindow.on("move", saveBounds);

  // Show window when ready
  mainWindow.once("ready-to-show", () => {
    if (!settings.get("startMinimized")) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  // Minimize to tray instead of closing
  mainWindow.on("close", (event) => {
    if (!isQuitting && settings.get("minimizeToTray")) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http") && !url.includes("localhost")) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  // Handle navigation - keep in-app links in window
  mainWindow.webContents.on("will-navigate", (event, url) => {
    const serverUrl = getServerUrl(settings);
    if (!url.startsWith(serverUrl) && !url.startsWith("http://localhost")) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  // Load the Jarvis web UI
  const serverUrl = getServerUrl(settings);
  try {
    await mainWindow.loadURL(serverUrl);
  } catch {
    // Server not running yet - show retry page
    mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(getRetryHTML(serverUrl))}`);
    mainWindow.show();
  }
}

function getRetryHTML(serverUrl) {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>JARVIS - Connecting</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #0f0f1a; color: #e0e0e8;
    min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .container { text-align: center; padding: 2rem; max-width: 420px; }
  .logo { width: 72px; height: 72px; background: rgba(108, 58, 237, 0.2);
    border: 1px solid rgba(108, 58, 237, 0.15); border-radius: 18px;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 2rem; font-size: 28px; font-weight: 700; color: #6C3AED; }
  h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.75rem; }
  p { color: #888; font-size: 0.875rem; line-height: 1.6; margin-bottom: 1.5rem; }
  code { background: rgba(108, 58, 237, 0.15); color: #a78bfa; padding: 0.2rem 0.5rem;
    border-radius: 0.375rem; font-size: 0.8rem; }
  button { background: #6C3AED; color: white; border: none; padding: 0.75rem 2rem;
    border-radius: 0.75rem; font-size: 0.875rem; font-weight: 500; cursor: pointer;
    transition: opacity 0.2s; }
  button:hover { opacity: 0.85; }
  .spinner { width: 20px; height: 20px; border: 2px solid rgba(108, 58, 237, 0.3);
    border-top-color: #6C3AED; border-radius: 50%; animation: spin 1s linear infinite;
    margin: 1.5rem auto 0; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #status { font-size: 0.75rem; color: #666; margin-top: 1rem; }
</style></head><body>
<div class="container">
  <div class="logo">J</div>
  <h1>Connecting to JARVIS...</h1>
  <p>Waiting for the Jarvis web server at <code>${serverUrl}</code>. Make sure the server is running:</p>
  <p><code>cd web && npm run dev</code></p>
  <button onclick="location.reload()">Retry Now</button>
  <div class="spinner"></div>
  <div id="status">Auto-retrying every 3 seconds...</div>
</div>
<script>
  let attempts = 0;
  const check = async () => {
    attempts++;
    document.getElementById('status').textContent = 'Attempt ' + attempts + '...';
    try {
      const r = await fetch('${serverUrl}', { mode: 'no-cors' });
      location.href = '${serverUrl}';
    } catch { setTimeout(check, 3000); }
  };
  setTimeout(check, 3000);
</script></body></html>`;
}

// Auto-start with Windows
async function updateAutoStart() {
  const settings = await getStore();
  const enabled = settings.get("autoStart");
  app.setLoginItemSettings({
    openAtLogin: enabled,
    path: process.execPath,
    args: enabled ? ["--start-minimized"] : [],
  });
}

// Single instance lock
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

app.on("ready", async () => {
  const settings = await getStore();

  // Check for --start-minimized flag
  if (process.argv.includes("--start-minimized")) {
    settings.set("startMinimized", true);
  } else {
    settings.set("startMinimized", false);
  }

  await createWindow();

  // Create system tray
  tray = initTray({
    mainWindow,
    settings,
    isQuitting: () => isQuitting,
    setQuitting: (val) => { isQuitting = val; },
    updateAutoStart,
    getServerUrl: () => getServerUrl(settings),
    iconPath: path.join(__dirname, "icons", "icon.png"),
  });

  await updateAutoStart();
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  } else {
    mainWindow.show();
  }
});
