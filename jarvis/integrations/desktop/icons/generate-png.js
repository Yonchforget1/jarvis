/**
 * Generate PNG icon from SVG for Electron.
 * Run: node icons/generate-png.js
 * Requires: npm install sharp (one-time)
 */

const fs = require("fs");
const path = require("path");

// Create a 256x256 PNG with the JARVIS "J" logo
// This is a simple canvas-based approach that works without sharp
const SIZE = 256;

// Generate ICO-compatible BMP data for Windows
// For now, we'll create a minimal valid PNG using raw Buffer manipulation

// Simple approach: write an HTML file that generates the icon
const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body>
<canvas id="c" width="${SIZE}" height="${SIZE}"></canvas>
<script>
const c = document.getElementById('c');
const ctx = c.getContext('2d');

// Background
const r = SIZE * 0.25;
ctx.beginPath();
ctx.roundRect(0, 0, SIZE, SIZE, r);
ctx.fillStyle = '#6C3AED';
ctx.fill();

// Letter J
ctx.fillStyle = 'white';
ctx.font = 'bold ${Math.round(SIZE * 0.625)}px system-ui, -apple-system, sans-serif';
ctx.textAlign = 'center';
ctx.textBaseline = 'middle';
ctx.fillText('J', SIZE/2, SIZE/2 + SIZE*0.04);

// Download as PNG
const link = document.createElement('a');
link.download = 'icon.png';
link.href = c.toDataURL('image/png');
link.click();
</script></body></html>`;

fs.writeFileSync(path.join(__dirname, "generate-icon.html"), html);
console.log("Open icons/generate-icon.html in a browser to download icon.png");
console.log("Then place icon.png in this icons/ directory.");
console.log("");
console.log("Alternatively, install sharp and run:");
console.log("  node -e \"require('sharp')('icon.svg').resize(256,256).png().toFile('icon.png')\"");
`;
