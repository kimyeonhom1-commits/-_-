# OpenClaw Workspace Rules

This is the only writable project workspace for the Discord agent.

## Allowed work

- Create, organize, edit, test, and document code only inside this workspace.
- Use Python from `.venv/bin/python`.
- Run workspace commands through:
  `~/.local/bin/openclaw-workspace-run -- <program> <args>`
- Point-cloud analysis, machine learning, deep learning, visualization, notebooks, and long-running training jobs are allowed inside this workspace.

## Hard safety rules

- `/data_raw` is read-only input data. Never write, edit, rename, move, or delete anything under it.
- Never read or expose credentials, `.env` files, SSH keys, browser profiles, or OpenClaw configuration secrets.
- Never run `rm`, disk formatting, partitioning, or destructive cleanup commands.
- Never use arbitrary `sudo` commands.
- Only request a reboot when the Discord owner explicitly asks for a reboot in the current conversation. Use `~/.local/bin/openclaw-reboot` and wait for explicit approval.
- Do not claim a command succeeded without checking its exit status or output.

## Project workflow

1. Inspect the relevant files before editing.
2. Preserve user code unless a replacement was explicitly requested.
3. Keep generated outputs under `outputs/`, models under `models/`, notebooks under `notebooks/`, and source code under `src/` when practical.
4. Prefer reproducible Python scripts and record dependencies.
5. Run focused tests after changes and report failures honestly.

## Discord reporting

- Acknowledge the requested task before starting when it may take more than a minute.
- For long-running analysis or training, report when the job starts and report completion or failure when it ends.
- Every completion report must include: status, elapsed time, important metrics, generated/changed file paths, and any warnings or failed checks.
- Keep routine reports concise. Put detailed machine-readable metrics in `outputs/<task-name>/report.json` and human-readable results in `outputs/<task-name>/REPORT.md` when appropriate.
- Never report an output artifact unless it exists and was checked.
- Analysis and training scripts must print their final machine-readable result JSON to stdout. Report metric values only when they appeared in verified tool output or were read back from the artifact; never guess versions, metrics, or file contents.

## Research control routing

- For requests to check status, GPU, disk, memory, logs, daily reports, leaderboard, or failures, always call the `research_control` tool with the matching fixed command.
- In particular, `상태 확인` must call `research_control` with `command: "status"` before replying.
- Never reuse an earlier status value or invent system metrics. Return the tool result without replacing measured values.
- Prefer the deterministic Discord commands `/status`, `/gpu`, `/disk`, `/mem`, `/log`, `/report`, `/top5`, and `/failed` for operator-facing checks.
