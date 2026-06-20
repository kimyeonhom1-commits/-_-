import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { homedir } from "node:os";
import { join } from "node:path";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const execFileAsync = promisify(execFile);
const WORKSPACE = process.env.OPENCLAW_RESEARCH_WORKSPACE || join(homedir(), "openclaw-workspace");
const WRAPPER = process.env.OPENCLAW_WORKSPACE_RUNNER || join(homedir(), ".local", "bin", "openclaw-workspace-run");
const SCRIPT = join(WORKSPACE, "scripts", "research_control.py");
const COMMANDS = [
  ["gpu", "GPU 사용률, 온도, VRAM 요약"],
  ["disk", "디스크 사용량 요약"],
  ["mem", "메모리와 스왑 사용량 요약"],
  ["log", "최근 OpenClaw 또는 실험 로그 요약"],
  ["report", "최근 24시간 연구 PC와 실험 상태 보고"],
  ["top5", "실험 리더보드 최고 성능 5개"],
  ["failed", "최근 실패 실행 또는 오류 로그 5개"],
];

async function collect(command) {
  try {
    const { stdout } = await execFileAsync(WRAPPER, [SCRIPT, command], {
      timeout: 30000,
      maxBuffer: 512 * 1024,
      windowsHide: true,
    });
    return stdout.trim().slice(0, 12000) || "수집 결과가 없습니다.";
  } catch (error) {
    const stderr = typeof error?.stderr === "string" ? error.stderr.trim() : "";
    return `관제 명령 실행 실패${stderr ? `: ${stderr.slice(0, 500)}` : ""}`;
  }
}

export default definePluginEntry({
  id: "research-control",
  name: "Research Control",
  description: "Read-only research PC status commands for Discord",
  register(api) {
    api.registerTool({
      name: "research_control",
      description: "Read-only research PC monitoring. Use for status, GPU, disk, memory, log, report, leaderboard, or failed-run checks. Only a fixed command enum is accepted.",
      parameters: {
        type: "object",
        additionalProperties: false,
        required: ["command"],
        properties: {
          command: {
            type: "string",
            enum: ["status", "gpu", "disk", "mem", "log", "report", "top5", "failed"],
          },
        },
      },
      async execute(_id, params) {
        const allowed = new Set(["status", "gpu", "disk", "mem", "log", "report", "top5", "failed"]);
        if (!allowed.has(params.command)) {
          return { content: [{ type: "text", text: "허용되지 않은 관제 명령입니다." }] };
        }
        return { content: [{ type: "text", text: await collect(params.command) }] };
      },
    });

    for (const [name, description] of COMMANDS) {
      api.registerCommand({
        name,
        description,
        channels: ["discord"],
        acceptsArgs: false,
        requireAuth: true,
        handler: async () => ({ text: await collect(name) }),
      });
    }
  },
});
