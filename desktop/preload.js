/**
 * Preload script: exposes safe APIs to the renderer process.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jarvis", {
  // App info
  getVersion: () => ipcRenderer.invoke("get-version"),
  getPlatform: () => process.platform,

  // Window controls
  minimize: () => ipcRenderer.send("window-minimize"),
  maximize: () => ipcRenderer.send("window-maximize"),
  close: () => ipcRenderer.send("window-close"),

  // Settings
  getSetting: (key) => ipcRenderer.invoke("get-setting", key),
  setSetting: (key, value) => ipcRenderer.invoke("set-setting", key, value),

  // Navigation (from main process)
  onNavigate: (callback) => ipcRenderer.on("navigate", (_, path) => callback(path)),

  // Updates
  onUpdateAvailable: (callback) => ipcRenderer.on("update-available", (_, info) => callback(info)),
  onUpdateDownloaded: (callback) => ipcRenderer.on("update-downloaded", (_, info) => callback(info)),
  installUpdate: () => ipcRenderer.send("install-update"),

  // System
  openExternal: (url) => ipcRenderer.send("open-external", url),
});
