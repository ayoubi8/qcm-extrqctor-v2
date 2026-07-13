import { FolderPlus, Upload } from "lucide-react";
import { useState } from "react";
import { Button, Card, TextInput } from "../components/ui";
import type { ProjectDraft } from "./types";

interface ProjectLauncherProps {
  onCreate: (draft: ProjectDraft) => void;
}

export function ProjectLauncher({ onCreate }: ProjectLauncherProps) {
  const [name, setName] = useState("Untitled QCM project");
  const [file, setFile] = useState<File | null>(null);

  return (
    <Card title="New project">
      <div className="grid gap-4">
        <TextInput label="Project name" value={name} onChange={(event) => setName(event.target.value)} />
        <label className="grid gap-2 text-sm text-slate-300">
          <span>Source PDF</span>
          <input
            type="file"
            accept="application/pdf"
            className="min-h-10 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <Button
          variant="primary"
          icon={file ? <Upload className="h-4 w-4" aria-hidden="true" /> : <FolderPlus className="h-4 w-4" aria-hidden="true" />}
          onClick={() => onCreate({ name, file })}
        >
          Create project
        </Button>
      </div>
    </Card>
  );
}
