/**
 * JARVIS Desktop Preload Script
 *
 * Exposes safe APIs to the renderer process via contextBridge.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("jarvisDesktop", {
  platform: process.platform,
  isDesktop: true,
  version: process.env.npm_package_version || "1.0.0",
});
