#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::{
    error::Error,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
};
use tauri::{Manager, State};

struct Backend {
    port: u16,
    token: String,
    child: Mutex<Option<Child>>,
}

impl Drop for Backend {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

#[derive(Serialize, Clone)]
struct BackendInfo {
    port: u16,
    token: String,
}

#[tauri::command]
fn backend_info(state: State<'_, Backend>) -> BackendInfo {
    BackendInfo {
        port: state.port,
        token: state.token.clone(),
    }
}

fn python_command() -> Result<Command, Box<dyn Error>> {
    let executable = if cfg!(windows) { "python" } else { "python3" };
    let mut command = Command::new(executable);
    command.args(["-m", "backend.main"]);

    let current = std::env::current_dir()?;
    let root = if current.join("backend").is_dir() {
        current
    } else if current
        .parent()
        .map(|parent| parent.join("backend").is_dir())
        .unwrap_or(false)
    {
        current.parent().map(Path::to_path_buf).unwrap_or(current)
    } else {
        current
    };
    command.current_dir(root);
    Ok(command)
}

fn spawn_backend(resource_dir: Option<PathBuf>) -> Result<Backend, Box<dyn Error>> {
    let mut command = if let Ok(path) = std::env::var("VEYRA_BACKEND_BIN") {
        Command::new(path)
    } else {
        let mut sibling: Option<PathBuf> = None;
        if let Ok(executable) = std::env::current_exe() {
            if let Some(directory) = executable.parent() {
                let candidate = directory.join("veyra-backend.exe");
                if candidate.is_file() {
                    sibling = Some(candidate);
                }
            }
        }

        if let Some(candidate) = sibling {
            Command::new(candidate)
        } else if let Some(candidate) = resource_dir
            .map(|directory| directory.join("veyra-backend.exe"))
            .filter(|candidate| candidate.is_file())
        {
            Command::new(candidate)
        } else {
            python_command()?
        }
    };

    command
        .arg("--handshake")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit());

    let mut child = command.spawn()?;
    let stdout = child
        .stdout
        .take()
        .ok_or("the backend produced no standard output")?;
    let mut reader = BufReader::new(stdout);

    let mut port: u16 = 0;
    let mut token = String::new();
    for _ in 0..5 {
        let mut line = String::new();
        if reader.read_line(&mut line)? == 0 {
            break;
        }
        let Ok(value) = serde_json::from_str::<serde_json::Value>(line.trim()) else {
            continue;
        };
        if value.get("type").and_then(|kind| kind.as_str()) == Some("veyra-ready") {
            port = value
                .get("port")
                .and_then(|item| item.as_u64())
                .unwrap_or(0) as u16;
            token = value
                .get("token")
                .and_then(|item| item.as_str())
                .unwrap_or_default()
                .to_string();
            break;
        }
    }

    if port == 0 || token.is_empty() {
        let _ = child.kill();
        return Err("the backend did not complete the handshake".into());
    }

    Ok(Backend {
        port,
        token,
        child: Mutex::new(Some(child)),
    })
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![backend_info])
        .setup(|app| {
            let resources = app.path().resource_dir().ok();
            let backend = match spawn_backend(resources) {
                Ok(backend) => backend,
                Err(error) => {
                    eprintln!("Veyra backend failed to start: {error}");
                    Backend {
                        port: 0,
                        token: String::new(),
                        child: Mutex::new(None),
                    }
                }
            };
            app.manage(backend);

            let show =
                tauri::menu::MenuItem::with_id(app, "show", "Show Veyra", true, None::<&str>)?;
            let quit =
                tauri::menu::MenuItem::with_id(app, "quit", "Quit Veyra", true, None::<&str>)?;
            let menu = tauri::menu::Menu::with_items(app, &[&show, &quit])?;

            tauri::tray::TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click {
                        button: tauri::tray::MouseButton::Left,
                        button_state: tauri::tray::MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // Closing the window keeps Veyra in the tray; quit from there.
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Veyra");
}
