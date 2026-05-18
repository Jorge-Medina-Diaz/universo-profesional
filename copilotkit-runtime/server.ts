/**
 * CopilotKit self-hosted runtime (Node 22, CopilotKit @copilotkit/runtime v1.57.1).
 *
 * Mock mode (default): uses `ExperimentalEmptyAdapter` — chat messages don't
 * route to any LLM, but the runtime + AG-UI surface boot fine, the frontend
 * `useCopilotAction` HITL flow works (because actions execute in the BROWSER),
 * and `useCopilotChat().setMcpServers([...])` from the frontend wires MCP
 * tools directly. Real chat answers require setting LLM_PROVIDER=anthropic|openai
 * with the corresponding API key — then we swap to the real adapter.
 */
import express from "express";
import cors from "cors";
import {
  AnthropicAdapter,
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  OpenAIAdapter,
  copilotRuntimeNodeHttpEndpoint,
  type CopilotServiceAdapter,
} from "@copilotkit/runtime";
import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";

const PORT = Number(process.env.PORT || 4000);
const PROVIDER = (process.env.LLM_PROVIDER || "mock").toLowerCase();

function buildAdapter(): CopilotServiceAdapter {
  if (PROVIDER === "anthropic" && process.env.ANTHROPIC_API_KEY) {
    return new AnthropicAdapter({
      anthropic: new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY }),
      model: "claude-sonnet-4-6",
    });
  }
  if (PROVIDER === "openai" && process.env.OPENAI_API_KEY) {
    return new OpenAIAdapter({
      openai: new OpenAI({ apiKey: process.env.OPENAI_API_KEY }),
      model: "gpt-4o-mini",
    });
  }
  // Mock mode: OpenAIAdapter shim with a placeholder client. The runtime needs
  // a model-aware adapter to register a default agent. Real chat messages will
  // 401 against OpenAI, but the chat surface boots, MCP tool routing works,
  // and `useCopilotAction` HITL executes in the browser regardless of LLM.
  console.log(
    "[copilotkit] LLM_PROVIDER=mock — using OpenAIAdapter shim (chat 401s, but HITL + MCP work)",
  );
  return new OpenAIAdapter({
    openai: new OpenAI({ apiKey: "sk-mock-mode-no-real-llm" }),
    model: "gpt-4o-mini",
  });
}

const runtime = new CopilotRuntime({});

const app = express();
app.use(cors({ origin: true, credentials: true }));

app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    provider: PROVIDER,
    mode: PROVIDER === "mock" ? "empty-adapter" : "real",
  });
});

const handler = copilotRuntimeNodeHttpEndpoint({
  endpoint: "/copilotkit",
  runtime,
  serviceAdapter: buildAdapter(),
});

app.use("/copilotkit", handler);

app.listen(PORT, () => {
  console.log(`[copilotkit] runtime listening on :${PORT}`);
});
