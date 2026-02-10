/**
 * Jarvis WhatsApp Bridge
 *
 * Connects to WhatsApp Web via whatsapp-web.js, forwards messages to the
 * Jarvis FastAPI server, and sends responses back as WhatsApp replies.
 *
 * First run: displays a QR code in the terminal — scan it once with your phone.
 * After that, the session persists and reconnects automatically.
 *
 * Usage:
 *   node whatsapp_bridge.js                           (QR code auth)
 *   node whatsapp_bridge.js --phone 13478058362       (phone number pairing)
 *   node whatsapp_bridge.js --api http://localhost:8000
 */

const { Client, LocalAuth, MessageMedia } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const API_BASE = (() => {
  const eqArg = process.argv.find((a) => a.startsWith("--api="));
  if (eqArg) return eqArg.split("=")[1];
  const idx = process.argv.indexOf("--api");
  if (idx !== -1 && process.argv[idx + 1]) return process.argv[idx + 1];
  return "http://localhost:8000";
})();

const PAIR_PHONE = (() => {
  const eqArg = process.argv.find((a) => a.startsWith("--phone="));
  if (eqArg) return eqArg.split("=")[1];
  const idx = process.argv.indexOf("--phone");
  if (idx !== -1 && process.argv[idx + 1]) return process.argv[idx + 1];
  return null;
})();

const IMAGES_DIR = path.join(__dirname, "whatsapp_images");
if (!fs.existsSync(IMAGES_DIR)) fs.mkdirSync(IMAGES_DIR, { recursive: true });

// Per-phone session tracking (phone -> Jarvis session_id)
const sessions = {};

// ---------------------------------------------------------------------------
// HTTP helper (no external deps)
// ---------------------------------------------------------------------------
function apiPost(urlPath, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlPath, API_BASE);
    const payload = JSON.stringify(body);
    const mod = url.protocol === "https:" ? https : http;

    const req = mod.request(
      url,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(payload),
        },
        timeout: 120_000,
      },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          try {
            resolve({ status: res.statusCode, body: JSON.parse(data) });
          } catch {
            resolve({ status: res.statusCode, body: data });
          }
        });
      }
    );
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Request timeout"));
    });
    req.write(payload);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// WhatsApp Client
// ---------------------------------------------------------------------------
const clientOpts = {
  authStrategy: new LocalAuth({ dataPath: path.join(__dirname, ".wwebjs_auth") }),
  puppeteer: {
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
};

if (PAIR_PHONE) {
  clientOpts.pairWithPhoneNumber = {
    phoneNumber: PAIR_PHONE,
    showNotification: true,
  };
}

const client = new Client(clientOpts);

// --- Events ---------------------------------------------------------------

if (PAIR_PHONE) {
  client.on("code", (code) => {
    console.log("\n╔════════════════════════════════════════════╗");
    console.log("║  Enter this code in WhatsApp on your phone ║");
    console.log("║  Settings > Linked Devices > Link a Device ║");
    console.log("║  > Link with phone number                  ║");
    console.log("╚════════════════════════════════════════════╝\n");
    console.log(`  Pairing code:  ${code}\n`);
    console.log("Waiting for pairing...\n");
  });
} else {
  client.on("qr", (qr) => {
    console.log("\n╔════════════════════════════════════════════╗");
    console.log("║  Scan this QR code with WhatsApp on your  ║");
    console.log("║  phone to link Jarvis:                     ║");
    console.log("╚════════════════════════════════════════════╝\n");
    qrcode.generate(qr, { small: true });
    console.log("\nWaiting for scan...\n");
  });
}

client.on("authenticated", () => {
  console.log("[jarvis-wa] Authenticated successfully.");
});

client.on("auth_failure", (msg) => {
  console.error("[jarvis-wa] Authentication failed:", msg);
});

client.on("ready", () => {
  console.log("[jarvis-wa] WhatsApp client is ready!");
  console.log(`[jarvis-wa] Forwarding messages to ${API_BASE}`);
  console.log("[jarvis-wa] Send a WhatsApp message to start chatting with Jarvis.\n");
});

client.on("disconnected", (reason) => {
  console.warn("[jarvis-wa] Disconnected:", reason);
  console.log("[jarvis-wa] Attempting to reconnect in 5s...");
  setTimeout(() => client.initialize(), 5000);
});

// --- Message handling -----------------------------------------------------

client.on("message", async (msg) => {
  // Skip group messages, status updates, and self-sent messages
  if (msg.from.endsWith("@g.us")) return;
  if (msg.from === "status@broadcast") return;
  if (msg.fromMe) return;

  const phone = msg.from.replace("@c.us", "");
  const contact = await msg.getContact();
  const name = contact.pushname || contact.name || phone;

  console.log(`[jarvis-wa] Message from ${name} (${phone}): ${msg.body?.slice(0, 100) || "(media)"}`);

  try {
    let messageText = msg.body || "";

    // Handle image messages
    if (msg.hasMedia) {
      const media = await msg.downloadMedia();
      if (media && media.mimetype?.startsWith("image/")) {
        const ext = media.mimetype.split("/")[1] || "png";
        const filename = `wa_${phone}_${Date.now()}.${ext}`;
        const filepath = path.join(IMAGES_DIR, filename);
        fs.writeFileSync(filepath, Buffer.from(media.data, "base64"));
        console.log(`[jarvis-wa] Saved image: ${filepath}`);

        // OCR the image via Jarvis API
        const ocrResult = await apiPost("/api/whatsapp/ocr", {
          image_path: filepath,
        });

        const ocrText = ocrResult.body?.text || "(could not read image)";
        messageText = messageText
          ? `${messageText}\n\n[Image received - OCR text: ${ocrText}]`
          : `[Image received - OCR text: ${ocrText}]`;
      }
    }

    if (!messageText.trim()) {
      console.log("[jarvis-wa] Empty message, skipping.");
      return;
    }

    // Send to Jarvis
    const sessionId = sessions[phone] || null;
    const result = await apiPost("/api/whatsapp/bridge", {
      phone: phone,
      name: name,
      message: messageText,
      session_id: sessionId,
    });

    if (result.status === 200 && result.body?.response) {
      sessions[phone] = result.body.session_id || sessionId;
      const reply = result.body.response;

      // WhatsApp has a ~65000 char limit but keep it readable
      if (reply.length > 4000) {
        // Split into chunks
        const chunks = reply.match(/[\s\S]{1,4000}/g) || [reply];
        for (const chunk of chunks) {
          await msg.reply(chunk);
          await new Promise((r) => setTimeout(r, 500));
        }
      } else {
        await msg.reply(reply);
      }
      console.log(`[jarvis-wa] Replied to ${name}: ${reply.slice(0, 100)}...`);
    } else {
      console.error("[jarvis-wa] API error:", result.status, result.body);
      await msg.reply("Sorry, Jarvis encountered an error. Please try again.");
    }
  } catch (err) {
    console.error("[jarvis-wa] Error processing message:", err.message);
    await msg.reply("Sorry, Jarvis is temporarily unavailable. Please try again in a moment.");
  }
});

// --- Graceful shutdown ----------------------------------------------------

process.on("SIGINT", async () => {
  console.log("\n[jarvis-wa] Shutting down...");
  await client.destroy();
  process.exit(0);
});

process.on("SIGTERM", async () => {
  console.log("\n[jarvis-wa] Shutting down...");
  await client.destroy();
  process.exit(0);
});

// --- Start ----------------------------------------------------------------

console.log("[jarvis-wa] Jarvis WhatsApp Bridge starting...");
console.log(`[jarvis-wa] API endpoint: ${API_BASE}`);
console.log(`[jarvis-wa] Images dir: ${IMAGES_DIR}`);
client.initialize();
