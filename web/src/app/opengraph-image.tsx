import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "JARVIS AI Agent Platform - Deploy Your AI Workforce";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          width: "100%",
          height: "100%",
          background: "linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #0f0f23 100%)",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "32px",
          }}
        >
          <div
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "20px",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "36px",
              fontWeight: 800,
              color: "white",
            }}
          >
            J
          </div>
          <div
            style={{
              fontSize: "56px",
              fontWeight: 800,
              color: "white",
              letterSpacing: "-2px",
            }}
          >
            JARVIS
          </div>
        </div>
        <div
          style={{
            fontSize: "28px",
            fontWeight: 600,
            color: "#a5b4fc",
            marginBottom: "16px",
          }}
        >
          Deploy Your AI Workforce
        </div>
        <div
          style={{
            fontSize: "18px",
            color: "#94a3b8",
            maxWidth: "600px",
            textAlign: "center",
            lineHeight: 1.5,
          }}
        >
          16+ professional tools for filesystem, web, shell, game dev, and more
        </div>
        <div
          style={{
            display: "flex",
            gap: "12px",
            marginTop: "40px",
          }}
        >
          {["Claude", "OpenAI", "Gemini"].map((name) => (
            <div
              key={name}
              style={{
                padding: "8px 20px",
                borderRadius: "999px",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                color: "#c7d2fe",
                fontSize: "14px",
                fontWeight: 500,
              }}
            >
              {name}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
