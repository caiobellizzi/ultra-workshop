import { useTheme } from "@/components/ThemeProvider";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="font-mono text-xs cursor-pointer bg-transparent border-none p-0 w-full text-left"
      style={{
        color: "var(--text-dim)",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--text-sm)",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text-muted)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-dim)"; }}
    >
      {theme === "dark" ? "◑ light mode" : "◑ dark mode"}
    </button>
  );
}
