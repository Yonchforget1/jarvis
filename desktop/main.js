/**
 * Jarvis Desktop – Electron main process.
 *
 * Starts the FastAPI backend, then loads the web UI.
 */

const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const { setupTray } = require("./tray");
const { setupUpdater } = require("./updater");

const API_PORT = 3000;
const API_URL = `http://localhost:${API_PORT}`;
let mainWindow = null;
let backendProcess = null;

function startBackend() {
  const pythonCmd = process.platform === "win32" ? "python" : "python3";
  const apiDir = path.join(__dirname, "..");

  backendProcess = spawn(
    pythonCmd,
    ["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", String(API_PORT)],
    {
      cwd: apiDir,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    }
  );

  backendProcess.stdout.on("data", (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.on("exit", (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

async function waitForBackend(maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const { default: fetch } = await import("node-fetch").catch(() => {
        // Fallback to http module
        return { default: null };
      });
      if (fetch) {
        const res = await fetch(`${API_URL}/api/health`);
        if (res.ok) return true;
      } else {
        // Use built-in http
        const http = require("http");
        const ok = await new Promise((resolve) => {
          http
            .get(`${API_URL}/api/health`, (res) => resolve(res.statusCode === 200))
            .on("error", () => resolve(false));
        });
        if (ok) return true;
      }
    } catch {
      // ignore
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "Jarvis",
    backgroundColor: "#09090b",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(API_URL);

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(async () => {
  startBackend();
  const backendReady = await waitForBackend();

  if (!backendReady) {
    console.error("Backend failed to start within timeout");
  }

  createWindow();
  setupTray(mainWindow, () => createWindow());
  setupUpdater();
});

app.on("window-all-closed", () => {
  // Don't quit on macOS – stay in tray
  if (process.platform !== "darwin") {
    // Keep running in tray on all platforms
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
