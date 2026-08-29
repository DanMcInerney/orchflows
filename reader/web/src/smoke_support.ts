import { spawn, type ChildProcess } from "node:child_process";

export interface ViewIdentity {
  identity: string;
  path: string;
  view: string;
  breakpoint: string;
}

export interface ViewManifest {
  views: ViewIdentity[];
  breakpoints: Record<string, [number, number]>;
  navigationParents: Record<string, string>;
}

export interface NowProjectionRun {
  id: string;
  repository: string;
  terminal_at: string;
  terminal_status: string;
}

export interface NowProjection {
  runs: NowProjectionRun[];
}

export function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for this action`);
  return value;
}

export async function startOriginProcess(
  command: string,
  args: string[],
  label: string,
  cwd: string,
  env: NodeJS.ProcessEnv,
): Promise<{ child: ChildProcess; origin: string }> {
  const child = spawn(command, args, {
    cwd,
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  const origin = await new Promise<string>((resolveOrigin, reject) => {
    let stderr = "";
    child.stderr?.on("data", (chunk: Buffer) => { stderr += chunk.toString(); });
    child.stdout?.on("data", (chunk: Buffer) => {
      const match = chunk.toString().match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) resolveOrigin(match[0]);
    });
    child.once("exit", (code: number | null) => reject(new Error(`${label} exited ${code}: ${stderr}`)));
  });
  return { child, origin };
}
