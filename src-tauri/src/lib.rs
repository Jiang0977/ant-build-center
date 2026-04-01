use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use ant_build_core::ant_project::inspect_build_file;
use ant_build_core::runner::{
    execute_build_streaming, BuildEvent, BuildRequest, CancellationToken,
};
use ant_build_core::workspace::{
    load_workspace, save_workspace, ProjectRecord, RuntimeSettings, Workspace,
};
use serde::{Deserialize, Serialize};
use tauri::{Emitter, Manager, State};
use uuid::Uuid;

#[derive(Clone, Default)]
struct AppState {
    workspace_lock: Arc<Mutex<()>>,
    running_build: Arc<Mutex<Option<RunningBuild>>>,
}

#[derive(Clone)]
struct RunningBuild {
    cancellation_token: CancellationToken,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct WorkspaceDto {
    version: u32,
    runtime: RuntimeSettingsDto,
    projects: Vec<ProjectRecordDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeSettingsDto {
    java_home: String,
    ant_home: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProjectRecordDto {
    id: String,
    path: String,
    name: String,
    default_target: String,
    targets: Vec<String>,
    last_status: String,
    last_run_at: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BuildLogEventDto {
    project_id: String,
    stream: &'static str,
    line: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BuildFinishedEventDto {
    project_id: String,
    success: bool,
    cancelled: bool,
    duration_ms: u128,
    message: Option<String>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default();

    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }));
    }

    builder
        .manage(AppState::default())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_workspace,
            add_projects,
            remove_project,
            save_runtime,
            run_build,
            cancel_build
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn get_workspace(state: State<'_, AppState>) -> Result<WorkspaceDto, String> {
    let workspace = load_current_workspace(&state).map_err(|error| error.to_string())?;
    Ok(workspace.into())
}

#[tauri::command]
fn add_projects(state: State<'_, AppState>, paths: Vec<String>) -> Result<WorkspaceDto, String> {
    let mut workspace = load_current_workspace(&state).map_err(|error| {
        clear_running_build(&state.running_build);
        error.to_string()
    })?;

    for raw_path in paths {
        let normalized = normalize_path(&raw_path);
        if workspace
            .projects
            .iter()
            .any(|project| project.path == normalized)
        {
            continue;
        }

        let metadata =
            inspect_build_file(Path::new(&normalized)).map_err(|error| error.to_string())?;
        workspace.projects.push(ProjectRecord {
            id: Uuid::new_v4().to_string(),
            path: normalized,
            name: metadata.project_name,
            default_target: metadata.default_target,
            targets: metadata.targets,
            last_status: "idle".to_string(),
            last_run_at: None,
        });
    }

    save_current_workspace(&state, &workspace).map_err(|error| error.to_string())?;
    Ok(workspace.into())
}

#[tauri::command]
fn remove_project(state: State<'_, AppState>, project_id: String) -> Result<WorkspaceDto, String> {
    let mut workspace = load_current_workspace(&state).map_err(|error| error.to_string())?;
    workspace
        .projects
        .retain(|project| project.id != project_id);
    save_current_workspace(&state, &workspace).map_err(|error| error.to_string())?;
    Ok(workspace.into())
}

#[tauri::command]
fn save_runtime(
    state: State<'_, AppState>,
    runtime: RuntimeSettingsDto,
) -> Result<WorkspaceDto, String> {
    let mut workspace = load_current_workspace(&state).map_err(|error| error.to_string())?;
    workspace.runtime = runtime.into();
    save_current_workspace(&state, &workspace).map_err(|error| error.to_string())?;
    Ok(workspace.into())
}

#[tauri::command]
fn run_build(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    project_id: String,
    target: Option<String>,
) -> Result<(), String> {
    {
        let mut running = state
            .running_build
            .lock()
            .map_err(|_| "failed to lock build state".to_string())?;
        if running.is_some() {
            return Err("A build is already running.".to_string());
        }

        *running = Some(RunningBuild {
            cancellation_token: CancellationToken::new(),
        });
    }

    let mut workspace = load_current_workspace(&state).map_err(|error| error.to_string())?;
    let project_index = workspace
        .projects
        .iter()
        .position(|project| project.id == project_id)
        .ok_or_else(|| {
            clear_running_build(&state.running_build);
            "Project not found.".to_string()
        })?;

    workspace.projects[project_index].last_status = "running".to_string();
    let build_file = PathBuf::from(workspace.projects[project_index].path.clone());
    let runtime = workspace.runtime.clone();
    save_current_workspace(&state, &workspace).map_err(|error| {
        clear_running_build(&state.running_build);
        error.to_string()
    })?;

    let build_request = BuildRequest {
        build_file,
        target,
        runtime,
    };
    let running_state = Arc::clone(&state.running_build);
    let workspace_lock = Arc::clone(&state.workspace_lock);
    let project_id_for_thread = project_id.clone();
    let cancellation_token = state
        .running_build
        .lock()
        .map_err(|_| "failed to lock build state".to_string())?
        .as_ref()
        .map(|build| build.cancellation_token.clone())
        .ok_or_else(|| "Build state disappeared before launch.".to_string())?;

    std::thread::spawn(move || {
        let build_result = execute_build_streaming(&build_request, cancellation_token, |event| {
            let payload = map_build_event(&project_id_for_thread, event);
            let _ = app.emit("build-log", payload);
        });

        match build_result {
            Ok(summary) => {
                let status_label = if summary.success {
                    "success"
                } else {
                    "failure"
                };
                let _ = update_project_after_build(
                    &workspace_lock,
                    &project_id_for_thread,
                    status_label,
                    Some(timestamp_string()),
                );
                let _ = app.emit(
                    "build-finished",
                    BuildFinishedEventDto {
                        project_id: project_id_for_thread.clone(),
                        success: summary.success,
                        cancelled: summary.cancelled,
                        duration_ms: summary.duration_ms,
                        message: if summary.cancelled {
                            Some("Build cancelled.".to_string())
                        } else if summary.success {
                            Some("Build finished successfully.".to_string())
                        } else {
                            Some("Build failed.".to_string())
                        },
                    },
                );
            }
            Err(error) => {
                let _ = update_project_after_build(
                    &workspace_lock,
                    &project_id_for_thread,
                    "failure",
                    Some(timestamp_string()),
                );
                let _ = app.emit(
                    "build-finished",
                    BuildFinishedEventDto {
                        project_id: project_id_for_thread.clone(),
                        success: false,
                        cancelled: false,
                        duration_ms: 0,
                        message: Some(error.to_string()),
                    },
                );
            }
        }

        clear_running_build(&running_state);
    });

    Ok(())
}

#[tauri::command]
fn cancel_build(state: State<'_, AppState>) -> Result<(), String> {
    let running = state
        .running_build
        .lock()
        .map_err(|_| "failed to lock build state".to_string())?;

    let build = running
        .as_ref()
        .ok_or_else(|| "No running build to cancel.".to_string())?;
    build.cancellation_token.cancel();
    Ok(())
}

fn load_current_workspace(state: &State<'_, AppState>) -> Result<Workspace, std::io::Error> {
    let _guard = state
        .workspace_lock
        .lock()
        .map_err(|_| std::io::Error::new(std::io::ErrorKind::Other, "workspace lock poisoned"))?;
    load_workspace(&workspace_file_path())
}

fn save_current_workspace(
    state: &State<'_, AppState>,
    workspace: &Workspace,
) -> Result<(), std::io::Error> {
    let _guard = state
        .workspace_lock
        .lock()
        .map_err(|_| std::io::Error::new(std::io::ErrorKind::Other, "workspace lock poisoned"))?;
    save_workspace(&workspace_file_path(), workspace)
}

fn update_project_after_build(
    workspace_lock: &Arc<Mutex<()>>,
    project_id: &str,
    next_status: &str,
    last_run_at: Option<String>,
) -> Result<(), std::io::Error> {
    let _guard = workspace_lock
        .lock()
        .map_err(|_| std::io::Error::new(std::io::ErrorKind::Other, "workspace lock poisoned"))?;

    let workspace_path = workspace_file_path();
    let mut workspace = load_workspace(&workspace_path)?;
    if let Some(project) = workspace
        .projects
        .iter_mut()
        .find(|project| project.id == project_id)
    {
        project.last_status = next_status.to_string();
        project.last_run_at = last_run_at;
        save_workspace(&workspace_path, &workspace)?;
    }

    Ok(())
}

fn workspace_file_path() -> PathBuf {
    let base = dirs::config_dir()
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));
    base.join("ant-build-center").join("workspace-v2.json")
}

fn normalize_path(raw_path: &str) -> String {
    let path = PathBuf::from(raw_path);
    if path.exists() {
        path.canonicalize()
            .unwrap_or(path)
            .to_string_lossy()
            .into_owned()
    } else {
        path.to_string_lossy().into_owned()
    }
}

fn clear_running_build(running_state: &Arc<Mutex<Option<RunningBuild>>>) {
    if let Ok(mut running) = running_state.lock() {
        *running = None;
    }
}

fn map_build_event(project_id: &str, event: BuildEvent) -> BuildLogEventDto {
    match event {
        BuildEvent::Stdout(line) => BuildLogEventDto {
            project_id: project_id.to_string(),
            stream: "stdout",
            line,
        },
        BuildEvent::Stderr(line) => BuildLogEventDto {
            project_id: project_id.to_string(),
            stream: "stderr",
            line,
        },
        BuildEvent::System(line) => BuildLogEventDto {
            project_id: project_id.to_string(),
            stream: "system",
            line,
        },
    }
}

fn timestamp_string() -> String {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string())
}

impl From<Workspace> for WorkspaceDto {
    fn from(value: Workspace) -> Self {
        Self {
            version: value.version,
            runtime: value.runtime.into(),
            projects: value.projects.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<RuntimeSettings> for RuntimeSettingsDto {
    fn from(value: RuntimeSettings) -> Self {
        Self {
            java_home: value.java_home,
            ant_home: value.ant_home,
        }
    }
}

impl From<RuntimeSettingsDto> for RuntimeSettings {
    fn from(value: RuntimeSettingsDto) -> Self {
        Self {
            java_home: value.java_home,
            ant_home: value.ant_home,
        }
    }
}

impl From<ProjectRecord> for ProjectRecordDto {
    fn from(value: ProjectRecord) -> Self {
        Self {
            id: value.id,
            path: value.path,
            name: value.name,
            default_target: value.default_target,
            targets: value.targets,
            last_status: value.last_status,
            last_run_at: value.last_run_at,
        }
    }
}
