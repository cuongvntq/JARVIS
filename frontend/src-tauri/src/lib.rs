use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct BackendProcess(Mutex<Option<CommandChild>>);

/// Kill a process AND its whole child tree on Windows.
///
/// The backend is bundled with PyInstaller `onefile`: the spawned `jarvis-server.exe`
/// is a bootloader that forks a child process which actually runs uvicorn and holds
/// port 8000. Killing only the direct `CommandChild` (the bootloader) leaves that
/// child alive as a zombie that keeps the port — so the next launch can't bind 8000
/// and login fails with "Không thể kết nối đến máy chủ". `taskkill /T` kills the tree.
#[cfg(windows)]
fn kill_process_tree(pid: u32) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let _ = std::process::Command::new("taskkill")
        .args(["/F", "/T", "/PID", &pid.to_string()])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}

/// Kill any leftover backend sidecar from a previous session (e.g. after a forced
/// close, crash, or Task Manager kill) so port 8000 is free before spawning a fresh
/// one. Safe on a single-user desktop: there is only ever one backend sidecar.
///
/// Uses a `jarvis-server*` wildcard so it matches both the runtime name
/// (`jarvis-server.exe`, after Tauri strips the target triple) and the raw bundled
/// name (`jarvis-server-x86_64-pc-windows-msvc.exe`) — depending on the build,
/// a crashed/force-killed leftover may carry either name.
#[cfg(all(windows, not(debug_assertions)))]
fn kill_stray_sidecars() {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let _ = std::process::Command::new("taskkill")
        .args(["/F", "/IM", "jarvis-server*.exe"])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // In dev mode, backend runs manually — only spawn sidecar in release builds
            #[cfg(not(debug_assertions))]
            {
                // Clear any zombie sidecar left by a previous session before spawning,
                // so port 8000 is free and the new backend can bind it.
                #[cfg(windows)]
                kill_stray_sidecars();

                let sidecar = app.shell().sidecar("jarvis-server").unwrap();
                let (_, child) = sidecar.spawn().expect("Failed to start backend sidecar");
                *app.state::<BackendProcess>().0.lock().unwrap() = Some(child);
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(child) = window
                    .app_handle()
                    .state::<BackendProcess>()
                    .0
                    .lock()
                    .unwrap()
                    .take()
                {
                    // Kill the whole tree (onefile bootloader + the real uvicorn child),
                    // otherwise the child keeps holding port 8000 after the app closes.
                    #[cfg(windows)]
                    kill_process_tree(child.pid());
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
