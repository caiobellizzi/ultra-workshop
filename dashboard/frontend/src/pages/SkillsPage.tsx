import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Loader2, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSkillList } from "@/hooks/useSkills";

export function SkillsPage() {
  const { data, isLoading } = useSkillList();
  const [search, setSearch] = useState("");

  const filtered = data?.skills.filter(
    (s) =>
      !search ||
      s.name.includes(search.toLowerCase()) ||
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
      <PageHeader title="Skills" description="SKILL.md editor" />
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="p-4 border-b">
          <div className="relative max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-8"
              placeholder="Search skills…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        {isLoading ? (
          <div className="flex flex-1 justify-center items-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <ScrollArea className="flex-1 p-4">
            {Object.entries(groups).map(([group, skills]) => (
              <div key={group} className="mb-6">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  {group}
                </h3>
                <div className="space-y-1">
                  {skills?.map((skill) => (
                    <Link
                      key={skill.name}
                      to="/skills/$skillName"
                      params={{ skillName: skill.name }}
                      className="flex items-start gap-3 rounded-md px-3 py-2 hover:bg-accent transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{skill.name}</span>
                          <Badge variant="outline" className="text-xs">v{skill.version}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground truncate">{skill.description}</p>
                      </div>
                    </Link>
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
