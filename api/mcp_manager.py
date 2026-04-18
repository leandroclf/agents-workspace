import subprocess
import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MCPServer:
    name: str
    command: str
    args: list[str]
    env: dict = None
    process: Optional[subprocess.Popen] = None


class MCPManager:
    def __init__(self):
        self.servers: dict[str, MCPServer] = {}

    def register(self, server: MCPServer):
        self.servers[server.name] = server

    def start(self, name: str):
        server = self.servers[name]
        env = {**os.environ, **(server.env or {})}
        server.process = subprocess.Popen(
            [server.command] + server.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )

    def stop(self, name: str):
        server = self.servers[name]
        if server.process:
            server.process.terminate()
            server.process.wait()
            server.process = None

    def start_all(self):
        for name in self.servers:
            self.start(name)

    def stop_all(self):
        for name in self.servers:
            self.stop(name)

    def is_running(self, name: str) -> bool:
        s = self.servers.get(name)
        return s is not None and s.process is not None and s.process.poll() is None

    @staticmethod
    def default_workspace_manager(workspace_root: str) -> "MCPManager":
        mgr = MCPManager()
        mgr.register(MCPServer(
            name="filesystem",
            command="node",
            args=["dist/mcp/servers/filesystem-server.js"],
            env={"WORKSPACE_ROOT": workspace_root},
        ))
        mgr.register(MCPServer(
            name="git",
            command="node",
            args=["dist/mcp/servers/git-server.js"],
        ))
        return mgr
