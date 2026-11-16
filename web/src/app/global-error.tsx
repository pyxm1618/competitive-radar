"use client";

// Last-resort boundary: replaces the root layout, so globals.css and the
// providers are unavailable. Styles are inline and mirror the light theme.

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "0 24px",
          background: "#f7f6f1",
          color: "#1c1b17",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif",
        }}
      >
        <p style={{ fontSize: 12, letterSpacing: "0.2em", textTransform: "uppercase", color: "#6b6a60" }}>
          Something broke
        </p>
        <h1 style={{ marginTop: 12, fontSize: 32, fontWeight: 600 }}>The whole page crashed.</h1>
        <p style={{ marginTop: 16, maxWidth: 420, color: "#6b6a60", lineHeight: 1.6 }}>
          Xiaoshuyin Competitive Radar hit an unexpected error. Reloading usually fixes it.
        </p>
        {error.digest && (
          <p style={{ marginTop: 8, fontFamily: "monospace", fontSize: 12, color: "#9b9a90" }}>
            ref {error.digest}
          </p>
        )}
        <button
          type="button"
          onClick={reset}
          style={{
            marginTop: 28,
            padding: "10px 20px",
            borderRadius: 10,
            border: "none",
            background: "#1c1b17",
            color: "#f7f6f1",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Reload
        </button>
      </body>
    </html>
  );
}
