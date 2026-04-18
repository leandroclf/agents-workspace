import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { execSync } from "child_process";

const server = new Server(
  { name: "git-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

function git(cmd: string, cwd: string = process.cwd()): string {
  return execSync(`git ${cmd}`, { cwd, encoding: "utf-8" });
}

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "git_status",
      description: "Status do repositório git",
      inputSchema: {
        type: "object",
        properties: { repo_path: { type: "string", default: "." } },
      },
    },
    {
      name: "git_log",
      description: "Histórico de commits",
      inputSchema: {
        type: "object",
        properties: {
          repo_path: { type: "string", default: "." },
          limit: { type: "number", default: 10 },
        },
      },
    },
    {
      name: "git_diff",
      description: "Diff de arquivos modificados",
      inputSchema: {
        type: "object",
        properties: {
          repo_path: { type: "string", default: "." },
          file: { type: "string" },
        },
      },
    },
    {
      name: "git_branches",
      description: "Listar branches",
      inputSchema: {
        type: "object",
        properties: { repo_path: { type: "string", default: "." } },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const repoPath = (args?.repo_path as string) || ".";

  try {
    switch (name) {
      case "git_status":
        return { content: [{ type: "text", text: git("status", repoPath) }] };
      case "git_log": {
        const limit = (args?.limit as number) || 10;
        const log = git(`log --oneline -${limit}`, repoPath);
        return { content: [{ type: "text", text: log }] };
      }
      case "git_diff": {
        const file = args?.file as string | undefined;
        const diff = git(file ? `diff -- ${file}` : "diff", repoPath);
        return { content: [{ type: "text", text: diff || "Sem alterações" }] };
      }
      case "git_branches":
        return { content: [{ type: "text", text: git("branch -a", repoPath) }] };
      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}`, isError: true }] };
    }
  } catch (err: any) {
    return { content: [{ type: "text", text: `Git error: ${err.message}`, isError: true }] };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
