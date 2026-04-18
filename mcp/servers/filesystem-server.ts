import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs";
import * as path from "path";

const ALLOWED_ROOT = process.env.WORKSPACE_ROOT || process.cwd();

function safePath(filePath: string): string {
  const resolved = path.resolve(filePath);
  if (!resolved.startsWith(ALLOWED_ROOT)) {
    throw new Error(`Path traversal blocked: ${filePath}`);
  }
  return resolved;
}

const server = new Server(
  { name: "filesystem-mcp", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "read_file",
      description: "Ler conteúdo de um arquivo",
      inputSchema: {
        type: "object",
        properties: { path: { type: "string" } },
        required: ["path"],
      },
    },
    {
      name: "write_file",
      description: "Escrever conteúdo em um arquivo",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string" },
          content: { type: "string" },
        },
        required: ["path", "content"],
      },
    },
    {
      name: "list_directory",
      description: "Listar conteúdo de um diretório",
      inputSchema: {
        type: "object",
        properties: { path: { type: "string", default: "." } },
      },
    },
    {
      name: "search_files",
      description: "Buscar arquivos por padrão de nome",
      inputSchema: {
        type: "object",
        properties: {
          pattern: { type: "string" },
          directory: { type: "string", default: "." },
        },
        required: ["pattern"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "read_file": {
        const content = fs.readFileSync(safePath(args!.path as string), "utf-8");
        return { content: [{ type: "text", text: content }] };
      }
      case "write_file": {
        const filePath = safePath(args!.path as string);
        fs.mkdirSync(path.dirname(filePath), { recursive: true });
        fs.writeFileSync(filePath, args!.content as string, "utf-8");
        return { content: [{ type: "text", text: `Written: ${filePath}` }] };
      }
      case "list_directory": {
        const dirPath = safePath((args?.path as string) || ".");
        const entries = fs.readdirSync(dirPath, { withFileTypes: true });
        const list = entries.map(e => `${e.isDirectory() ? "[DIR] " : ""}${e.name}`).join("\n");
        return { content: [{ type: "text", text: list }] };
      }
      case "search_files": {
        const dir = safePath((args?.directory as string) || ".");
        const pattern = args!.pattern as string;
        const results: string[] = [];
        function walk(d: string) {
          for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
            const full = path.join(d, entry.name);
            if (entry.isDirectory() && !full.includes("node_modules") && !full.includes(".git")) walk(full);
            else if (entry.name.includes(pattern)) results.push(full);
          }
        }
        walk(dir);
        return { content: [{ type: "text", text: results.join("\n") || "Nenhum resultado" }] };
      }
      default:
        return { content: [{ type: "text", text: `Tool not found: ${name}`, isError: true }] };
    }
  } catch (err: any) {
    return { content: [{ type: "text", text: `Error: ${err.message}`, isError: true }] };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
