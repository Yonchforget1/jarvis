/**
 * JARVIS System Tray Module
 *
 * Provides tray icon with context menu for quick actions.
 */

const { Tray, Menu, nativeImage, app, shell } = require("electron");

function initTray({ mainWindow, settings, isQuitting, setQuitting, updateAutoStart, getServerUrl, iconPath }) {
  let trayIcon;
  try {
    trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
  } catch {
    // Fallback: create a simple colored icon
    trayIcon = nativeImage.createEmpty();
  }

  const tray = new Tray(trayIcon);
  tray.setToolTip("JARVIS AI Agent Platform");

  function buildMenu() {
    const autoStart = settings.get("autoStart");
    const minimizeToTray = settings.get("minimizeToTray");

    return Menu.buildFromTemplate([
      {
        label: "Open JARVIS",
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      {
        label: "Open in Browser",
        click: () => {
          shell.openExternal(getServerUrl());
        },
      },
      { type: "separator" },
      {
        label: "New Chat",
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
            mainWindow.loadURL(`${getServerUrl()}/chat`);
          }
        },
      },
      {
        label: "Dashboard",
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
            mainWindow.loadURL(`${getServerUrl()}/dashboard`);
          }
        },
      },
      { type: "separator" },
      {
        label: "Start with Windows",
        type: "checkbox",
        checked: autoStart,
        click: (item) => {
          settings.set("autoStart", item.checked);
          updateAutoStart();
          tray.setContextMenu(buildMenu());
        },
      },
      {
        label: "Minimize to Tray",
        type: "checkbox",
        checked: minimizeToTray,
        click: (item) => {
          settings.set("minimizeToTray", item.checked);
          tray.setContextMenu(buildMenu());
        },
      },
      { type: "separator" },
      {
        label: `JARVIS v${app.getVersion()}`,
        enabled: false,
      },
      {
        label: "Quit JARVIS",
        click: () => {
          setQuitting(true);
          app.quit();
        },
      },
    ]);
  }

  tray.setContextMenu(buildMenu());

  // Double-click to show window
  tray.on("double-click", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  return tray;
}

module.exports = { initTray };
