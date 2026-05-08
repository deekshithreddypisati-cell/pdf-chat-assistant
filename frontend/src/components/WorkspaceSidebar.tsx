import { useState } from "react";
import type { Workspace } from "../types";

interface Props {
  workspaces: Workspace[];
  selectedWorkspaceId: string | null;
  onSelectWorkspace: (id: string) => void;
  onCreateWorkspace: (name: string) => Promise<void>;
}

export default function WorkspaceSidebar({
  workspaces,
  selectedWorkspaceId,
  onSelectWorkspace,
  onCreateWorkspace,
}: Props) {
  const [newWorkspaceName, setNewWorkspaceName] = useState("");

  const handleCreate = async () => {
    if (!newWorkspaceName.trim()) return;

    await onCreateWorkspace(newWorkspaceName);
    setNewWorkspaceName("");
  };

  return (
    <div className="sidebar">
      <h2>Workspaces</h2>

      <div className="workspace-create">
        <input
          type="text"
          placeholder="New workspace"
          value={newWorkspaceName}
          onChange={(e) => setNewWorkspaceName(e.target.value)}
        />

        <button onClick={handleCreate}>
          Create
        </button>
      </div>

      <div className="workspace-list">
        {workspaces.map((ws) => (
          <button
            key={ws.id}
            className={
              selectedWorkspaceId === ws.id
                ? "workspace-item active"
                : "workspace-item"
            }
            onClick={() => onSelectWorkspace(ws.id)}
          >
            {ws.name}
          </button>
        ))}
      </div>
    </div>
  );
}