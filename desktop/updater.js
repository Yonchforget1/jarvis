/**
 * Auto-updater – checks GitHub Releases for new versions.
 */

const { dialog } = require("electron");

function setupUpdater() {
  try {
    const { autoUpdater } = require("electron-updater");

    autoUpdater.autoDownload = false;

    autoUpdater.on("update-available", (info) => {
      dialog
        .showMessageBox({
          type: "info",
          title: "Update Available",
          message: `Jarvis v${info.version} is available. Download now?`,
          buttons: ["Download", "Later"],
        })
        .then((result) => {
          if (result.response === 0) {
            autoUpdater.downloadUpdate();
          }
        });
    });

    autoUpdater.on("update-downloaded", () => {
      dialog
        .showMessageBox({
          type: "info",
          title: "Update Ready",
          message: "Update downloaded. Restart now to install?",
          buttons: ["Restart", "Later"],
        })
        .then((result) => {
          if (result.response === 0) {
            autoUpdater.quitAndInstall();
          }
        });
    });

    autoUpdater.on("error", (err) => {
      console.error("Auto-updater error:", err.message);
    });

    // Check for updates on startup (after 10s delay)
    setTimeout(() => {
      autoUpdater.checkForUpdates().catch(() => {});
    }, 10000);
  } catch (err) {
    console.log("Auto-updater not available:", err.message);
  }
}

module.exports = { setupUpdater };
