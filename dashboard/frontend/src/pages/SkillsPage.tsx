import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { PageHeader } from "@/components/layout/PageHeader";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSkillList } from "@/hooks/useSkills";

export function SkillsPage() {
  const { data, isLoading } = useSkillList();
  const [search, setSearch] = useState("");

  const filtered = data?.skills.filter(
    (s) =>
      !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase()),
  );

  // Group by first tag
  const groups: Record<string, typeof filtered> = {};
  filtered?.forEach((s) => {
    const group = s.tags[0] ?? "other";
    if (!groups[group]) groups[group] = [];
    groups[group]!.push(s);
  });

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Skills"
        description="SKILL.md registry & editor"
        actions={
          data?.skills.length ? (
            <span className="font-mono px-2 py-0.5 rounded-sm" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", backgroundColor: "var(--surface-raised)", border: "1px solid var(--border)" }}>
              {data.skills.length} skills
            </span>
          ) : undefined
        }
      />
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="p-4 border-b border-[--border]">
          <div className="relative max-w-sm">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[--text-d] text-xs pointer-events-none">
              ⌕
            </span>
            <Input
              className="pl-7 font-mono bg-[--surface-r] border-[--border-s] text-[--text] placeholder:text-[--text-d] text-xs rounded-sm focus:border-[--border-s] focus-visible:ring-0 focus-visible:ring-offset-0"
              placeholder="search skills…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        {isLoading ? (
          <div className="flex flex-1 justify-center items-center">
            <span className="text-[--text-d] font-mono text-xs animate-pulse">loading…</span>
          </div>
        ) : !filtered?.length ? (
          <div className="flex flex-1 justify-center items-center">
            <span className="text-[--text-d] font-mono text-sm">-- no skills found --</span>
          </div>
        ) : (
          <ScrollArea className="flex-1 p-6">
            {Object.entries(groups).map(([group, skills]) => (
              <div key={group} className="mb-8">
                <div className="text-[--text-d] text-xs font-mono uppercase tracking-[0.08em] mb-3">
                  {group}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {skills?.map((skill) => (
                    <div
                      key={skill.name}
                      className="bg-[--surface] border border-[--border] rounded-sm hover:border-[--border-s] p-4 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[--accent] font-mono font-medium text-sm">
                              {skill.name}
                            </span>
                            {skill.tags[0] && (
                              <span className="font-mono px-1.5 py-0.5 rounded-sm" style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", backgroundColor: "var(--surface-raised)", border: "1px solid var(--border)" }}>
                                {skill.tags[0]}
                              </span>
                            )}
                          </div>
                          <p className="text-[--text-m] font-mono text-xs truncate mb-2">
                            {skill.description}
                          </p>
                          <div className="flex items-center gap-4">
                            <span className="text-[--text-d] text-xs font-mono">
                              v{skill.version}
                            </span>
                            <span className="text-[--text-d] text-xs font-mono truncate max-w-[240px]">
                              {skill.path}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Button
                            asChild
                            variant="outline"
                            size="sm"
                            className="border-[--border-s] text-[--text-m] font-mono text-xs rounded-sm h-7 px-3 hover:border-[--border-s] hover:text-[--text] bg-transparent"
                          >
                            <Link
                              to="/skills/$skillName"
                              params={{ skillName: skill.name }}
                            >
                              View
                            </Link>
                          </Button>
                          <Button
                            asChild
                            variant="outline"
                            size="sm"
                            className="border-[--border-s] text-[--text-m] font-mono text-xs rounded-sm h-7 px-3 hover:border-[--border-s] hover:text-[--text] bg-transparent"
                          >
                            <Link
                              to="/skills/$skillName"
                              params={{ skillName: skill.name }}
                            >
                              Edit
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
