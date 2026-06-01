import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth";

export function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(password);
      await navigate({ to: "/board" });
    } catch {
      setError("Invalid password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ backgroundColor: "var(--background)" }}
    >
      <div className="flex flex-col items-center w-full" style={{ maxWidth: "360px", padding: 24 }}>
        <div
          className="w-full"
          style={{
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "32px 28px 28px",
          }}
        >
          {/* Brand header — centered */}
          <div className="text-center" style={{ marginBottom: 28 }}>
            <div
              className="font-mono font-bold"
              style={{ color: "var(--accent)", fontSize: "18px", letterSpacing: "0.08em", marginBottom: 6 }}
            >
              ◆ WORKSHOP
            </div>
            <div
              className="font-mono"
              style={{ color: "var(--text-dim)", fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
            >
              Ultra Workshop Control Panel
            </div>
          </div>

          <hr style={{ border: "none", borderTop: "1px solid var(--border)", marginBottom: 24 }} />

          <form onSubmit={(e) => void handleSubmit(e)}>
            <div style={{ marginBottom: 20 }}>
              <label
                htmlFor="password"
                className="block font-mono"
                style={{ color: "var(--text-muted)", fontSize: "var(--text-xs)", marginBottom: 4 }}
              >
                Access token
              </label>
              <input
                id="password"
                type="password"
                placeholder="sk-workshop-••••••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
                autoComplete="current-password"
                className="w-full font-mono outline-none"
                style={{
                  backgroundColor: "var(--surface-raised)",
                  border: "1px solid var(--border-strong)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text)",
                  fontSize: "var(--text-sm)",
                  padding: "7px 10px",
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-border)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border-strong)"; }}
              />
            </div>

            {error && (
              <p className="font-mono" style={{ color: "var(--danger)", fontSize: "var(--text-xs)", marginBottom: 16 }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full font-mono font-bold"
              style={{
                backgroundColor: loading ? "var(--accent-dim)" : "var(--accent)",
                color: "var(--background)",
                border: "1px solid var(--accent)",
                borderRadius: "var(--radius-sm)",
                fontSize: "var(--text-sm)",
                padding: "9px 14px",
                letterSpacing: "0.04em",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "SIGNING IN…" : "Login"}
            </button>
          </form>
        </div>

        <div
          className="font-mono text-center"
          style={{ marginTop: 20, fontSize: "var(--text-xs)", color: "var(--text-dim)", letterSpacing: "0.04em" }}
        >
          ultra-workshop &nbsp;·&nbsp; v0.1.0
        </div>
      </div>
    </div>
  );
}
