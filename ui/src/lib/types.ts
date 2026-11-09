export type View = "home" | "chat" | "tools" | "settings";

export type OrbState = "idle" | "listening" | "thinking" | "speaking" | "error";

export type Risk = "safe" | "confirm" | "dangerous";

export interface ModelSettings {
  local_model: string;
  context_tokens: number;
  temperature: number;
  online_enabled: boolean;
  online_base_url: string;
  online_model: string;
  online_api_style: string;
}

export interface VoiceSettings {
  engine: string;
  piper_voice: string;
  rate: number;
  volume: number;
  speak_replies: boolean;
}

export interface AudioSettings {
  input_device: number | null;
  stt_model: string;
  stt_compute_type: string;
  vad_threshold: number;
  silence_ms: number;
  max_utterance_s: number;
  wake_engine: string;
  wake_model_path: string;
  push_to_talk: boolean;
}

export interface IntegrationSettings {
  github_login: string;
  github_read_only: boolean;
  google_read_only: boolean;
  gmail_address: string;
}

export interface InterfaceSettings {
  language: string;
  low_power: boolean;
  mini_widget: boolean;
  autostart: boolean;
  close_to_tray: boolean;
}

export interface Settings {
  assistant_name: string;
  wake_word: string;
  system_prompt: string;
  models: ModelSettings;
  voice: VoiceSettings;
  audio: AudioSettings;
  integrations: IntegrationSettings;
  interface: InterfaceSettings;
  tool_permissions: Record<string, boolean>;
  ram_floor_mb: number;
}

export interface Health {
  status: string;
  version: string;
  model: string;
  online_enabled: boolean;
  ram_mb: number;
  data_dir: string;
}

export type DownloadStatus = "pending" | "running" | "done" | "skipped" | "error";

export interface BootstrapJob {
  id: string;
  label: string;
  status: DownloadStatus;
  progress: number | null;
  detail: string;
  downloaded: number;
  total: number;
  error: string;
}

export interface BootstrapStatus {
  running: boolean;
  complete: boolean;
  failed: boolean;
  jobs: BootstrapJob[];
}

export interface ToolInfo {
  name: string;
  category: string;
  risk: Risk;
  description: string;
  enabled: boolean;
  tags: string[];
}

export interface ToolLogEntry {
  id: number;
  tool: string;
  category: string;
  risk: string;
  status: string;
  duration_ms: number;
  error: string;
  output_preview: string;
  args_redacted: Record<string, unknown>;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  used_online?: boolean;
}

export interface ToolEvent {
  id: string;
  tool: string;
  risk: Risk;
  status: string;
  args: Record<string, unknown>;
  output?: string;
  duration_ms?: number;
}

export interface ConfirmRequest {
  request_id: string;
  tool: string;
  category: string;
  risk: Risk;
  summary: string;
  arguments: Record<string, unknown>;
  external_content_read: boolean;
  timeout_s: number;
}

export type WsEvent =
  | { type: "ready"; data: { model: string; assistant_name: string; language: string } }
  | { type: "state"; state: OrbState; detail?: string }
  | {
      type: "transcript";
      data: { role: "user" | "assistant"; text: string; used_online?: boolean };
    }
  | { type: "tool_call"; data: Omit<ToolEvent, "id" | "args"> & { arguments: Record<string, unknown> } }
  | { type: "tool_result"; data: { tool: string; status: string; output: string; duration_ms: number } }
  | { type: "tool_confirm_request"; data: ConfirmRequest }
  | { type: "notice"; data: { message: string } }
  | { type: "error"; message: string }
  | { type: "audio_level"; data: { source: string; level: number } }
  | { type: "speak"; data: { text: string } }
  | { type: "timer_due"; data: { label: string } }
  | { type: "pong" };
