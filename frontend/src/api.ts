export type Environment = { id: string; course_key: string | null; state: string; error: string | null; setup_done: number; name: string; cpus: number; memory_mb: number; pids: number; is_default: number; created_at: string };
export type CheckResult = { status: 'pass' | 'fail' | 'error'; message: string; stdout?: string; stderr?: string; command?: string; exit_code?: number; expected_exit?: number; expected_stdout?: string; expected_stderr?: string };
export type TaskResult = { id: string; status: string; earned: number; available: number; checks: CheckResult[] };
export type Result = { exercise_id: string; tasks: TaskResult[]; earned: number; available: number; checked_at: string };
export type Reference = { document_hash: string; title: string; pages: number[]; available?: boolean; source_id?: string };
export type Evaluation = { id: string; description: string; points: number; checks: { type: string; args?: string[]; requirement?: string }[] };
export type InputRequirement = { description: string; error?: string };
export type OutputRequirement = { id: string; description: string; exit_code: number; stream: 'stdout' | 'stderr'; message?: string };
export type Example = { command: string; stdout?: string; stderr?: string; exit_code?: number; description?: string };
export type Exercise = { id: string; title: string; description: string; script?: { path: string; usage?: string }; input_requirements: InputRequirement[]; output_requirements: OutputRequirement[]; examples: Example[]; evaluations: Evaluation[]; tips: string[]; setup: object[]; sources: Reference[]; supplemental?: string };
export type Course = { id: string; version: string; title: string; description: string; exercises: Exercise[] };
export type CourseSummary = { key: string; id: string; title: string; description: string; version: string; exercise_count: number; points: number; earned: number; completed: number; environment: Environment | null };
export type CourseDetail = { key: string; course: Course; environment: Environment; results: Record<string, Result> };
export type Source = { id: string; title: string; filename: string; hash: string; state: string; pages: number; indexed_pages: number; ocr_pages: number; error: string | null; warnings: string[] };
export type Job = { id: string; state: string; progress: string; error: string | null };
export type Chat = { id: string; title: string; draft: string; messages: { id: number; role: string; content: string }[]; job: Job | null };
export type Config = { token: string; docker: { available: boolean; image_ready: boolean; message: string }; ollama_url: string; ocr_languages: string; desktop: boolean };
let token = '';

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set('X-Lab-Token', token);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch('/api' + path, { ...options, headers });
  if (!response.ok) {
    let detail: unknown = response.statusText;
    try { detail = (await response.json()).detail; } catch { /* retain status */ }
    if (Array.isArray(detail)) detail = detail.map(e => `${e.path ?? e.loc?.join('.') ?? ''}: ${e.message ?? e.msg ?? ''}`).join('\n');
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return response.json();
}

export async function configure(): Promise<Config> {
  const config = await api<Config>('/config'); token = config.token; return config;
}
export const post = <T,>(path: string, data: unknown = {}) => api<T>(path, { method: 'POST', body: JSON.stringify(data) });
export const desktopURL = (id: string) => `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/environments/${id}/desktop?token=${encodeURIComponent(token)}`;
export const download = (content: string, filename: string) => {
  const url = URL.createObjectURL(new Blob([content], { type: 'application/yaml' }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
};
export function progressPercent(earned: number, total: number): number { return total > 0 ? Math.min(100, Math.round(earned / total * 100)) : 0; }

export function selectLocalModel(models: { name: string }[], saved: string): string {
  return models.find(m => m.name === saved)?.name
    || models.find(m => m.name === 'gemma3:12b-it-qat')?.name
    || models[0]?.name || '';
}
