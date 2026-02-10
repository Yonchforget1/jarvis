/**
 * Auto-updater: checks GitHub Releases for new versions.
 *
 * Uses electron-updater with GitHub as the publish provider.
 * Updates are downloaded in the background and installed on restart.
 */

const { autoUpdater } = require("electron-updater");
const { dialog } = require("electron");

let mainWindow = null;

function setupAutoUpdater(win) {
  mainWindow = win;

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.logger = console;

  autoUpdater.on("checking-for-update", () => {
    console.log("[updater] Checking for updates...");
  });

  autoUpdater.on("update-available", (info) => {
    console.log("[updater] Update available:", info.version);
    if (mainWindow) {
      mainWindow.webContents.send("update-available", {
        version: info.version,
        releaseDate: info.releaseDate,
      });
    }
  });

  autoUpdater.on("update-not-available", () => {
    console.log("[updater] App is up to date.");
  });

  autoUpdater.on("download-progress", (progress) => {
    console.log(`[updater] Download: ${Math.round(progress.percent)}%`);
  });

  autoUpdater.on("update-downloaded", (info) => {
    console.log("[updater] Update downloaded:", info.version);
    if (mainWindow) {
      mainWindow.webContents.send("update-downloaded", {
        version: info.version,
      });
    }

    // Show dialog to user
    dialog
      .showMessageBox(mainWindow, {
        type: "info",
        title: "Update Ready",
        message: `Jarvis ${info.version} has been downloaded.`,
        detail: "Restart now to apply the update?",
        buttons: ["Restart Now", "Later"],
        defaultId: 0,
      })
      .then(({ response }) => {
        if (response === 0) {
          autoUpdater.quitAndInstall();
        }
      });
  });

  autoUpdater.on("error", (err) => {
    console.error("[updater] Error:", err.message);
  });

  // Check for updates after a short delay
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((err) => {
      console.log("[updater] Update check failed:", err.message);
    });
  }, 10000);

  // Check periodically (every 4 hours)
  setInterval(() => {
    autoUpdater.checkForUpdates().catch(() => {});
  }, 4 * 60 * 60 * 1000);
}

module.exports = { setupAutoUpdater };
