import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  assistantCoreKind,
  completeHabit,
  completeTask,
  deleteGoal,
  deleteHabit,
  deleteMemory,
  deleteReminder,
  deleteTask,
  loadAssistant,
  saveGoal,
  saveHabit,
  saveMemory,
  saveReminder,
  saveTask,
} from "../lib/assistantCore";
import type {
  AssistantGoal,
  AssistantHabit,
  AssistantMemory,
  AssistantSnapshot,
  AssistantTask,
} from "../lib/types";
import { useI18n } from "../i18n";

type Tab = "memories" | "reminders" | "habits" | "goals" | "tasks";
type Mutate = (action: () => Promise<unknown>) => Promise<boolean>;

interface SectionProps {
  snapshot: AssistantSnapshot;
  busy: boolean;
  mutate: Mutate;
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "—";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function toLocalInput(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

function toDateInput(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 10);
}

function fromLocalInput(value: string): string {
  return value ? new Date(value).toISOString() : "";
}

function nextHour(): string {
  return toLocalInput(new Date(Date.now() + 3_600_000).toISOString());
}

function Empty({ label }: { label: string }) {
  return <p className="py-8 text-center text-xs text-silver-500">{label}</p>;
}

function ItemActions({
  onEdit,
  onDelete,
  disabled,
}: {
  onEdit?: () => void;
  onDelete: () => void;
  disabled: boolean;
}) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap gap-2">
      {onEdit && (
        <button type="button" className="vy-btn h-8 px-3 text-xs" disabled={disabled} onClick={onEdit}>
          {t("assistant.edit")}
        </button>
      )}
      <button
        type="button"
        className="vy-btn h-8 px-3 text-xs"
        disabled={disabled}
        onClick={() => {
          if (window.confirm(t("assistant.deleteConfirm"))) onDelete();
        }}
      >
        {t("assistant.delete")}
      </button>
    </div>
  );
}

function MemorySection({ snapshot, busy, mutate }: SectionProps) {
  const { t } = useI18n();
  const [editing, setEditing] = useState<AssistantMemory | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const reset = () => {
    setEditing(null);
    setTitle("");
    setBody("");
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (await mutate(() => saveMemory({ id: editing?.id, title, body }))) reset();
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[330px_1fr]">
      <form className="vy-panel h-fit space-y-3 p-5" onSubmit={(event) => void submit(event)}>
        <h2 className="font-display text-lg tracking-wide text-silver-100">
          {editing ? t("assistant.edit") : t("assistant.add")}
        </h2>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.titleField")}
          </span>
          <input
            className="vy-field"
            required
            maxLength={200}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.body")}
          </span>
          <textarea
            className="vy-field min-h-[150px] resize-y"
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
        </label>
        <p className="text-[11px] leading-relaxed text-silver-500">{t("assistant.memoryHint")}</p>
        <div className="flex gap-2">
          <button type="submit" className="vy-btn vy-btn-primary" disabled={busy}>
            {t("assistant.save")}
          </button>
          {editing && (
            <button type="button" className="vy-btn" disabled={busy} onClick={reset}>
              {t("assistant.cancel")}
            </button>
          )}
        </div>
      </form>

      <div className="space-y-3">
        {snapshot.memories.length === 0 ? (
          <Empty label={t("assistant.empty")} />
        ) : (
          snapshot.memories.map((memory) => (
            <article key={memory.id} className="vy-panel p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="truncate text-sm text-silver-100">{memory.title}</h3>
                  <p className="mt-1 text-[10px] uppercase tracking-[0.12em] text-silver-500">
                    {formatDate(memory.updated_at)}
                  </p>
                </div>
                <ItemActions
                  disabled={busy}
                  onEdit={() => {
                    setEditing(memory);
                    setTitle(memory.title);
                    setBody(memory.body);
                  }}
                  onDelete={() => void mutate(() => deleteMemory(memory.id))}
                />
              </div>
              {memory.body && (
                <p className="mt-3 whitespace-pre-wrap text-xs leading-relaxed text-silver-400">
                  {memory.body}
                </p>
              )}
            </article>
          ))
        )}
      </div>
    </div>
  );
}

function ReminderSection({ snapshot, busy, mutate }: SectionProps) {
  const { t } = useI18n();
  const [label, setLabel] = useState("");
  const [fireAt, setFireAt] = useState(nextHour);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (await mutate(() => saveReminder({ label, fire_at: fromLocalInput(fireAt) }))) {
      setLabel("");
      setFireAt(nextHour());
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[330px_1fr]">
      <form className="vy-panel h-fit space-y-3 p-5" onSubmit={(event) => void submit(event)}>
        <h2 className="font-display text-lg tracking-wide text-silver-100">
          {t("assistant.add")}
        </h2>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.label")}
          </span>
          <input
            className="vy-field"
            required
            maxLength={200}
            value={label}
            onChange={(event) => setLabel(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.when")}
          </span>
          <input
            type="datetime-local"
            className="vy-field"
            required
            value={fireAt}
            onChange={(event) => setFireAt(event.target.value)}
          />
        </label>
        <p className="text-[11px] leading-relaxed text-silver-500">{t("assistant.reminderHint")}</p>
        <button type="submit" className="vy-btn vy-btn-primary" disabled={busy}>
          {t("assistant.save")}
        </button>
      </form>

      <div className="space-y-3">
        {snapshot.reminders.length === 0 ? (
          <Empty label={t("assistant.empty")} />
        ) : (
          snapshot.reminders.map((reminder) => (
            <article key={reminder.id} className="vy-panel flex items-start justify-between gap-4 p-4">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm text-silver-100">{reminder.label}</h3>
                  {reminder.overdue && (
                    <span className="font-display text-[9px] uppercase tracking-[0.14em] text-accent">
                      {t("assistant.overdue")}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-silver-400">{formatWhen(reminder.fire_at)}</p>
              </div>
              <ItemActions
                disabled={busy}
                onDelete={() => void mutate(() => deleteReminder(reminder.id))}
              />
            </article>
          ))
        )}
      </div>
    </div>
  );
}

function HabitSection({ snapshot, busy, mutate }: SectionProps) {
  const { t } = useI18n();
  const [editing, setEditing] = useState<AssistantHabit | null>(null);
  const [name, setName] = useState("");
  const [cadence, setCadence] = useState<"daily" | "weekly">("daily");
  const [target, setTarget] = useState(7);

  const reset = () => {
    setEditing(null);
    setName("");
    setCadence("daily");
    setTarget(7);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (await mutate(() => saveHabit({ id: editing?.id, name, cadence, target_per_week: target }))) {
      reset();
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[330px_1fr]">
      <form className="vy-panel h-fit space-y-3 p-5" onSubmit={(event) => void submit(event)}>
        <h2 className="font-display text-lg tracking-wide text-silver-100">
          {editing ? t("assistant.edit") : t("assistant.add")}
        </h2>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.name")}
          </span>
          <input
            className="vy-field"
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.cadence")}
          </span>
          <select
            className="vy-field"
            value={cadence}
            onChange={(event) => {
              const next = event.target.value as "daily" | "weekly";
              setCadence(next);
              setTarget(next === "daily" ? 7 : 3);
            }}
          >
            <option value="daily">{t("assistant.daily")}</option>
            <option value="weekly">{t("assistant.weekly")}</option>
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.target")}
          </span>
          <input
            type="number"
            className="vy-field"
            min={1}
            max={7}
            disabled={cadence === "daily"}
            value={target}
            onChange={(event) => setTarget(Number(event.target.value))}
          />
        </label>
        <p className="text-[11px] leading-relaxed text-silver-500">{t("assistant.habitHint")}</p>
        <div className="flex gap-2">
          <button type="submit" className="vy-btn vy-btn-primary" disabled={busy}>
            {t("assistant.save")}
          </button>
          {editing && (
            <button type="button" className="vy-btn" disabled={busy} onClick={reset}>
              {t("assistant.cancel")}
            </button>
          )}
        </div>
      </form>

      <div className="space-y-3">
        {snapshot.habits.length === 0 ? (
          <Empty label={t("assistant.empty")} />
        ) : (
          snapshot.habits.map((habit) => (
            <article key={habit.id} className="vy-panel p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="text-sm text-silver-100">{habit.name}</h3>
                  <p className="mt-1 text-[11px] text-silver-500">
                    {habit.cadence === "daily"
                      ? t("assistant.daily")
                      : `${habit.target_per_week} ${t("assistant.perWeek")}`}
                    {" · "}
                    {t("assistant.streak")} {habit.streak}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={`vy-btn h-8 px-3 text-xs ${habit.done_today ? "vy-btn-primary" : ""}`}
                    disabled={busy || habit.done_today}
                    onClick={() => void mutate(() => completeHabit(habit.id))}
                  >
                    {habit.done_today ? t("assistant.doneToday") : t("assistant.markDone")}
                  </button>
                  <ItemActions
                    disabled={busy}
                    onEdit={() => {
                      setEditing(habit);
                      setName(habit.name);
                      setCadence(habit.cadence);
                      setTarget(habit.target_per_week);
                    }}
                    onDelete={() => void mutate(() => deleteHabit(habit.id))}
                  />
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}

function GoalSection({ snapshot, busy, mutate }: SectionProps) {
  const { t } = useI18n();
  const [editing, setEditing] = useState<AssistantGoal | null>(null);
  const [title, setTitle] = useState("");
  const [target, setTarget] = useState(10);
  const [progress, setProgress] = useState(0);
  const [deadline, setDeadline] = useState("");

  const reset = () => {
    setEditing(null);
    setTitle("");
    setTarget(10);
    setProgress(0);
    setDeadline("");
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const date = deadline ? new Date(`${deadline}T23:59:59`).toISOString() : "";
    if (
      await mutate(() =>
        saveGoal({ id: editing?.id, title, target: Number(target), progress: Number(progress), deadline: date }),
      )
    ) {
      reset();
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[330px_1fr]">
      <form className="vy-panel h-fit space-y-3 p-5" onSubmit={(event) => void submit(event)}>
        <h2 className="font-display text-lg tracking-wide text-silver-100">
          {editing ? t("assistant.edit") : t("assistant.add")}
        </h2>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.titleField")}
          </span>
          <input
            className="vy-field"
            required
            maxLength={200}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
              {t("assistant.target")}
            </span>
            <input
              type="number"
              className="vy-field"
              min={1}
              value={target}
              onChange={(event) => setTarget(Number(event.target.value))}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
              {t("assistant.progress")}
            </span>
            <input
              type="number"
              className="vy-field"
              min={0}
              value={progress}
              onChange={(event) => setProgress(Number(event.target.value))}
            />
          </label>
        </div>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.deadline")}
          </span>
          <input
            type="date"
            className="vy-field"
            value={deadline}
            onChange={(event) => setDeadline(event.target.value)}
          />
        </label>
        <p className="text-[11px] leading-relaxed text-silver-500">{t("assistant.goalHint")}</p>
        <div className="flex gap-2">
          <button type="submit" className="vy-btn vy-btn-primary" disabled={busy}>
            {t("assistant.save")}
          </button>
          {editing && (
            <button type="button" className="vy-btn" disabled={busy} onClick={reset}>
              {t("assistant.cancel")}
            </button>
          )}
        </div>
      </form>

      <div className="space-y-3">
        {snapshot.goals.length === 0 ? (
          <Empty label={t("assistant.empty")} />
        ) : (
          snapshot.goals.map((goal) => {
            const percent = Math.min(100, Math.round((goal.progress / goal.target) * 100));
            return (
              <article key={goal.id} className="vy-panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="text-sm text-silver-100">{goal.title}</h3>
                    <p className="mt-1 text-[11px] text-silver-500">
                      {goal.progress}/{goal.target}
                      {goal.deadline ? ` · ${formatDate(goal.deadline)}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {goal.status !== "done" && (
                      <button
                        type="button"
                        className="vy-btn h-8 px-3 text-xs"
                        disabled={busy}
                        onClick={() =>
                          void mutate(() =>
                            saveGoal({
                              id: goal.id,
                              title: goal.title,
                              target: goal.target,
                              progress: Math.min(goal.target, goal.progress + 1),
                              deadline: goal.deadline,
                            }),
                          )
                        }
                      >
                        +1
                      </button>
                    )}
                    <ItemActions
                      disabled={busy}
                      onEdit={() => {
                        setEditing(goal);
                        setTitle(goal.title);
                        setTarget(goal.target);
                        setProgress(goal.progress);
                        setDeadline(toDateInput(goal.deadline));
                      }}
                      onDelete={() => void mutate(() => deleteGoal(goal.id))}
                    />
                  </div>
                </div>
                <div className="vy-progress mt-4">
                  <span style={{ width: `${percent}%` }} />
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}

function TaskSection({ snapshot, busy, mutate }: SectionProps) {
  const { t } = useI18n();
  const [editing, setEditing] = useState<AssistantTask | null>(null);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [dueAt, setDueAt] = useState(nextHour);

  const reset = () => {
    setEditing(null);
    setTitle("");
    setNotes("");
    setDueAt(nextHour());
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (await mutate(() => saveTask({ id: editing?.id, title, notes, due_at: fromLocalInput(dueAt) }))) {
      reset();
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[330px_1fr]">
      <form className="vy-panel h-fit space-y-3 p-5" onSubmit={(event) => void submit(event)}>
        <h2 className="font-display text-lg tracking-wide text-silver-100">
          {editing ? t("assistant.edit") : t("assistant.add")}
        </h2>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.titleField")}
          </span>
          <input
            className="vy-field"
            required
            maxLength={200}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.notes")}
          </span>
          <textarea
            className="vy-field min-h-[100px] resize-y"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
            {t("assistant.due")}
          </span>
          <input
            type="datetime-local"
            className="vy-field"
            required
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
          />
        </label>
        <p className="text-[11px] leading-relaxed text-silver-500">{t("assistant.taskHint")}</p>
        <div className="flex gap-2">
          <button type="submit" className="vy-btn vy-btn-primary" disabled={busy}>
            {t("assistant.save")}
          </button>
          {editing && (
            <button type="button" className="vy-btn" disabled={busy} onClick={reset}>
              {t("assistant.cancel")}
            </button>
          )}
        </div>
      </form>

      <div className="space-y-3">
        {snapshot.tasks.length === 0 ? (
          <Empty label={t("assistant.empty")} />
        ) : (
          snapshot.tasks.map((task) => {
            const completed = task.status === "done";
            return (
              <article key={task.id} className="vy-panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3
                        className={`text-sm ${
                          completed ? "text-silver-500 line-through" : "text-silver-100"
                        }`}
                      >
                        {task.title}
                      </h3>
                      {task.overdue && !completed && (
                        <span className="font-display text-[9px] uppercase tracking-[0.14em] text-accent">
                          {t("assistant.overdue")}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-[11px] text-silver-500">{formatWhen(task.due_at)}</p>
                    {task.notes && (
                      <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-silver-400">
                        {task.notes}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="vy-btn h-8 px-3 text-xs"
                      disabled={busy}
                      onClick={() => void mutate(() => completeTask(task.id, !completed))}
                    >
                      {completed ? t("assistant.reopen") : t("assistant.complete")}
                    </button>
                    <ItemActions
                      disabled={busy}
                      onEdit={() => {
                        setEditing(task);
                        setTitle(task.title);
                        setNotes(task.notes);
                        setDueAt(toLocalInput(task.due_at));
                      }}
                      onDelete={() => void mutate(() => deleteTask(task.id))}
                    />
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}

export function AssistantScreen() {
  const { t } = useI18n();
  const [snapshot, setSnapshot] = useState<AssistantSnapshot | null>(null);
  const [tab, setTab] = useState<Tab>("memories");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const core = assistantCoreKind();

  const refresh = useCallback(async () => {
    try {
      setSnapshot(await loadAssistant());
      setError(null);
    } catch (cause) {
      setError((cause as Error).message || t("assistant.error"));
    }
  }, [t]);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const mutate = useCallback<Mutate>(
    async (action) => {
      setBusy(true);
      setError(null);
      try {
        await action();
        await refresh();
        return true;
      } catch (cause) {
        setError((cause as Error).message || t("assistant.error"));
        return false;
      } finally {
        setBusy(false);
      }
    },
    [refresh, t],
  );

  if (!snapshot) {
    return (
      <div className="mx-auto w-full max-w-content px-6 py-6">
        <p className="text-sm text-silver-500">{error ?? t("assistant.loading")}</p>
      </div>
    );
  }

  const overdueCount =
    snapshot.reminders.filter((reminder) => reminder.overdue).length +
    snapshot.tasks.filter((task) => task.overdue && task.status !== "done").length;
  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "memories", label: t("assistant.memories"), count: snapshot.memories.length },
    { id: "reminders", label: t("assistant.reminders"), count: snapshot.reminders.length },
    { id: "habits", label: t("assistant.habits"), count: snapshot.habits.length },
    { id: "goals", label: t("assistant.goals"), count: snapshot.goals.length },
    { id: "tasks", label: t("assistant.tasks"), count: snapshot.tasks.length },
  ];

  return (
    <div className="mx-auto w-full max-w-content px-6 py-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl tracking-wide text-silver-100">
            {t("assistant.title")}
          </h1>
          <p className="mt-1 text-xs text-silver-500">{t("assistant.subtitle")}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="vy-label hidden sm:inline">
            {core === "rust" ? t("assistant.core") : t("assistant.preview")}
          </span>
          <button type="button" className="vy-btn h-8 px-3 text-xs" disabled={busy} onClick={() => void refresh()}>
            {t("assistant.refresh")}
          </button>
        </div>
      </div>

      {overdueCount > 0 && (
        <p
          className="mb-4 border-l-2 px-3 py-2 text-xs text-silver-300"
          style={{ borderColor: "var(--vy-accent-500)" }}
        >
          {t("assistant.overdueCount", { count: overdueCount })}
        </p>
      )}
      {error && (
        <p
          className="mb-4 border-l-2 px-3 py-2 text-xs text-silver-300"
          style={{ borderColor: "var(--vy-accent-500)" }}
        >
          {error}
        </p>
      )}

      <div className="mb-5 flex flex-wrap gap-1 border-b border-white/10 pb-2">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`vy-chip ${tab === item.id ? "text-silver-100" : ""}`}
            style={
              tab === item.id
                ? { boxShadow: "inset 0 0 0 1px var(--vy-accent-500)" }
                : undefined
            }
            onClick={() => setTab(item.id)}
          >
            {item.label}
            <span className="ml-2 font-mono text-[10px] opacity-60">{item.count}</span>
          </button>
        ))}
      </div>

      {tab === "memories" && <MemorySection snapshot={snapshot} busy={busy} mutate={mutate} />}
      {tab === "reminders" && <ReminderSection snapshot={snapshot} busy={busy} mutate={mutate} />}
      {tab === "habits" && <HabitSection snapshot={snapshot} busy={busy} mutate={mutate} />}
      {tab === "goals" && <GoalSection snapshot={snapshot} busy={busy} mutate={mutate} />}
      {tab === "tasks" && <TaskSection snapshot={snapshot} busy={busy} mutate={mutate} />}
    </div>
  );
}
