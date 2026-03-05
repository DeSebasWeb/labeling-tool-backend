class WorkspaceNotFoundException(Exception):
    def __init__(self, workspace_id: str):
        super().__init__(f"Workspace no encontrado: '{workspace_id}'")
        self.workspace_id = workspace_id
