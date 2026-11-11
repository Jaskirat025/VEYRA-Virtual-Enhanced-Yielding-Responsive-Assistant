import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { apiFetch, resolveBackend, ttsUrl, type BackendInfo } from "./api";
import type {
  ChatMessage,
  ConfirmRequest,
  Health,
  OrbState,
  Settings,
  ToolEvent,
  ToolInfo,
  ToolLogEntry,
  WsEvent,
} from "./types";

interface VeyraContextValue {
  backend: BackendInfo | null;
  connected: boolean;
  orbState: OrbState;
  settings: Settings | null;
  health: Health | null;
  messages: ChatMessage[];
  toolEvents: ToolEvent[];
  confirm: ConfirmRequest | null;
  notice: string | null;
  error: string | null;
  level: number;
  onboarded: boolean | null;
  wakeAvailable: boolean;
  tools: ToolInfo[];
  toolLog: ToolLogEntry[];
  send: (text: string) => void;
  listen: () => void;
  cancel: () => void;
  respondConfirm: (approved: boolean) => void;
  saveSettings: (patch: Record<string, unknown>) => Promise<void>;
  setLanguage: (language: string) => Promise<void>;
  completeOnboarding: (name: string, language: string) => Promise<void>;
  skipOnboarding: () => Promise<void>;
  deleteAllData: () => Promise<void>;
  refreshTools: () => Promise<void>;
  loadToolLog: () => Promise<void>;
  speakTest: (text: string) => void;
  dismissError: () => void;
  dismissNotice: () => void;
}

const VeyraContext = createContext<VeyraContextValue | null>(null);

async function applyDesktopPreferences(preferences: {
  mini_widget: boolean;
  autostart: boolean;
  close_to_tray: boolean;
}) {
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await Promise.all([
      invoke("set_mini_widget", { visible: preferences.mini_widget }),
      invoke("set_autostart", { enabled: preferences.autostart }),
      invoke("set_close_to_tray", { enabled: preferences.close_to_tray }),
    ]);
  } catch {
    // Browser preview and non-desktop builds have no Tauri commands.
  }
}

function parseArgs(value: Record<string, unknown> | undefined): Record<string, unknown> {
  return value && typeof value === "object" ? value : {};
}

export function VeyraProvider({ children }: { children: ReactNode }) {
  const [backend, setBackend] = useState<BackendInfo | null>(null);
  const [connected, setConnected] = useState(false);
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [settings, setSettings] = useState<Settings | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [confirm, setConfirm] = useState<ConfirmRequest | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [level, setLevel] = useState(0);
  const [onboarded, setOnboarded] = useState<boolean | null>(null);
  const [wakeAvailable, setWakeAvailable] = useState(false);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [toolLog, setToolLog] = useState<ToolLogEntry[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const backendRef = useRef<BackendInfo | null>(null);
  const onboardedRef = useRef<boolean | null>(null);
  onboardedRef.current = onboarded;

  const applySettings = useCallback((next: Settings) => {
    setSettings(next);
  }, []);

  const playSpeech = useCallback(async (text: string) => {
    const info = backendRef.current;
    if (!info || !text.trim()) return;
    try {
      const response = await fetch(ttsUrl(info, text), {
        headers: { "X-Veyra-Token": info.token },
      });
      if (!response.ok) return;
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      const AudioContextClass =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      let context: AudioContext | null = null;
      let frame = 0;
      let analyser: AnalyserNode | null = null;

      if (AudioContextClass) {
        try {
          context = new AudioContextClass();
          const source = context.createMediaElementSource(audio);
          analyser = context.createAnalyser();
          analyser.fftSize = 256;
          source.connect(analyser);
          analyser.connect(context.destination);
        } catch {
          context = null;
        }
      }

      const tick = () => {
        if (!analyser) return;
        const data = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(data);
        const average = data.reduce((sum, value) => sum + value, 0) / data.length / 255;
        setLevel(average);
        frame = requestAnimationFrame(tick);
      };

      audio.onended = () => {
        cancelAnimationFrame(frame);
        setLevel(0);
        URL.revokeObjectURL(url);
        context?.close().catch(() => undefined);
      };
      await audio.play();
      tick();
    } catch {
      // Autoplay can be blocked; the text is always visible in the transcript.
      setLevel(0);
    }
  }, []);

  const handleEvent = useCallback(
    (event: WsEvent) => {
      switch (event.type) {
        case "ready":
          setOrbState("idle");
          setWakeAvailable(Boolean(event.data.wake_available));
          break;
        case "state":
          setOrbState(event.state);
          if (event.state !== "listening") setLevel(0);
          break;
        case "transcript":
          setMessages((current) => [
            ...current,
            {
              role: event.data.role,
              text: event.data.text,
              used_online: event.data.used_online,
            },
          ]);
          break;
        case "tool_call":
          setToolEvents((current) => [
            ...current,
            {
              id: `${event.data.tool}-${current.length}-${Date.now()}`,
              tool: event.data.tool,
              risk: event.data.risk,
              status: event.data.status,
              args: parseArgs(event.data.arguments),
            },
          ]);
          break;
        case "tool_result":
          setToolEvents((current) => {
            const next = [...current];
            for (let index = next.length - 1; index >= 0; index -= 1) {
              if (next[index].tool === event.data.tool) {
                next[index] = {
                  ...next[index],
                  status: event.data.status,
                  output: event.data.output,
                  duration_ms: event.data.duration_ms,
                };
                break;
              }
            }
            return next;
          });
          break;
        case "tool_confirm_request":
          setConfirm(event.data);
          break;
        case "notice":
          setNotice(event.data.message);
          break;
        case "error":
          setError(event.message);
          setOrbState("error");
          break;
        case "audio_level":
          setLevel(event.data.level);
          break;
        case "speak":
          void playSpeech(event.data.text);
          break;
        case "timer_due":
          setNotice(event.data.label);
          break;
        default:
          break;
      }
    },
    [playSpeech],
  );

  useEffect(() => {
    let disposed = false;
    let reconnect: number | undefined;
    let socket: WebSocket | null = null;

    const connect = (info: BackendInfo) => {
      if (disposed) return;
      socket = new WebSocket(info.wsUrl);
      wsRef.current = socket;
      socket.onopen = () => {
        if (!disposed) setConnected(true);
      };
      socket.onclose = () => {
        if (disposed) return;
        setConnected(false);
        reconnect = window.setTimeout(() => connect(info), 3000);
      };
      socket.onmessage = (message) => {
        try {
          handleEvent(JSON.parse(message.data as string) as WsEvent);
        } catch {
          // Ignore malformed frames; the connection stays alive.
        }
      };
    };

    const bootstrap = async () => {
      const info = await resolveBackend();
      if (disposed) return;
      backendRef.current = info;
      setBackend(info);

      try {
        const [settingsResponse, healthResponse, kv, lastConversation, toolsResponse] =
          await Promise.all([
            apiFetch<{ settings: Settings }>(info, "/api/settings"),
            apiFetch<Health>(info, "/api/health"),
            apiFetch<{ value: string }>(info, "/api/kv/onboarded"),
            apiFetch<{ value: string }>(info, "/api/kv/last_conversation_id"),
            apiFetch<{ tools: ToolInfo[] }>(info, "/api/tools"),
          ]);
        applySettings(settingsResponse.settings);
        setHealth(healthResponse);
        setTools(toolsResponse.tools);
        setOnboarded(kv.value === "1");

        if (lastConversation.value) {
          try {
            const history = await apiFetch<{
              messages: { role: string; content: string }[];
            }>(
              info,
              `/api/messages?conversation_id=${encodeURIComponent(lastConversation.value)}&limit=100`,
            );
            setMessages(
              history.messages
                .filter(
                  (message): message is { role: "user" | "assistant"; content: string } =>
                    message.role === "user" || message.role === "assistant",
                )
                .map((message) => ({ role: message.role, text: message.content })),
            );
          } catch {
            // A missing history is not fatal; the chat starts empty.
          }
        }
      } catch {
        setError(
          "The local backend is not reachable. Start Veyra from the desktop app, or run the backend in development mode.",
        );
        setOnboarded(false);
      }

      connect(info);
    };

    void bootstrap();

    return () => {
      disposed = true;
      window.clearTimeout(reconnect);
      socket?.close();
      wsRef.current = null;
    };
  }, [applySettings, handleEvent]);

  const send = useCallback((text: string) => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN || !text.trim()) return;
    setError(null);
    socket.send(JSON.stringify({ type: "user_text", text: text.trim() }));
  }, []);

  const listen = useCallback(() => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: "start_listening" }));
  }, []);

  const cancel = useCallback(() => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: "cancel" }));
  }, []);

  const respondConfirm = useCallback(
    (approved: boolean) => {
      const socket = wsRef.current;
      const request = confirm;
      setConfirm(null);
      if (!socket || socket.readyState !== WebSocket.OPEN || !request) return;
      socket.send(
        JSON.stringify({
          type: "confirm_response",
          request_id: request.request_id,
          approved,
        }),
      );
    },
    [confirm],
  );

  const saveSettings = useCallback(async (patch: Record<string, unknown>) => {
    const info = backendRef.current;
    if (!info) return;
    const response = await apiFetch<{ settings: Settings }>(info, "/api/settings", {
      method: "PUT",
      body: JSON.stringify({ patch }),
    });
    setSettings(response.settings);
  }, []);

  const setLanguage = useCallback(
    async (language: string) => {
      setSettings((current) =>
        current ? { ...current, interface: { ...current.interface, language } } : current,
      );
      try {
        await saveSettings({ interface: { language } });
      } catch {
        // The language still applies for this session.
      }
    },
    [saveSettings],
  );

  const completeOnboarding = useCallback(
    async (name: string, language: string) => {
      setOnboarded(true);
      try {
        await saveSettings({
          assistant_name: name,
          interface: { language },
        });
        const info = backendRef.current;
        if (info) {
          await apiFetch(info, "/api/kv/onboarded", {
            method: "PUT",
            body: JSON.stringify({ value: "1" }),
          });
        }
      } catch {
        setError("Onboarding could not be saved; settings will be retried next launch.");
      }
    },
    [saveSettings],
  );

  const skipOnboarding = useCallback(async () => {
    setOnboarded(true);
    const info = backendRef.current;
    if (!info) return;
    try {
      await apiFetch(info, "/api/kv/onboarded", {
        method: "PUT",
        body: JSON.stringify({ value: "1" }),
      });
    } catch (cause) {
      setError(`Onboarding could not be saved: ${(cause as Error).message}`);
    }
  }, []);

  const deleteAllData = useCallback(async () => {
    const info = backendRef.current;
    if (!info) throw new Error("The local backend is not reachable.");
    await apiFetch(info, "/api/privacy/data", { method: "DELETE" });
    setMessages([]);
    setToolEvents([]);
    setToolLog([]);
    setSettings(null);
    setOnboarded(false);
  }, []);

  useEffect(() => {
    if (!settings) return;
    void applyDesktopPreferences(settings.interface);
  }, [settings]);

  const refreshTools = useCallback(async () => {
    const info = backendRef.current;
    if (!info) return;
    const response = await apiFetch<{ tools: ToolInfo[] }>(info, "/api/tools");
    setTools(response.tools);
  }, []);

  const loadToolLog = useCallback(async () => {
    const info = backendRef.current;
    if (!info) return;
    const response = await apiFetch<{ entries: ToolLogEntry[] }>(info, "/api/tools/log?limit=200");
    setToolLog(response.entries);
  }, []);

  const speakTest = useCallback(
    (text: string) => {
      void playSpeech(text);
    },
    [playSpeech],
  );

  const dismissError = useCallback(() => {
    setError(null);
    setOrbState((current) => (current === "error" ? "idle" : current));
  }, []);
  const dismissNotice = useCallback(() => setNotice(null), []);

  const value: VeyraContextValue = {
    backend,
    connected,
    orbState,
    settings,
    health,
    messages,
    toolEvents,
    confirm,
    notice,
    error,
    level,
    onboarded,
    wakeAvailable,
    tools,
    toolLog,
    send,
    listen,
    cancel,
    respondConfirm,
    saveSettings,
    setLanguage,
    completeOnboarding,
    skipOnboarding,
    deleteAllData,
    refreshTools,
    loadToolLog,
    speakTest,
    dismissError,
    dismissNotice,
  };

  return <VeyraContext.Provider value={value}>{children}</VeyraContext.Provider>;
}

export function useVeyra(): VeyraContextValue {
  const context = useContext(VeyraContext);
  if (!context) throw new Error("useVeyra must be used inside VeyraProvider");
  return context;
}
