/**
 * Jarvis AI Desktop Application
 *
 * Electron shell that:
 * 1. Starts the Python FastAPI backend
 * 2. Loads the web UI
 * 3. Provides system tray with quick access
 * 4. Supports auto-start on login
 * 5. Handles auto-updates from GitHub releases
 */

const { app, BrowserWindow, Menu, shell, dialog, nativeImage } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const Store = require("electron-store");

const { createTray, destroyTray } = require("./tray");
const { setupAutoUpdater } = require("./updater");

const store = new Store({
  defaults: {
    windowBounds: { width: 1200, height: 800 },
    startMinimized: false,
    autoStart: false,
    apiPort: 3000,
    theme: "dark",
  },
});

// --- Globals ---
let mainWindow = null;
let backendProcess = null;
const isDev = process.argv.includes("--dev");
const API_PORT = store.get("apiPort");
const API_URL = `http://localhost:${API_PORT}`;

// --- Single instance lock ---
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// --- Backend management ---

function findPython() {
  const candidates = ["python", "python3", "py"];
  for (const cmd of candidates) {
    try {
      const { execSync } = require("child_process");
      execSync(`${cmd} --version`, { stdio: "pipe" });
      return cmd;
    } catch {
      continue;
    }
  }
  return null;
}

function getProjectRoot() {
  if (isDev) {
    return path.join(__dirname, "..");
  }
  return path.join(process.resourcesPath);
}

function startBackend() {
  const python = findPython();
  if (!python) {
    dialog.showErrorBox(
      "Python Not Found",
      "Jarvis requires Python 3.10+ to be installed.\n\nPlease install Python from python.org and restart Jarvis."
    );
    app.quit();
    return;
  }

  const projectRoot = getProjectRoot();
  const args = [
    "-m", "uvicorn", "api.main:app",
    "--host", "127.0.0.1",
    "--port", String(API_PORT),
    "--log-level", "info",
  ];

  console.log(`[jarvis] Starting backend: ${python} ${args.join(" ")}`);
  console.log(`[jarvis] Working directory: ${projectRoot}`);

  backendProcess = spawn(python, args, {
    cwd: isDev ? path.join(__dirname, "..") : projectRoot,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    stdio: ["pipe", "pipe", "pipe"],
  });

  backendProcess.stdout.on("data", (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.on("exit", (code) => {
    console.log(`[jarvis] Backend exited with code ${code}`);
    if (code !== 0 && code !== null && mainWindow) {
      dialog.showErrorBox(
        "Backend Error",
        `The Jarvis backend stopped unexpectedly (exit code ${code}).\n\nPlease check the logs and restart.`
      );
    }
  });
}

function stopBackend() {
  if (backendProcess) {
    console.log("[jarvis] Stopping backend...");
    backendProcess.kill("SIGTERM");
    setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        backendProcess.kill("SIGKILL");
      }
    }, 5000);
    backendProcess = null;
  }
}

// --- Wait for backend to be ready ---

function waitForBackend(maxWaitMs = 30000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      http
        .get(`${API_URL}/api/health`, (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else {
            retry();
          }
        })
        .on("error", retry);
    };

    const retry = () => {
      if (Date.now() - start > maxWaitMs) {
        reject(new Error("Backend failed to start within timeout"));
      } else {
        setTimeout(check, 500);
      }
    };

    check();
  });
}

// --- Window creation ---

function createMainWindow() {
  const bounds = store.get("windowBounds");

  mainWindow = new BrowserWindow({
    width: bounds.width,
    height: bounds.height,
    minWidth: 800,
    minHeight: 600,
    title: "Jarvis AI",
    icon: path.join(__dirname, "icons", "icon.png"),
    backgroundColor: "#0a0a0f",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: true,
    },
  });

  // Remove default menu in production
  if (!isDev) {
    const template = [
      {
        label: "Jarvis",
        submenu: [
          { label: "About Jarvis", click: showAbout },
          { type: "separator" },
          { label: "Settings", accelerator: "CmdOrCtrl+,", click: () => mainWindow.webContents.send("navigate", "/settings") },
          { type: "separator" },
          { role: "quit" },
        ],
      },
      {
        label: "Edit",
        submenu: [
          { role: "undo" },
          { role: "redo" },
          { type: "separator" },
          { role: "cut" },
          { role: "copy" },
          { role: "paste" },
          { role: "selectAll" },
        ],
      },
      {
        label: "View",
        submenu: [
          { role: "reload" },
          { role: "forceReload" },
          { role: "toggleDevTools" },
          { type: "separator" },
          { role: "resetZoom" },
          { role: "zoomIn" },
          { role: "zoomOut" },
          { type: "separator" },
          { role: "togglefullscreen" },
        ],
      },
      {
        label: "Help",
        submenu: [
          { label: "Documentation", click: () => shell.openExternal("https://github.com/Yonchforget1/jarvis") },
          { label: "Report Issue", click: () => shell.openExternal("https://github.com/Yonchforget1/jarvis/issues") },
        ],
      },
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
  }

  // Save window size on resize
  mainWindow.on("resize", () => {
    const [width, height] = mainWindow.getSize();
    store.set("windowBounds", { width, height });
  });

  // Minimize to tray instead of closing
  mainWindow.on("close", (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  return mainWindow;
}

function showAbout() {
  dialog.showMessageBox(mainWindow, {
    type: "info",
    title: "About Jarvis AI",
    message: "Jarvis AI Agent Platform",
    detail: `Version: ${app.getVersion()}\nElectron: ${process.versions.electron}\nNode: ${process.versions.node}\n\nThe most advanced AI agent platform.\nBuilt by Crystal Clear Solutions LLC.`,
  });
}

// --- App lifecycle ---

app.on("ready", async () => {
  console.log("[jarvis] Jarvis Desktop starting...");

  // Start the Python backend
  startBackend();

  // Create main window
  const win = createMainWindow();

  // Create system tray
  createTray(win, store, app);

  // Wait for backend, then load the UI
  try {
    await waitForBackend();
    console.log("[jarvis] Backend is ready, loading UI...");
    win.loadURL(API_URL);
    win.once("ready-to-show", () => {
      if (!store.get("startMinimized")) {
        win.show();
      }
    });
  } catch (err) {
    console.error("[jarvis] Backend startup failed:", err.message);
    win.loadFile(path.join(__dirname, "error.html"));
    win.show();
  }

  // Setup auto-updater (production only)
  if (!isDev) {
    setupAutoUpdater(win);
  }
});

app.on("before-quit", () => {
  app.isQuitting = true;
  destroyTray();
  stopBackend();
});

app.on("window-all-closed", () => {
  // On macOS, keep app running in tray
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  // macOS dock click
  if (mainWindow) {
    mainWindow.show();
  }
});
