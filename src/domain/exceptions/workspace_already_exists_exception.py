class WorkspaceAlreadyExistsException(Exception):
    def __init__(self, container_name: str):
        super().__init__(f"Ya existe un workspace con el container '{container_name}'")
        self.container_name = container_name
