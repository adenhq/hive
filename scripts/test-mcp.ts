/**
 * MCP Server Test Script
 *
 * Tests the MCP server by connecting via HTTP/SSE and invoking tools.
 *
 * Usage:
 *   npx tsx scripts/test-mcp.ts
 *   npx tsx scripts/test-mcp.ts --list-tools
 *   npx tsx scripts/test-mcp.ts --tool hive_metrics
 *   npx tsx scripts/test-mcp.ts --category budget
 *
 * Environment:
 *   ADEN_API_URL - Base URL (default: http://localhost:3000)
 *   ADEN_AUTH_TOKEN - JWT token for authentication
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const API_URL = process.env.ADEN_API_URL || "http://localhost:3000";
const AUTH_TOKEN = process.env.ADEN_AUTH_TOKEN;

interface CliArgs {
  listTools: boolean;
  tool?: string;
  category?: string;
  help: boolean;
}

function parseArgs(): CliArgs {
  const args: CliArgs = {
    listTools: false,
    help: false,
  };

  for (let i = 2; i < process.argv.length; i++) {
    const arg = process.argv[i];
    switch (arg) {
      case "--list-tools":
      case "--list":
        args.listTools = true;
        break;
      case "--tool":
        args.tool = process.argv[++i];
        break;
      case "--category":
        args.category = process.argv[++i];
        break;
      case "--help":
      case "-h":
        args.help = true;
        break;
    }
  }

  return args;
}

function printHelp() {
  console.log(`
MCP Server Test Script

Usage:
  npx tsx scripts/test-mcp.ts [options]

Options:
  --list-tools, --list    List all available tools and exit
  --tool <name>           Run a specific tool by name
  --category <category>   Run tools in a specific category (budget, agents, analytics, policies)
  --help, -h              Show this help message

Environment Variables:
  ADEN_API_URL           Base URL (default: http://localhost:3000)
  ADEN_AUTH_TOKEN        JWT token for authentication (required)

Examples:
  npx tsx scripts/test-mcp.ts --list-tools
  npx tsx scripts/test-mcp.ts --tool hive_metrics
  npx tsx scripts/test-mcp.ts --category budget
  ADEN_AUTH_TOKEN=your-token npx tsx scripts/test-mcp.ts
`);
}

async function main() {
  const args = parseArgs();

  if (args.help) {
    printHelp();
    process.exit(0);
  }

  if (!AUTH_TOKEN) {
    console.error("Error: ADEN_AUTH_TOKEN environment variable is required");
    console.error("Usage: ADEN_AUTH_TOKEN=your-jwt-token npx tsx scripts/test-mcp.ts");
    process.exit(1);
  }

  console.log("=".repeat(60));
  console.log("MCP Server Test");
  console.log("=".repeat(60));
  console.log(`API URL: ${API_URL}`);
  console.log("");

  // Create MCP client
  const client = new Client({
    name: "mcp-test-client",
    version: "1.0.0",
  });

  // Create SSE transport with auth headers
  const transport = new SSEClientTransport(new URL(`${API_URL}/mcp`), {
    requestInit: {
      headers: {
        Authorization: `Bearer ${AUTH_TOKEN}`,
      },
    },
  });

  try {
    // Connect to MCP server
    console.log("Connecting to MCP server...");
    await client.connect(transport);
    console.log("✓ Connected successfully\n");

    // List available tools
    console.log("Listing available tools...");
    const tools = await client.listTools();
    console.log(`✓ Found ${tools.tools.length} tools:\n`);

    // Group tools by category
    const categories: Record<string, string[]> = {
      budget: [],
      agents: [],
      analytics: [],
      policies: [],
      other: [],
    };

    for (const tool of tools.tools) {
      if (tool.name.includes("budget")) {
        categories.budget.push(tool.name);
      } else if (tool.name.includes("agent")) {
        categories.agents.push(tool.name);
      } else if (
        tool.name.includes("analytics") ||
        tool.name.includes("insights") ||
        tool.name.includes("metrics") ||
        tool.name.includes("logs")
      ) {
        categories.analytics.push(tool.name);
      } else if (tool.name.includes("polic")) {
        categories.policies.push(tool.name);
      } else {
        categories.other.push(tool.name);
      }
    }

    // If --list-tools, print and exit
    if (args.listTools) {
      for (const [category, toolNames] of Object.entries(categories)) {
        if (toolNames.length > 0) {
          console.log(`  ${category.toUpperCase()} (${toolNames.length}):`);
          for (const name of toolNames) {
            console.log(`    - ${name}`);
          }
        }
      }
      console.log("");
      return;
    }

    // Print tool categories
    for (const [category, toolNames] of Object.entries(categories)) {
      if (toolNames.length > 0) {
        console.log(`  ${category.toUpperCase()} (${toolNames.length}):`);
        for (const name of toolNames) {
          console.log(`    - ${name}`);
        }
      }
    }
    console.log("");

    // Run test scenarios
    console.log("=".repeat(60));
    console.log("Running Test Scenarios");
    console.log("=".repeat(60));
    console.log("");

    // If specific tool requested
    if (args.tool) {
      const toolExists = tools.tools.some((t) => t.name === args.tool);
      if (!toolExists) {
        console.error(`Error: Tool '${args.tool}' not found`);
        process.exit(1);
      }
      await runTest(client, args.tool, {}, `Test tool: ${args.tool}`);
      return;
    }

    // If specific category requested
    if (args.category) {
      const categoryTools = categories[args.category.toLowerCase()];
      if (!categoryTools || categoryTools.length === 0) {
        console.error(`Error: Category '${args.category}' not found or empty`);
        console.error(`Available categories: ${Object.keys(categories).join(", ")}`);
        process.exit(1);
      }
      console.log(`Running tests for category: ${args.category}`);
      console.log("");
      for (const toolName of categoryTools) {
        await runTest(client, toolName, {}, `Test: ${toolName}`);
      }
      return;
    }

    // Default: run predefined test scenarios
    // Test 1: Get policy
    await runTest(client, "hive_policy_get", { policyId: "default" }, "Get default policy");

    // Test 2: List agents
    await runTest(client, "hive_agents_summary", {}, "Get agent fleet summary");

    // Test 3: Get insights
    await runTest(client, "hive_insights", { days: 7 }, "Get 7-day insights");

    // Test 4: Get metrics
    await runTest(client, "hive_metrics", { days: 30 }, "Get 30-day metrics");

    // Test 5: Budget validation (dry run)
    await runTest(
      client,
      "hive_budget_validate",
      {
        estimatedCost: 0.01,
        context: { agent: "test-agent" },
      },
      "Validate budget (dry run)"
    );

    console.log("=".repeat(60));
    console.log("All tests completed!");
    console.log("=".repeat(60));
  } catch (error) {
    console.error("Error:", error);
    process.exit(1);
  } finally {
    await client.close();
  }
}

async function runTest(
  client: Client,
  toolName: string,
  args: Record<string, unknown>,
  description: string
) {
  console.log(`Test: ${description}`);
  console.log(`  Tool: ${toolName}`);
  console.log(`  Args: ${JSON.stringify(args)}`);

  try {
    const startTime = Date.now();
    const result = await client.callTool({ name: toolName, arguments: args });
    const duration = Date.now() - startTime;

    console.log(`  Status: ✓ Success (${duration}ms)`);

    // Parse and display result
    if (result.content && result.content.length > 0) {
      const textContent = result.content.find((c) => c.type === "text");
      if (textContent && "text" in textContent) {
        try {
          const parsed = JSON.parse(textContent.text);
          console.log(`  Result: ${JSON.stringify(parsed, null, 2).split("\n").slice(0, 10).join("\n")}`);
          if (JSON.stringify(parsed, null, 2).split("\n").length > 10) {
            console.log("    ... (truncated)");
          }
        } catch {
          console.log(`  Result: ${textContent.text.slice(0, 200)}...`);
        }
      }
    }

    if (result.isError) {
      console.log(`  Warning: Tool returned isError=true`);
    }
  } catch (error) {
    console.log(`  Status: ✗ Failed`);
    console.log(`  Error: ${error instanceof Error ? error.message : error}`);
  }

  console.log("");
}

main().catch(console.error);
