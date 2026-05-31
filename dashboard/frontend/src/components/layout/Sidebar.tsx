import { Link } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { hitl } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";

interface NavItem {
  to: string;
  label: string;
  badge?: number;
}

export function Sidebar() {
  const { logout } = useAuth();
  const { data: hitlData } = useQuery({
    queryKey: ["hitl"],
    queryFn: () => hitl.list(),
    refetchInterval: 10_000,
  });

  const hitlCount = hitlData?.items.length ?? 0;

  const navItems: NavItem[] = [
    { to: "/board", label: "Live Board" },
    { to: "/hitl", label: "HITL Queue", badge: hitlCount || undefined },
    { to: "/cost", label: "Cost" },
    { to: "/health", label: "Health" },
    { to: "/skills", label: "Skills" },
    { to: "/repos", label: "Repos" },
    { to: "/launch", label: "Launch" },
  ];

  const configItems: NavItem[] = [
    { to: "/config/models", label: "Models" },
    { to: "/config/reviewers", label: "Reviewers" },
    { to: "/config/policies", label: "Policies" },
  ];

  return (
    <aside
      className="flex flex-col border-r"
      style={{
        width: "160px",
        minWidth: "160px",
        height: "100%",
        backgroundColor: "var(--surface)",
        borderRight: "1px solid var(--border)",
        fontFamily: "var(--font-mono)",
      }}
    >
      {/* Brand */}
      <div style={{ padding: "16px 8px 16px 8px" }}>
        <span
          style={{
            color: "var(--accent)",
            fontWeight: "var(--font-bold)",
            letterSpacing: "var(--tracking-wide)",
            fontSize: "var(--text-sm)",
          }}
        >
          ◆ WORKSHOP
        </span>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto" style={{ paddingTop: "4px" }}>
        {navItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={cn("flex items-center")}
            activeProps={{
              style: {
                backgroundColor: "var(--accent-bg)",
                borderLeft: "2px solid var(--accent)",
                color: "var(--accent)",
              },
            }}
            inactiveProps={{
              style: {
                color: "var(--text-muted)",
                borderLeft: "2px solid transparent",
              },
            }}
            style={{
              display: "flex",
              alignItems: "center",
              height: "36px",
              padding: "0 8px",
              fontSize: "var(--text-base)",
              fontFamily: "var(--font-mono)",
              textDecoration: "none",
              width: "100%",
            }}
          >
            {({ isActive }) => (
              <>
                <span style={{ width: "14px", display: "inline-block", flexShrink: 0 }}>
                  {isActive ? "▶" : "○"}
                </span>
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.badge != null && item.badge > 0 && (
                  <span
                    style={{
                      backgroundColor: "var(--warning)",
                      color: "var(--background)",
                      fontSize: "var(--text-xs)",
                      borderRadius: "9999px",
                      minWidth: "18px",
                      height: "18px",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      padding: "0 4px",
                    }}
                  >
                    {item.badge > 9 ? "9+" : item.badge}
                  </span>
                )}
              </>
            )}
          </Link>
        ))}

        {/* Config section — always expanded */}
        <div style={{ marginTop: "8px" }}>
          <div
            style={{
              color: "var(--text-dim)",
              fontSize: "var(--text-xs)",
              letterSpacing: "var(--tracking-wide)",
              padding: "8px 8px 4px",
              textTransform: "uppercase",
            }}
          >
            Config
          </div>
          {configItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              activeProps={{
                style: {
                  backgroundColor: "var(--accent-bg)",
                  borderLeft: "2px solid var(--accent)",
                  color: "var(--accent)",
                },
              }}
              inactiveProps={{
                style: {
                  color: "var(--text-muted)",
                  borderLeft: "2px solid transparent",
                },
              }}
              style={{
                display: "flex",
                alignItems: "center",
                height: "36px",
                paddingLeft: "20px",
                paddingRight: "8px",
                fontSize: "var(--text-base)",
                fontFamily: "var(--font-mono)",
                textDecoration: "none",
                width: "100%",
              }}
            >
              {({ isActive }) => (
                <>
                  <span style={{ width: "14px", display: "inline-block", flexShrink: 0 }}>
                    {isActive ? "▶" : "○"}
                  </span>
                  <span>{item.label}</span>
                </>
              )}
            </Link>
          ))}
        </div>
      </nav>

      {/* Theme toggle */}
      <div style={{ borderTop: "1px solid var(--border)", padding: "8px" }}>
        <ThemeToggle />
      </div>

      {/* Logout */}
      <div style={{ padding: "0 8px 8px" }}>
        <button
          onClick={() => void logout()}
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-sm)",
            color: "var(--text-muted)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: "0",
            width: "100%",
            textAlign: "left",
            height: "28px",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; }}
        >
          → sign out
        </button>
      </div>
    </aside>
  );
}
