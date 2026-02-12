/**
 * Preload script – exposes safe APIs to the renderer.
 */

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("jarvisDesktop", {
  platform: process.platform,
  version: require("./package.json").version,
});
