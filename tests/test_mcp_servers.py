import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_filesystem_server_file_exists():
    assert os.path.exists("mcp/servers/filesystem-server.ts"), \
        "filesystem-server.ts não encontrado"

def test_git_server_file_exists():
    assert os.path.exists("mcp/servers/git-server.ts"), \
        "git-server.ts não encontrado"

def test_mcp_manager_instantiation():
    from api.mcp_manager import MCPManager, MCPServer
    mgr = MCPManager()
    mgr.register(MCPServer(name="test", command="echo", args=["hello"]))
    assert "test" in mgr.servers
    assert not mgr.is_running("test")

def test_mcp_manager_default_workspace():
    from api.mcp_manager import MCPManager
    mgr = MCPManager.default_workspace_manager("/tmp/test")
    assert "filesystem" in mgr.servers
    assert "git" in mgr.servers

def test_filesystem_server_uses_relative_root_guard():
    source = open("mcp/servers/filesystem-server.ts", encoding="utf-8").read()
    assert "path.relative(ALLOWED_ROOT" in source
    assert "startsWith(ALLOWED_ROOT)" not in source
    assert "fs.realpathSync.native" in source
