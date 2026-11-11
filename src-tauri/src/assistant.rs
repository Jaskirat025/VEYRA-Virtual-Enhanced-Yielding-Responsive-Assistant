//! Native personal-memory core for the Tauri shell.
//!
//! The core owns the assistant-facing slices of the shared `veyra.db`:
//! notes, timers, habits, goals and scheduled tasks. Conversations and the
//! tool log stay with the Python brain. Notes and timers use the exact tables
//! the Python tools already use, so both processes see one source of truth.

use chrono::{DateTime, Duration as ChronoDuration, Utc};
use rusqlite::{params, Connection, OptionalExtension, Row};
use serde::Serialize;
use std::{
    path::Path,
    sync::{Mutex, MutexGuard},
    time::Duration as StdDuration,
};
use tauri::State;

const SCHEMA: &str = r#"
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    fire_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cadence TEXT NOT NULL DEFAULT 'daily',
    target_per_week INTEGER NOT NULL DEFAULT 7,
    streak INTEGER NOT NULL DEFAULT 0,
    last_completed_on TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    target INTEGER NOT NULL DEFAULT 1,
    progress INTEGER NOT NULL DEFAULT 0,
    deadline TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    due_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes (updated_at);
CREATE INDEX IF NOT EXISTS idx_timers_pending ON timers (status, fire_at);
CREATE INDEX IF NOT EXISTS idx_tasks_pending ON scheduled_tasks (status, due_at);
"#;

pub struct AssistantCore {
    connection: Mutex<Connection>,
}

#[derive(Serialize)]
pub struct Memory {
    id: i64,
    title: String,
    body: String,
    created_at: String,
    updated_at: String,
}

#[derive(Serialize)]
pub struct Reminder {
    id: i64,
    label: String,
    fire_at: String,
    created_at: String,
    overdue: bool,
}

#[derive(Serialize)]
pub struct Habit {
    id: i64,
    name: String,
    cadence: String,
    target_per_week: i64,
    streak: i64,
    last_completed_on: String,
    done_today: bool,
}

#[derive(Serialize)]
pub struct Goal {
    id: i64,
    title: String,
    target: i64,
    progress: i64,
    deadline: String,
    status: String,
    updated_at: String,
}

#[derive(Serialize)]
pub struct ScheduledTask {
    id: i64,
    title: String,
    notes: String,
    due_at: String,
    status: String,
    created_at: String,
    completed_at: String,
    overdue: bool,
}

#[derive(Serialize)]
pub struct AssistantSnapshot {
    memories: Vec<Memory>,
    reminders: Vec<Reminder>,
    habits: Vec<Habit>,
    goals: Vec<Goal>,
    tasks: Vec<ScheduledTask>,
    generated_at: String,
}

impl AssistantCore {
    pub fn open(path: &Path) -> Result<Self, String> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|error| {
                format!("could not create the assistant data directory: {error}")
            })?;
        }

        let connection = Connection::open(path)
            .map_err(|error| format!("could not open the assistant database: {error}"))?;
        connection
            .busy_timeout(StdDuration::from_secs(3))
            .map_err(db_error)?;
        connection
            .execute_batch(
                "PRAGMA journal_mode=WAL; PRAGMA secure_delete=ON; PRAGMA foreign_keys=ON;",
            )
            .map_err(db_error)?;
        connection.execute_batch(SCHEMA).map_err(db_error)?;

        Ok(Self {
            connection: Mutex::new(connection),
        })
    }

    fn lock(&self) -> Result<MutexGuard<'_, Connection>, String> {
        self.connection
            .lock()
            .map_err(|_| "the assistant storage lock is poisoned".to_string())
    }

    pub fn snapshot(&self) -> Result<AssistantSnapshot, String> {
        let connection = self.lock()?;
        let today = today_string();

        let memories = {
            let mut statement = connection
                .prepare(
                    "SELECT id, title, body, created_at, updated_at FROM notes
                     ORDER BY datetime(updated_at) DESC, id DESC LIMIT 100",
                )
                .map_err(db_error)?;
            let rows = statement.query_map([], memory_from_row).map_err(db_error)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()
                .map_err(db_error)?
        };

        let reminders = {
            let mut statement = connection
                .prepare(
                    "SELECT id, label, fire_at, created_at,
                            CASE WHEN datetime(fire_at) <= datetime('now') THEN 1 ELSE 0 END
                     FROM timers WHERE status = 'pending'
                     ORDER BY datetime(fire_at), id LIMIT 100",
                )
                .map_err(db_error)?;
            let rows = statement
                .query_map([], reminder_from_row)
                .map_err(db_error)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()
                .map_err(db_error)?
        };

        let habits = {
            let mut statement = connection
                .prepare(
                    "SELECT id, name, cadence, target_per_week, streak, last_completed_on
                     FROM habits ORDER BY name COLLATE NOCASE, id LIMIT 100",
                )
                .map_err(db_error)?;
            let rows = statement
                .query_map([], |row| habit_from_row(row, &today))
                .map_err(db_error)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()
                .map_err(db_error)?
        };

        let goals = {
            let mut statement = connection
                .prepare(
                    "SELECT id, title, target, progress, deadline, status, updated_at
                     FROM goals
                     ORDER BY CASE WHEN status = 'done' THEN 1 ELSE 0 END,
                              CASE WHEN deadline = '' THEN 1 ELSE 0 END,
                              datetime(deadline), id LIMIT 100",
                )
                .map_err(db_error)?;
            let rows = statement.query_map([], goal_from_row).map_err(db_error)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()
                .map_err(db_error)?
        };

        let tasks = {
            let mut statement = connection
                .prepare(
                    "SELECT id, title, notes, due_at, status, created_at, completed_at,
                            CASE WHEN status = 'pending' AND datetime(due_at) <= datetime('now')
                                 THEN 1 ELSE 0 END
                     FROM scheduled_tasks
                     ORDER BY CASE WHEN status = 'done' THEN 1 ELSE 0 END,
                              datetime(due_at), id LIMIT 100",
                )
                .map_err(db_error)?;
            let rows = statement.query_map([], task_from_row).map_err(db_error)?;
            rows.collect::<rusqlite::Result<Vec<_>>>()
                .map_err(db_error)?
        };

        Ok(AssistantSnapshot {
            memories,
            reminders,
            habits,
            goals,
            tasks,
            generated_at: now_string(),
        })
    }

    fn save_memory(&self, id: Option<i64>, title: &str, body: &str) -> Result<Memory, String> {
        let title = clean_title(title, 200, "A memory title")?;
        let body = clean_body(body, 20_000)?;
        let connection = self.lock()?;
        let now = now_string();

        if let Some(id) = id {
            let changed = connection
                .execute(
                    "UPDATE notes SET title = ?, body = ?, updated_at = ? WHERE id = ?",
                    params![title, body, now, id],
                )
                .map_err(db_error)?;
            if changed == 0 {
                return Err("That memory no longer exists.".into());
            }
            return memory_by_id(&connection, id);
        }

        connection
            .execute(
                "INSERT INTO notes (title, body, created_at, updated_at) VALUES (?, ?, ?, ?)",
                params![title, body, now, now],
            )
            .map_err(db_error)?;
        memory_by_id(&connection, connection.last_insert_rowid())
    }

    fn delete_memory(&self, id: i64) -> Result<(), String> {
        let connection = self.lock()?;
        connection
            .execute("DELETE FROM notes WHERE id = ?", params![id])
            .map_err(db_error)?;
        Ok(())
    }

    fn save_reminder(&self, label: &str, fire_at: &str) -> Result<Reminder, String> {
        let label = clean_title(label, 200, "A reminder label")?;
        let fire_at = normalize_timestamp(fire_at, "A reminder time")?;
        let connection = self.lock()?;
        let now = now_string();
        connection
            .execute(
                "INSERT INTO timers (label, fire_at, status, created_at)
                 VALUES (?, ?, 'pending', ?)",
                params![label, fire_at, now],
            )
            .map_err(db_error)?;
        reminder_by_id(&connection, connection.last_insert_rowid())
    }

    fn delete_reminder(&self, id: i64) -> Result<(), String> {
        let connection = self.lock()?;
        connection
            .execute("DELETE FROM timers WHERE id = ?", params![id])
            .map_err(db_error)?;
        Ok(())
    }

    fn save_habit(
        &self,
        id: Option<i64>,
        name: &str,
        cadence: &str,
        target_per_week: i64,
    ) -> Result<Habit, String> {
        let name = clean_title(name, 120, "A habit name")?;
        let cadence = match cadence {
            "daily" => "daily",
            "weekly" => "weekly",
            _ => return Err("A habit cadence must be daily or weekly.".into()),
        };
        let target = if cadence == "daily" {
            7
        } else {
            target_per_week.clamp(1, 7)
        };
        let connection = self.lock()?;
        let today = today_string();

        if let Some(id) = id {
            let changed = connection
                .execute(
                    "UPDATE habits SET name = ?, cadence = ?, target_per_week = ? WHERE id = ?",
                    params![name, cadence, target, id],
                )
                .map_err(db_error)?;
            if changed == 0 {
                return Err("That habit no longer exists.".into());
            }
            return habit_by_id(&connection, id, &today);
        }

        connection
            .execute(
                "INSERT INTO habits (name, cadence, target_per_week, streak,
                                     last_completed_on, created_at)
                 VALUES (?, ?, ?, 0, '', ?)",
                params![name, cadence, target, now_string()],
            )
            .map_err(db_error)?;
        habit_by_id(&connection, connection.last_insert_rowid(), &today)
    }

    fn complete_habit(&self, id: i64) -> Result<Habit, String> {
        let connection = self.lock()?;
        let today = today_string();
        let (last, streak): (String, i64) = connection
            .query_row(
                "SELECT last_completed_on, streak FROM habits WHERE id = ?",
                params![id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .optional()
            .map_err(db_error)?
            .ok_or_else(|| "That habit no longer exists.".to_string())?;

        if last == today {
            return habit_by_id(&connection, id, &today);
        }

        let next_streak = if last == yesterday_string() {
            streak + 1
        } else {
            1
        };
        connection
            .execute(
                "UPDATE habits SET streak = ?, last_completed_on = ? WHERE id = ?",
                params![next_streak, today, id],
            )
            .map_err(db_error)?;
        habit_by_id(&connection, id, &today)
    }

    fn delete_habit(&self, id: i64) -> Result<(), String> {
        let connection = self.lock()?;
        connection
            .execute("DELETE FROM habits WHERE id = ?", params![id])
            .map_err(db_error)?;
        Ok(())
    }

    fn save_goal(
        &self,
        id: Option<i64>,
        title: &str,
        target: i64,
        progress: i64,
        deadline: &str,
    ) -> Result<Goal, String> {
        let title = clean_title(title, 200, "A goal title")?;
        let target = target.clamp(1, 1_000_000);
        let progress = progress.clamp(0, target);
        let deadline = if deadline.trim().is_empty() {
            String::new()
        } else {
            normalize_timestamp(deadline, "A goal deadline")?
        };
        let status = if progress >= target { "done" } else { "active" };
        let connection = self.lock()?;
        let now = now_string();

        if let Some(id) = id {
            let changed = connection
                .execute(
                    "UPDATE goals SET title = ?, target = ?, progress = ?, deadline = ?,
                                      status = ?, updated_at = ?
                     WHERE id = ?",
                    params![title, target, progress, deadline, status, now, id],
                )
                .map_err(db_error)?;
            if changed == 0 {
                return Err("That goal no longer exists.".into());
            }
            return goal_by_id(&connection, id);
        }

        connection
            .execute(
                "INSERT INTO goals (title, target, progress, deadline, status,
                                    created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)",
                params![title, target, progress, deadline, status, now, now],
            )
            .map_err(db_error)?;
        goal_by_id(&connection, connection.last_insert_rowid())
    }

    fn delete_goal(&self, id: i64) -> Result<(), String> {
        let connection = self.lock()?;
        connection
            .execute("DELETE FROM goals WHERE id = ?", params![id])
            .map_err(db_error)?;
        Ok(())
    }

    fn save_task(
        &self,
        id: Option<i64>,
        title: &str,
        notes: &str,
        due_at: &str,
    ) -> Result<ScheduledTask, String> {
        let title = clean_title(title, 200, "A task title")?;
        let notes = clean_body(notes, 8_000)?;
        let due_at = normalize_timestamp(due_at, "A task due time")?;
        let connection = self.lock()?;

        if let Some(id) = id {
            let changed = connection
                .execute(
                    "UPDATE scheduled_tasks SET title = ?, notes = ?, due_at = ? WHERE id = ?",
                    params![title, notes, due_at, id],
                )
                .map_err(db_error)?;
            if changed == 0 {
                return Err("That task no longer exists.".into());
            }
            return task_by_id(&connection, id);
        }

        connection
            .execute(
                "INSERT INTO scheduled_tasks (title, notes, due_at, status,
                                              created_at, completed_at)
                 VALUES (?, ?, ?, 'pending', ?, '')",
                params![title, notes, due_at, now_string()],
            )
            .map_err(db_error)?;
        task_by_id(&connection, connection.last_insert_rowid())
    }

    fn complete_task(&self, id: i64, completed: bool) -> Result<ScheduledTask, String> {
        let connection = self.lock()?;
        let status = if completed { "done" } else { "pending" };
        let completed_at = if completed {
            now_string()
        } else {
            String::new()
        };
        let changed = connection
            .execute(
                "UPDATE scheduled_tasks SET status = ?, completed_at = ? WHERE id = ?",
                params![status, completed_at, id],
            )
            .map_err(db_error)?;
        if changed == 0 {
            return Err("That task no longer exists.".into());
        }
        task_by_id(&connection, id)
    }

    fn delete_task(&self, id: i64) -> Result<(), String> {
        let connection = self.lock()?;
        connection
            .execute("DELETE FROM scheduled_tasks WHERE id = ?", params![id])
            .map_err(db_error)?;
        Ok(())
    }
}

fn db_error(error: rusqlite::Error) -> String {
    format!("assistant storage: {error}")
}

fn memory_from_row(row: &Row<'_>) -> rusqlite::Result<Memory> {
    Ok(Memory {
        id: row.get(0)?,
        title: row.get(1)?,
        body: row.get(2)?,
        created_at: row.get(3)?,
        updated_at: row.get(4)?,
    })
}

fn reminder_from_row(row: &Row<'_>) -> rusqlite::Result<Reminder> {
    Ok(Reminder {
        id: row.get(0)?,
        label: row.get(1)?,
        fire_at: row.get(2)?,
        created_at: row.get(3)?,
        overdue: row.get::<_, i64>(4)? != 0,
    })
}

fn habit_from_row(row: &Row<'_>, today: &str) -> rusqlite::Result<Habit> {
    let last_completed_on: String = row.get(5)?;
    Ok(Habit {
        id: row.get(0)?,
        name: row.get(1)?,
        cadence: row.get(2)?,
        target_per_week: row.get(3)?,
        streak: row.get(4)?,
        done_today: last_completed_on == today,
        last_completed_on,
    })
}

fn goal_from_row(row: &Row<'_>) -> rusqlite::Result<Goal> {
    Ok(Goal {
        id: row.get(0)?,
        title: row.get(1)?,
        target: row.get(2)?,
        progress: row.get(3)?,
        deadline: row.get(4)?,
        status: row.get(5)?,
        updated_at: row.get(6)?,
    })
}

fn task_from_row(row: &Row<'_>) -> rusqlite::Result<ScheduledTask> {
    Ok(ScheduledTask {
        id: row.get(0)?,
        title: row.get(1)?,
        notes: row.get(2)?,
        due_at: row.get(3)?,
        status: row.get(4)?,
        created_at: row.get(5)?,
        completed_at: row.get(6)?,
        overdue: row.get::<_, i64>(7)? != 0,
    })
}

fn memory_by_id(connection: &Connection, id: i64) -> Result<Memory, String> {
    connection
        .query_row(
            "SELECT id, title, body, created_at, updated_at FROM notes WHERE id = ?",
            params![id],
            memory_from_row,
        )
        .optional()
        .map_err(db_error)?
        .ok_or_else(|| "That memory no longer exists.".to_string())
}

fn reminder_by_id(connection: &Connection, id: i64) -> Result<Reminder, String> {
    connection
        .query_row(
            "SELECT id, label, fire_at, created_at,
                    CASE WHEN datetime(fire_at) <= datetime('now') THEN 1 ELSE 0 END
             FROM timers WHERE id = ?",
            params![id],
            reminder_from_row,
        )
        .optional()
        .map_err(db_error)?
        .ok_or_else(|| "That reminder no longer exists.".to_string())
}

fn habit_by_id(connection: &Connection, id: i64, today: &str) -> Result<Habit, String> {
    connection
        .query_row(
            "SELECT id, name, cadence, target_per_week, streak, last_completed_on
             FROM habits WHERE id = ?",
            params![id],
            |row| habit_from_row(row, today),
        )
        .optional()
        .map_err(db_error)?
        .ok_or_else(|| "That habit no longer exists.".to_string())
}

fn goal_by_id(connection: &Connection, id: i64) -> Result<Goal, String> {
    connection
        .query_row(
            "SELECT id, title, target, progress, deadline, status, updated_at
             FROM goals WHERE id = ?",
            params![id],
            goal_from_row,
        )
        .optional()
        .map_err(db_error)?
        .ok_or_else(|| "That goal no longer exists.".to_string())
}

fn task_by_id(connection: &Connection, id: i64) -> Result<ScheduledTask, String> {
    connection
        .query_row(
            "SELECT id, title, notes, due_at, status, created_at, completed_at,
                    CASE WHEN status = 'pending' AND datetime(due_at) <= datetime('now')
                         THEN 1 ELSE 0 END
             FROM scheduled_tasks WHERE id = ?",
            params![id],
            task_from_row,
        )
        .optional()
        .map_err(db_error)?
        .ok_or_else(|| "That task no longer exists.".to_string())
}

fn clean_title(raw: &str, max: usize, label: &str) -> Result<String, String> {
    let value = raw.trim();
    if value.is_empty() {
        return Err(format!("{label} is required."));
    }
    if value.chars().count() > max {
        return Err(format!("{label} is too long."));
    }
    Ok(value.to_string())
}

fn clean_body(raw: &str, max: usize) -> Result<String, String> {
    let value = raw.trim();
    if value.chars().count() > max {
        return Err("That text is too long.".into());
    }
    Ok(value.to_string())
}

fn normalize_timestamp(raw: &str, label: &str) -> Result<String, String> {
    let value = raw.trim();
    if value.is_empty() {
        return Err(format!("{label} is required."));
    }
    let parsed = DateTime::parse_from_rfc3339(value)
        .map_err(|_| format!("{label} must be a valid ISO date and time."))?;
    Ok(parsed
        .with_timezone(&Utc)
        .format("%Y-%m-%dT%H:%M:%S+00:00")
        .to_string())
}

fn now_string() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%S+00:00").to_string()
}

fn today_string() -> String {
    Utc::now().format("%Y-%m-%d").to_string()
}

fn yesterday_string() -> String {
    (Utc::now() - ChronoDuration::days(1))
        .format("%Y-%m-%d")
        .to_string()
}

#[tauri::command]
pub fn assistant_snapshot(core: State<'_, AssistantCore>) -> Result<AssistantSnapshot, String> {
    core.snapshot()
}

#[tauri::command]
pub fn assistant_save_memory(
    core: State<'_, AssistantCore>,
    id: Option<i64>,
    title: String,
    body: String,
) -> Result<Memory, String> {
    core.save_memory(id, &title, &body)
}

#[tauri::command]
pub fn assistant_delete_memory(core: State<'_, AssistantCore>, id: i64) -> Result<(), String> {
    core.delete_memory(id)
}

#[tauri::command]
pub fn assistant_save_reminder(
    core: State<'_, AssistantCore>,
    label: String,
    fire_at: String,
) -> Result<Reminder, String> {
    core.save_reminder(&label, &fire_at)
}

#[tauri::command]
pub fn assistant_delete_reminder(core: State<'_, AssistantCore>, id: i64) -> Result<(), String> {
    core.delete_reminder(id)
}

#[tauri::command]
pub fn assistant_save_habit(
    core: State<'_, AssistantCore>,
    id: Option<i64>,
    name: String,
    cadence: String,
    target_per_week: i64,
) -> Result<Habit, String> {
    core.save_habit(id, &name, &cadence, target_per_week)
}

#[tauri::command]
pub fn assistant_complete_habit(core: State<'_, AssistantCore>, id: i64) -> Result<Habit, String> {
    core.complete_habit(id)
}

#[tauri::command]
pub fn assistant_delete_habit(core: State<'_, AssistantCore>, id: i64) -> Result<(), String> {
    core.delete_habit(id)
}

#[tauri::command]
pub fn assistant_save_goal(
    core: State<'_, AssistantCore>,
    id: Option<i64>,
    title: String,
    target: i64,
    progress: i64,
    deadline: String,
) -> Result<Goal, String> {
    core.save_goal(id, &title, target, progress, &deadline)
}

#[tauri::command]
pub fn assistant_delete_goal(core: State<'_, AssistantCore>, id: i64) -> Result<(), String> {
    core.delete_goal(id)
}

#[tauri::command]
pub fn assistant_save_task(
    core: State<'_, AssistantCore>,
    id: Option<i64>,
    title: String,
    notes: String,
    due_at: String,
) -> Result<ScheduledTask, String> {
    core.save_task(id, &title, &notes, &due_at)
}

#[tauri::command]
pub fn assistant_complete_task(
    core: State<'_, AssistantCore>,
    id: i64,
    completed: bool,
) -> Result<ScheduledTask, String> {
    core.complete_task(id, completed)
}

#[tauri::command]
pub fn assistant_delete_task(core: State<'_, AssistantCore>, id: i64) -> Result<(), String> {
    core.delete_task(id)
}
