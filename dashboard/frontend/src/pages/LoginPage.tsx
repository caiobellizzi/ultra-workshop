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
      <div
        className="w-full p-8"
        style={{
          maxWidth: "24rem",
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)",
        }}
      >
        {/* Brand header */}
        <div
          className="font-mono font-bold tracking-widest text-xs mb-1"
          style={{ color: "var(--accent)", letterSpacing: "var(--tracking-wide)" }}
        >
          ◆ WORKSHOP
        </div>
        {/* Subtitle */}
        <div
          className="font-mono text-xs mb-6"
          style={{ color: "var(--text-dim)", fontSize: "var(--text-xs)" }}
        >
          Ultra Workshop Control Panel
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="password"
              className="block font-mono text-xs"
              style={{ color: "var(--text-dim)", fontSize: "var(--text-xs)" }}
            >
              PASSWORD
            </label>
            <input
              id="password"
              type="password"
              placeholder="enter access password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              className="w-full font-mono px-3 py-2 outline-none"
              style={{
                backgroundColor: "var(--surface-raised)",
                border: "1px solid var(--border-strong)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text)",
                fontSize: "var(--text-base)",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "var(--border-strong)";
              }}
            />
          </div>

          {error && (
            <p
              className="font-mono text-xs"
              style={{ color: "var(--danger)", fontSize: "var(--text-xs)" }}
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full font-mono font-bold text-xs py-2 px-3"
            style={{
              backgroundColor: loading ? "var(--accent-dim)" : "var(--accent)",
              color: "var(--background)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: "var(--text-xs)",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "SIGNING IN..." : "SIGN IN"}
          </button>
        </form>
      </div>
    </div>
  );
}
