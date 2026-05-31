import { Outlet } from "@tanstack/react-router";
import { Sidebar } from "./Sidebar";
import { Toaster } from "@/components/ui/toaster";

export function AppShell() {
  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ backgroundColor: "var(--background)" }}
    >
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
}
