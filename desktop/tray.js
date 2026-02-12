/**
 * System tray integration.
 */

const { app, Menu, Tray, nativeImage } = require("electron");
const path = require("path");

let tray = null;

function setupTray(mainWindow, createWindowFn) {
  // Use a simple 16x16 tray icon (or fallback to default)
  const iconPath = path.join(__dirname, "assets", "tray.png");
  let icon;
  try {
    icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) throw new Error("empty");
  } catch {
    // Create a simple colored icon as fallback
    icon = nativeImage.createFromBuffer(
      Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAKklEQVQ4T2P8z8BQz0BAwMjAwPAfhRkYGBj+MzAwIDMYGBgYkAUZKDIAAKWoBhFvbYZiAAAAAElFTkSuQmCC",
        "base64"
      )
    );
  }

  tray = new Tray(icon);
  tray.setToolTip("Jarvis AI Agent");

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Open Jarvis",
      click: () => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindowFn();
        }
      },
    },
    { type: "separator" },
    {
      label: "Start with Windows",
      type: "checkbox",
      checked: app.getLoginItemSettings().openAtLogin,
      click: (item) => {
        app.setLoginItemSettings({ openAtLogin: item.checked });
      },
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on("click", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.focus();
    } else {
      createWindowFn();
    }
  });
}

module.exports = { setupTray };
