/**
 * Jarvis WhatsApp Bridge
 *
 * Connects to WhatsApp Web via whatsapp-web.js and forwards messages to
 * either Claude Code CLI (default) or the Jarvis FastAPI server (legacy).
 *
 * Claude Code mode: messages invoke `claude -p` with per-phone session
 * persistence. Images are OCR'd locally via Tesseract.
 *
 * Jarvis API mode: original behavior, forwards to POST /api/whatsapp/bridge.
 *
 * Usage:
 *   node whatsapp_bridge.js --phone 13478058362               (Claude Code, default)
 *   node whatsapp_bridge.js --phone 13478058362 --jarvis-api  (legacy API mode)
 *   node whatsapp_bridge.js --api http://localhost:8000 --jarvis-api
 */

const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");
const { execFile, spawn } = require("child_process");
const { randomUUID } = require("crypto");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const API_BASE = (() => {
  const eqArg = process.argv.find((a) => a.startsWith("--api="));
  if (eqArg) return eqArg.split("=")[1];
  const idx = process.argv.indexOf("--api");
  if (idx !== -1 && process.argv[idx + 1]) return process.argv[idx + 1];
  return "http://localhost:3000";
})();

const PAIR_PHONE = (() => {
  const eqArg = process.argv.find((a) => a.startsWith("--phone="));
  if (eqArg) return eqArg.split("=")[1];
  const idx = process.argv.indexOf("--phone");
  if (idx !== -1 && process.argv[idx + 1]) return process.argv[idx + 1];
  return null;
})();

// Mode: "claude-code" (default) or "jarvis-api" (legacy)
const MODE = process.argv.includes("--jarvis-api") ? "jarvis-api" : "claude-code";

// Working directory for Claude Code (defaults to project root)
const WORK_DIR = (() => {
  const eqArg = process.argv.find((a) => a.startsWith("--work-dir="));
  if (eqArg) return eqArg.split("=")[1];
  const idx = process.argv.indexOf("--work-dir");
  if (idx !== -1 && process.argv[idx + 1]) return process.argv[idx + 1];
  return path.resolve(__dirname, "..", "..");
})();

// Tesseract OCR path
const TESSERACT_PATH = String.raw`C:\Program Files\Tesseract-OCR\tesseract.exe`;

// Claude Code timeout: 10 minutes (can run tests, edit files, etc.)
const CLAUDE_TIMEOUT = 10 * 60 * 1000;

const IMAGES_DIR = path.join(__dirname, "whatsapp_images");
if (!fs.existsSync(IMAGES_DIR)) fs.mkdirSync(IMAGES_DIR, { recursive: true });

// ---------------------------------------------------------------------------
// Session management
// ---------------------------------------------------------------------------
const SESSIONS_FILE = path.join(__dirname, "whatsapp_sessions.json");

// sessions[phone] = { sessionId, initialized } (claude-code) or string (jarvis-api)
const sessions = {};

function loadSessions() {
  try {
    if (fs.existsSync(SESSIONS_FILE)) {
      const data = JSON.parse(fs.readFileSync(SESSIONS_FILE, "utf8"));
      Object.assign(sessions, data);
      console.log(`[jarvis-wa] Loaded ${Object.keys(data).length} saved session(s).`);
    }
  } catch (err) {
    console.warn("[jarvis-wa] Could not load sessions:", err.message);
  }
}

function saveSessions() {
  try {
    fs.writeFileSync(SESSIONS_FILE, JSON.stringify(sessions, null, 2));
  } catch (err) {
    console.warn("[jarvis-wa] Could not save sessions:", err.message);
  }
}

let saveTimer = null;
function debouncedSave() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(saveSessions, 2000);
}

function getOrCreateSession(phone) {
  if (MODE === "claude-code") {
    if (!sessions[phone] || !sessions[phone].sessionId) {
      sessions[phone] = { sessionId: randomUUID(), initialized: false };
    }
    return sessions[phone];
  }
  return sessions[phone] || null;
}

loadSessions();

// ---------------------------------------------------------------------------
// HTTP helper (for legacy Jarvis API mode)
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
// Local Tesseract OCR (no API dependency)
// ---------------------------------------------------------------------------
function ocrImage(imagePath) {
  return new Promise((resolve) => {
    execFile(
      TESSERACT_PATH,
      [imagePath, "stdout"],
      { timeout: 30_000 },
      (err, stdout) => {
        if (err) {
          console.error("[jarvis-wa] Tesseract error:", err.message);
          resolve("(could not read image)");
          return;
        }
        const text = stdout.trim();
        console.log(`[jarvis-wa] OCR result (${text.length} chars): ${text.slice(0, 100)}`);
        resolve(text || "(no text detected in image)");
      }
    );
  });
}

// ---------------------------------------------------------------------------
// Claude Code CLI invocation
// ---------------------------------------------------------------------------
function invokeClaudeCode(message, phone, name) {
  return new Promise((resolve, reject) => {
    const session = getOrCreateSession(phone);

    const args = ["-p", "--output-format", "json"];

    // First message: create session; subsequent: resume
    if (!session.initialized) {
      args.push("--session-id", session.sessionId);
    } else {
      args.push("-r", session.sessionId);
    }

    // WhatsApp context so Claude keeps responses mobile-friendly
    args.push(
      "--append-system-prompt",
      `The user is messaging from WhatsApp (phone: ${phone}, name: ${name}). ` +
        `Keep responses concise and mobile-friendly. ` +
        `Avoid large code blocks unless specifically requested. ` +
        `Use plain text formatting since WhatsApp has limited markdown support.`
    );

    // For long messages, pipe via stdin; otherwise pass as argument
    const useStdin = message.length > 7000;
    if (!useStdin) {
      args.push(message);
    }

    const child = spawn("claude", args, {
      cwd: WORK_DIR,
      shell: true,
      timeout: CLAUDE_TIMEOUT,
      env: { ...process.env },
      windowsHide: true,
    });

    if (useStdin) {
      child.stdin.write(message);
      child.stdin.end();
    }

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });
    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    child.on("error", (err) => {
      reject(new Error(`Claude Code spawn error: ${err.message}`));
    });

    child.on("close", (code) => {
      if (code !== 0) {
        console.error(`[jarvis-wa] Claude Code exited with code ${code}`);
        console.error(`[jarvis-wa] stderr: ${stderr.slice(0, 500)}`);
        reject(
          new Error(`Claude Code error (exit ${code}): ${stderr.slice(0, 200) || "unknown"}`)
        );
        return;
      }

      try {
        const result = JSON.parse(stdout);
        session.initialized = true;
        if (result.session_id) {
          session.sessionId = result.session_id;
        }

        resolve({
          response: result.result || "(no response)",
          sessionId: result.session_id,
          cost: result.total_cost_usd || 0,
          isError: result.is_error || false,
        });
      } catch (parseErr) {
        console.error("[jarvis-wa] Failed to parse Claude output:", parseErr.message);
        resolve({
          response: stdout.trim() || "(empty response)",
          sessionId: session.sessionId,
          cost: 0,
          isError: true,
        });
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Response chunking
// ---------------------------------------------------------------------------
function smartChunk(text, maxLen) {
  const chunks = [];
  let remaining = text;

  while (remaining.length > maxLen) {
    // Try paragraph break, then line break, then space, then hard split
    let splitIdx = remaining.lastIndexOf("\n\n", maxLen);
    if (splitIdx < maxLen * 0.5) splitIdx = remaining.lastIndexOf("\n", maxLen);
    if (splitIdx < maxLen * 0.3) splitIdx = remaining.lastIndexOf(" ", maxLen);
    if (splitIdx < maxLen * 0.2) splitIdx = maxLen;

    chunks.push(remaining.slice(0, splitIdx).trimEnd());
    remaining = remaining.slice(splitIdx).trimStart();
  }

  if (remaining.trim()) chunks.push(remaining.trim());
  return chunks;
}

async function sendChunkedReply(msg, text) {
  if (text.length > 65000) {
    text = text.slice(0, 64900) + "\n\n... (response truncated, too long for WhatsApp)";
  }

  if (text.length > 4000) {
    const chunks = smartChunk(text, 4000);
    for (let i = 0; i < chunks.length; i++) {
      const prefix = chunks.length > 1 ? `(${i + 1}/${chunks.length}) ` : "";
      const sent = await msg.reply(prefix + chunks[i]);
      if (sent?.id?._serialized) bridgeSentIds.add(sent.id._serialized);
      await new Promise((r) => setTimeout(r, 500));
    }
  } else {
    const sent = await msg.reply(text);
    if (sent?.id?._serialized) bridgeSentIds.add(sent.id._serialized);
  }
}

// ---------------------------------------------------------------------------
// Bridge commands (intercepted, not sent to Claude)
// ---------------------------------------------------------------------------
async function trackReply(msg, text) {
  const sent = await msg.reply(text);
  if (sent?.id?._serialized) bridgeSentIds.add(sent.id._serialized);
  return sent;
}

const BRIDGE_COMMANDS = {
  "!reset": async (msg, phone) => {
    delete sessions[phone];
    debouncedSave();
    await trackReply(msg, "Session reset. Starting fresh conversation.");
  },
  "!status": async (msg, phone) => {
    const session = sessions[phone];
    const info = [
      `Mode: ${MODE}`,
      `Session: ${session?.sessionId || "none"}`,
      `Initialized: ${session?.initialized || false}`,
      `Working dir: ${WORK_DIR}`,
    ];
    await trackReply(msg, `Bridge status:\n${info.join("\n")}`);
  },
  "!help": async (msg) => {
    await trackReply(
      msg,
      "Commands:\n" +
        "!reset - Start a new conversation\n" +
        "!status - Show bridge status\n" +
        "!help - Show this help\n\n" +
        "Everything else is sent to Claude Code."
    );
  },
};

// ---------------------------------------------------------------------------
// Message handlers
// ---------------------------------------------------------------------------
const busyPhones = new Set();
// Track message IDs sent by the bridge to avoid infinite loops with self-chat
const bridgeSentIds = new Set();
// Periodically clean up old IDs (keep set from growing forever)
setInterval(() => {
  if (bridgeSentIds.size > 500) {
    const excess = bridgeSentIds.size - 200;
    const iter = bridgeSentIds.values();
    for (let i = 0; i < excess; i++) bridgeSentIds.delete(iter.next().value);
  }
}, 60_000);

async function handleClaudeCodeMessage(msg, phone, name, messageText) {
  if (busyPhones.has(phone)) {
    await trackReply(msg, "Still working on your previous request... please wait.");
    return;
  }

  busyPhones.add(phone);
  try {
    // Typing indicator
    const chat = await msg.getChat();
    chat.sendStateTyping();

    console.log(
      `[jarvis-wa] Sending to Claude Code (session: ${getOrCreateSession(phone).sessionId})`
    );
    const result = await invokeClaudeCode(messageText, phone, name);

    if (result.cost > 0) {
      console.log(`[jarvis-wa] Claude Code cost: $${result.cost.toFixed(4)}`);
    }

    await sendChunkedReply(msg, result.response);
    console.log(`[jarvis-wa] Replied to ${name}: ${result.response.slice(0, 100)}...`);
    debouncedSave();
  } finally {
    busyPhones.delete(phone);
    try {
      const chat = await msg.getChat();
      chat.clearState();
    } catch {
      /* ignore */
    }
  }
}

async function handleJarvisApiMessage(msg, phone, name, messageText) {
  const sessionId = sessions[phone] || null;
  const result = await apiPost("/api/whatsapp/bridge", {
    phone,
    name,
    message: messageText,
    session_id: sessionId,
  });

  if (result.status === 200 && result.body?.response) {
    sessions[phone] = result.body.session_id || sessionId;
    await sendChunkedReply(msg, result.body.response);
    console.log(`[jarvis-wa] Replied to ${name}: ${result.body.response.slice(0, 100)}...`);
    debouncedSave();
  } else {
    console.error("[jarvis-wa] API error:", result.status, result.body);
    await msg.reply("Sorry, Jarvis encountered an error. Please try again.");
  }
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
  if (MODE === "claude-code") {
    console.log("[jarvis-wa] Mode: Claude Code CLI");
    console.log(`[jarvis-wa] Working directory: ${WORK_DIR}`);
  } else {
    console.log(`[jarvis-wa] Mode: Jarvis API (${API_BASE})`);
  }
  console.log("[jarvis-wa] Send a WhatsApp message to start.\n");
});

client.on("disconnected", (reason) => {
  console.warn("[jarvis-wa] Disconnected:", reason);
  console.log("[jarvis-wa] Attempting to reconnect in 5s...");
  setTimeout(() => client.initialize(), 5000);
});

// --- Message handling -----------------------------------------------------

client.on("message_create", async (msg) => {
  // Log EVERY message for debugging
  const msgId = msg.id?._serialized || "unknown";
  console.log(
    `[jarvis-wa] RAW MSG | from=${msg.from} | fromMe=${msg.fromMe} | ` +
      `type=${msg.type} | id=${msgId} | body=${(msg.body || "").slice(0, 80)}`
  );

  // Skip group messages and status updates
  if (msg.from?.endsWith("@g.us") || msg.to?.endsWith("@g.us")) return;
  if (msg.from === "status@broadcast") return;

  // Skip messages the bridge itself sent (prevent infinite loop)
  if (bridgeSentIds.has(msgId)) {
    console.log("[jarvis-wa] Skipping bridge-sent message.");
    return;
  }

  // For self-chat (Message yourself): msg.fromMe is true for both user AND bridge
  // We allow fromMe messages but skip if the bridge is currently busy with this phone
  // (the busyPhones guard in handleClaudeCodeMessage handles this)

  // For non-self chats, skip fromMe (those are our own replies)
  const selfChat = msg.from === msg.to;
  if (msg.fromMe && !selfChat) return;

  const phone = (msg.from || msg.to || "").replace("@c.us", "");
  if (!phone) return;

  let name = phone;
  try {
    const contact = await msg.getContact();
    name = contact.pushname || contact.name || phone;
  } catch {
    /* use phone as name */
  }

  console.log(
    `[jarvis-wa] Processing message from ${name} (${phone}): ${msg.body?.slice(0, 100) || "(media)"}`
  );

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

        let ocrText;
        if (MODE === "claude-code") {
          ocrText = await ocrImage(filepath);
        } else {
          const ocrResult = await apiPost("/api/whatsapp/ocr", { image_path: filepath });
          ocrText = ocrResult.body?.text || "(could not read image)";
        }

        messageText = messageText
          ? `${messageText}\n\n[Image received - OCR text: ${ocrText}]`
          : `[Image received - OCR text: ${ocrText}]`;
      }
    }

    if (!messageText.trim()) {
      console.log("[jarvis-wa] Empty message, skipping.");
      return;
    }

    // Check for bridge commands
    const cmd = messageText.trim().toLowerCase();
    if (BRIDGE_COMMANDS[cmd]) {
      await BRIDGE_COMMANDS[cmd](msg, phone);
      return;
    }

    // Route to appropriate backend
    if (MODE === "claude-code") {
      await handleClaudeCodeMessage(msg, phone, name, messageText);
    } else {
      await handleJarvisApiMessage(msg, phone, name, messageText);
    }
  } catch (err) {
    console.error("[jarvis-wa] Error processing message:", err.message);
    await msg.reply("Sorry, an error occurred. Please try again in a moment.");
  }
});

// --- Graceful shutdown ----------------------------------------------------

async function shutdown() {
  console.log("\n[jarvis-wa] Shutting down...");
  saveSessions();
  await client.destroy();
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

// --- Start ----------------------------------------------------------------

console.log("[jarvis-wa] Jarvis WhatsApp Bridge starting...");
console.log(`[jarvis-wa] Mode: ${MODE}`);
if (MODE === "jarvis-api") {
  console.log(`[jarvis-wa] API endpoint: ${API_BASE}`);
} else {
  console.log(`[jarvis-wa] Working directory: ${WORK_DIR}`);
}
console.log(`[jarvis-wa] Images dir: ${IMAGES_DIR}`);
client.initialize();
