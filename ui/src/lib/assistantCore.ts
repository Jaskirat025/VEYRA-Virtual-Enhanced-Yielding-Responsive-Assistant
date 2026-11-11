import type {
  AssistantGoal,
  AssistantHabit,
  AssistantMemory,
  AssistantReminder,
  AssistantSnapshot,
  AssistantTask,
} from "./types";

const DEMO_KEY = "veyra.assistant.demo.v1";

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function assistantCoreKind(): "rust" | "browser" {
  return isTauriRuntime() ? "rust" : "browser";
}

function nowIso(): string {
  return new Date().toISOString();
}

function emptySnapshot(): AssistantSnapshot {
  return {
    memories: [],
    reminders: [],
    habits: [],
    goals: [],
    tasks: [],
    generated_at: nowIso(),
  };
}

function nextId(items: { id: number }[]): number {
  return items.reduce((highest, item) => Math.max(highest, item.id), 0) + 1;
}

function recompute(snapshot: AssistantSnapshot): AssistantSnapshot {
  const now = Date.now();
  const today = new Date().toISOString().slice(0, 10);
  return {
    ...snapshot,
    reminders: snapshot.reminders.map((reminder) => ({
      ...reminder,
      overdue: new Date(reminder.fire_at).getTime() <= now,
    })),
    habits: snapshot.habits.map((habit) => ({
      ...habit,
      done_today: habit.last_completed_on === today,
    })),
    tasks: snapshot.tasks.map((task) => ({
      ...task,
      overdue:
        task.status === "pending" &&
        Boolean(task.due_at) &&
        new Date(task.due_at).getTime() <= now,
    })),
    generated_at: new Date().toISOString(),
  };
}

function readDemo(): AssistantSnapshot {
  try {
    const raw = localStorage.getItem(DEMO_KEY);
    if (!raw) return emptySnapshot();
    const parsed = JSON.parse(raw) as Partial<AssistantSnapshot>;
    return recompute({
      memories: Array.isArray(parsed.memories) ? parsed.memories : [],
      reminders: Array.isArray(parsed.reminders) ? parsed.reminders : [],
      habits: Array.isArray(parsed.habits) ? parsed.habits : [],
      goals: Array.isArray(parsed.goals) ? parsed.goals : [],
      tasks: Array.isArray(parsed.tasks) ? parsed.tasks : [],
      generated_at: typeof parsed.generated_at === "string" ? parsed.generated_at : nowIso(),
    });
  } catch {
    return emptySnapshot();
  }
}

function writeDemo(snapshot: AssistantSnapshot): void {
  localStorage.setItem(DEMO_KEY, JSON.stringify(snapshot));
}

async function invoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke: call } = await import("@tauri-apps/api/core");
  return call<T>(command, args);
}

export async function loadAssistant(): Promise<AssistantSnapshot> {
  if (isTauriRuntime()) return invoke<AssistantSnapshot>("assistant_snapshot");
  return readDemo();
}

export async function saveMemory(input: {
  id?: number;
  title: string;
  body: string;
}): Promise<AssistantMemory> {
  if (isTauriRuntime()) {
    return invoke<AssistantMemory>("assistant_save_memory", {
      id: input.id ?? null,
      title: input.title,
      body: input.body,
    });
  }

  const snapshot = readDemo();
  const now = nowIso();
  const existing = input.id
    ? snapshot.memories.find((memory) => memory.id === input.id)
    : undefined;
  const memory: AssistantMemory = existing
    ? { ...existing, title: input.title, body: input.body, updated_at: now }
    : {
        id: nextId(snapshot.memories),
        title: input.title,
        body: input.body,
        created_at: now,
        updated_at: now,
      };
  writeDemo({
    ...snapshot,
    memories: existing
      ? snapshot.memories.map((item) => (item.id === memory.id ? memory : item))
      : [memory, ...snapshot.memories],
    generated_at: now,
  });
  return memory;
}

export async function deleteMemory(id: number): Promise<void> {
  if (isTauriRuntime()) {
    await invoke("assistant_delete_memory", { id });
    return;
  }
  const snapshot = readDemo();
  writeDemo({
    ...snapshot,
    memories: snapshot.memories.filter((item) => item.id !== id),
    generated_at: nowIso(),
  });
}

export async function saveReminder(input: {
  label: string;
  fire_at: string;
}): Promise<AssistantReminder> {
  if (isTauriRuntime()) {
    return invoke<AssistantReminder>("assistant_save_reminder", {
      label: input.label,
      fireAt: input.fire_at,
    });
  }
  const snapshot = readDemo();
  const reminder: AssistantReminder = {
    id: nextId(snapshot.reminders),
    label: input.label,
    fire_at: input.fire_at,
    created_at: nowIso(),
    overdue: new Date(input.fire_at).getTime() <= Date.now(),
  };
  writeDemo({ ...snapshot, reminders: [...snapshot.reminders, reminder], generated_at: nowIso() });
  return reminder;
}

export async function deleteReminder(id: number): Promise<void> {
  if (isTauriRuntime()) {
    await invoke("assistant_delete_reminder", { id });
    return;
  }
  const snapshot = readDemo();
  writeDemo({
    ...snapshot,
    reminders: snapshot.reminders.filter((item) => item.id !== id),
    generated_at: nowIso(),
  });
}

export async function saveHabit(input: {
  id?: number;
  name: string;
  cadence: "daily" | "weekly";
  target_per_week: number;
}): Promise<AssistantHabit> {
  if (isTauriRuntime()) {
    return invoke<AssistantHabit>("assistant_save_habit", {
      id: input.id ?? null,
      name: input.name,
      cadence: input.cadence,
      targetPerWeek: input.target_per_week,
    });
  }
  const snapshot = readDemo();
  const existing = input.id
    ? snapshot.habits.find((habit) => habit.id === input.id)
    : undefined;
  const target = input.cadence === "daily" ? 7 : Math.max(1, Math.min(7, input.target_per_week));
  const habit: AssistantHabit = existing
    ? {
        ...existing,
        name: input.name,
        cadence: input.cadence,
        target_per_week: target,
      }
    : {
        id: nextId(snapshot.habits),
        name: input.name,
        cadence: input.cadence,
        target_per_week: target,
        streak: 0,
        last_completed_on: "",
        done_today: false,
      };
  writeDemo({
    ...snapshot,
    habits: existing
      ? snapshot.habits.map((item) => (item.id === habit.id ? habit : item))
      : [...snapshot.habits, habit],
    generated_at: nowIso(),
  });
  return habit;
}

export async function completeHabit(id: number): Promise<AssistantHabit> {
  if (isTauriRuntime()) {
    return invoke<AssistantHabit>("assistant_complete_habit", { id });
  }
  const snapshot = readDemo();
  const existing = snapshot.habits.find((habit) => habit.id === id);
  if (!existing) throw new Error("That habit no longer exists.");
  const today = new Date().toISOString().slice(0, 10);
  if (existing.last_completed_on === today) return existing;
  const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
  const streak = existing.last_completed_on === yesterday ? existing.streak + 1 : 1;
  const habit = { ...existing, streak, last_completed_on: today, done_today: true };
  writeDemo({
    ...snapshot,
    habits: snapshot.habits.map((item) => (item.id === id ? habit : item)),
    generated_at: nowIso(),
  });
  return habit;
}

export async function deleteHabit(id: number): Promise<void> {
  if (isTauriRuntime()) {
    await invoke("assistant_delete_habit", { id });
    return;
  }
  const snapshot = readDemo();
  writeDemo({
    ...snapshot,
    habits: snapshot.habits.filter((item) => item.id !== id),
    generated_at: nowIso(),
  });
}

export async function saveGoal(input: {
  id?: number;
  title: string;
  target: number;
  progress: number;
  deadline: string;
}): Promise<AssistantGoal> {
  if (isTauriRuntime()) {
    return invoke<AssistantGoal>("assistant_save_goal", {
      id: input.id ?? null,
      title: input.title,
      target: input.target,
      progress: input.progress,
      deadline: input.deadline,
    });
  }
  const snapshot = readDemo();
  const existing = input.id
    ? snapshot.goals.find((goal) => goal.id === input.id)
    : undefined;
  const target = Math.max(1, Math.min(1_000_000, input.target));
  const progress = Math.max(0, Math.min(target, input.progress));
  const goal: AssistantGoal = {
    id: existing?.id ?? nextId(snapshot.goals),
    title: input.title,
    target,
    progress,
    deadline: input.deadline,
    status: progress >= target ? "done" : "active",
    updated_at: nowIso(),
  };
  writeDemo({
    ...snapshot,
    goals: existing
      ? snapshot.goals.map((item) => (item.id === goal.id ? goal : item))
      : [goal, ...snapshot.goals],
    generated_at: nowIso(),
  });
  return goal;
}

export async function deleteGoal(id: number): Promise<void> {
  if (isTauriRuntime()) {
    await invoke("assistant_delete_goal", { id });
    return;
  }
  const snapshot = readDemo();
  writeDemo({
    ...snapshot,
    goals: snapshot.goals.filter((item) => item.id !== id),
    generated_at: nowIso(),
  });
}

export async function saveTask(input: {
  id?: number;
  title: string;
  notes: string;
  due_at: string;
}): Promise<AssistantTask> {
  if (isTauriRuntime()) {
    return invoke<AssistantTask>("assistant_save_task", {
      id: input.id ?? null,
      title: input.title,
      notes: input.notes,
      dueAt: input.due_at,
    });
  }
  const snapshot = readDemo();
  const existing = input.id
    ? snapshot.tasks.find((task) => task.id === input.id)
    : undefined;
  const task: AssistantTask = existing
    ? { ...existing, title: input.title, notes: input.notes, due_at: input.due_at }
    : {
        id: nextId(snapshot.tasks),
        title: input.title,
        notes: input.notes,
        due_at: input.due_at,
        status: "pending",
        created_at: nowIso(),
        completed_at: "",
        overdue: new Date(input.due_at).getTime() <= Date.now(),
      };
  writeDemo({
    ...snapshot,
    tasks: existing
      ? snapshot.tasks.map((item) => (item.id === task.id ? task : item))
      : [...snapshot.tasks, task],
    generated_at: nowIso(),
  });
  return task;
}

export async function completeTask(id: number, completed: boolean): Promise<AssistantTask> {
  if (isTauriRuntime()) {
    return invoke<AssistantTask>("assistant_complete_task", { id, completed });
  }
  const snapshot = readDemo();
  const existing = snapshot.tasks.find((task) => task.id === id);
  if (!existing) throw new Error("That task no longer exists.");
  const task: AssistantTask = {
    ...existing,
    status: completed ? "done" : "pending",
    completed_at: completed ? nowIso() : "",
    overdue: completed ? false : new Date(existing.due_at).getTime() <= Date.now(),
  };
  writeDemo({
    ...snapshot,
    tasks: snapshot.tasks.map((item) => (item.id === id ? task : item)),
    generated_at: nowIso(),
  });
  return task;
}

export async function deleteTask(id: number): Promise<void> {
  if (isTauriRuntime()) {
    await invoke("assistant_delete_task", { id });
    return;
  }
  const snapshot = readDemo();
  writeDemo({
    ...snapshot,
    tasks: snapshot.tasks.filter((item) => item.id !== id),
    generated_at: nowIso(),
  });
}
