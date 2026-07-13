interface TabItem<T extends string> {
  id: T;
  label: string;
}

interface TabsProps<T extends string> {
  items: readonly TabItem<T>[];
  activeId: T;
  onChange: (id: T) => void;
}

export function Tabs<T extends string>({ items, activeId, onChange }: TabsProps<T>) {
  return (
    <div className="inline-flex rounded-md border border-slate-800 bg-slate-950 p-1" role="tablist">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={item.id === activeId}
          className={`min-h-8 rounded px-3 text-sm transition-colors ${
            item.id === activeId ? "bg-cyan-300 text-slate-950" : "text-slate-300 hover:bg-slate-900"
          }`}
          onClick={() => onChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
