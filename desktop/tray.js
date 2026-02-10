/**
 * System tray integration for Jarvis Desktop.
 *
 * Features:
 * - Left-click toggles window visibility
 * - Right-click shows context menu with quick actions
 * - Auto-start toggle
 */

const { Tray, Menu, nativeImage } = require("electron");
const path = require("path");

let tray = null;

function createTray(mainWindow, store, app) {
  const iconPath = path.join(__dirname, "icons", "tray.png");
  let icon;
  try {
    icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) {
      // Fallback: create a simple 16x16 icon
      icon = nativeImage.createEmpty();
    }
  } catch {
    icon = nativeImage.createEmpty();
  }

  tray = new Tray(icon);
  tray.setToolTip("Jarvis AI Agent");

  const updateMenu = () => {
    const contextMenu = Menu.buildFromTemplate([
      {
        label: "Show Jarvis",
        click: () => {
          mainWindow.show();
          mainWindow.focus();
        },
      },
      { type: "separator" },
      {
        label: "New Chat",
        click: () => {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send("navigate", "/chat");
        },
      },
      {
        label: "Dashboard",
        click: () => {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send("navigate", "/dashboard");
        },
      },
      { type: "separator" },
      {
        label: "Start with Windows",
        type: "checkbox",
        checked: store.get("autoStart"),
        click: (item) => {
          store.set("autoStart", item.checked);
          app.setLoginItemSettings({
            openAtLogin: item.checked,
            path: app.getPath("exe"),
          });
        },
      },
      {
        label: "Start Minimized",
        type: "checkbox",
        checked: store.get("startMinimized"),
        click: (item) => {
          store.set("startMinimized", item.checked);
        },
      },
      { type: "separator" },
      {
        label: "Quit Jarvis",
        click: () => {
          app.isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);
  };

  updateMenu();

  // Toggle window on click
  tray.on("click", () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  return tray;
}

function destroyTray() {
  if (tray) {
    tray.destroy();
    tray = null;
  }
}

module.exports = { createTray, destroyTray };
