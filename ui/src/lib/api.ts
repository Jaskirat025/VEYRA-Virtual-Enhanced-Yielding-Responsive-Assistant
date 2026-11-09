export interface BackendInfo {
  baseUrl: string;
  wsUrl: string;
  token: string;
}

const DEV_PORT = Number(import.meta.env.VITE_VEYRA_PORT ?? 8765);
const DEV_TOKEN =
  import.meta.env.VITE_VEYRA_TOKEN ??
  (typeof localStorage !== "undefined" ? localStorage.getItem("veyra.devToken") : null) ??
  "dev-token";

async function fromTauri(): Promise<BackendInfo | null> {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const info = await invoke<{ port: number; token: string }>("backend_info");
    if (!info?.port || !info?.token) return null;
    const base = `127.0.0.1:${info.port}`;
    return {
      baseUrl: `http://${base}`,
      wsUrl: `ws://${base}/ws?token=${encodeURIComponent(info.token)}`,
      token: info.token,
    };
  } catch {
    return null;
  }
}

export async function resolveBackend(): Promise<BackendInfo> {
  const tauri = await fromTauri();
  if (tauri) return tauri;
  return {
    baseUrl: `http://127.0.0.1:${DEV_PORT}`,
    wsUrl: `ws://127.0.0.1:${DEV_PORT}/ws?token=${encodeURIComponent(DEV_TOKEN)}`,
    token: DEV_TOKEN,
  };
}

export async function apiFetch<T>(
  info: BackendInfo,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${info.baseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Veyra-Token": info.token,
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText || `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // Non-JSON error body: keep the status text.
    }
    throw new Error(detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function ttsUrl(info: BackendInfo, text: string): string {
  return `${info.baseUrl}/api/tts?text=${encodeURIComponent(text.slice(0, 1200))}`;
}
