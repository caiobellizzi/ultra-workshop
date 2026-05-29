import { Link } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Bell,
  Settings,
  Code2,
  DollarSign,
  HeartPulse,
  BookOpen,
  Rocket,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { hitl } from "@/lib/api";

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
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
    { to: "/board", label: "Live Board", icon: <LayoutDashboard className="h-5 w-5" /> },
    { to: "/hitl", label: "HITL Queue", icon: <Bell className="h-5 w-5" />, badge: hitlCount || undefined },
    { to: "/cost", label: "Cost", icon: <DollarSign className="h-5 w-5" /> },
    { to: "/health", label: "Health", icon: <HeartPulse className="h-5 w-5" /> },
    { to: "/skills", label: "Skills", icon: <Code2 className="h-5 w-5" /> },
    { to: "/config/models", label: "Config", icon: <Settings className="h-5 w-5" /> },
    { to: "/repos", label: "Repos", icon: <BookOpen className="h-5 w-5" /> },
    { to: "/launch", label: "Launch", icon: <Rocket className="h-5 w-5" /> },
  ];

  return (
    <aside className="flex h-full w-56 flex-col border-r bg-card">
      <div className="px-4 py-5 border-b">
        <h1 className="text-base font-bold tracking-tight">Ultra Workshop</h1>
        <p className="text-xs text-muted-foreground">Dashboard</p>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
              "[&.active]:bg-accent [&.active]:text-accent-foreground",
            )}
          >
            {item.icon}
            <span className="flex-1">{item.label}</span>
            {item.badge != null && item.badge > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-[10px] text-destructive-foreground font-bold">
                {item.badge > 9 ? "9+" : item.badge}
              </span>
            )}
          </Link>
        ))}
      </nav>

      <div className="border-t p-2">
        <button
          onClick={() => void logout()}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          <LogOut className="h-5 w-5" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
