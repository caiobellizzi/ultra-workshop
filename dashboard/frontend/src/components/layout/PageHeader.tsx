interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div
      className="flex items-center justify-between px-6"
      style={{
        backgroundColor: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        height: "48px",
      }}
    >
      <div>
        <h2
          style={{
            fontFamily: "var(--font-mono)",
            fontWeight: "var(--font-bold)",
            color: "var(--text)",
            fontSize: "var(--text-lg)",
            letterSpacing: "var(--tracking-tight)",
            margin: 0,
          }}
        >
          {title}
        </h2>
        {description && (
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xs)",
              color: "var(--text-muted)",
              margin: 0,
            }}
          >
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
