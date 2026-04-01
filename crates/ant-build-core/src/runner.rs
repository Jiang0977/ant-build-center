use std::collections::BTreeMap;
use std::io;
use std::io::BufRead;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc;
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use crate::workspace::RuntimeSettings;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuildRequest {
    pub build_file: PathBuf,
    pub target: Option<String>,
    pub runtime: RuntimeSettings,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolvedBuildCommand {
    pub program: PathBuf,
    pub args: Vec<String>,
    pub working_directory: PathBuf,
    pub env: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BuildEvent {
    Stdout(String),
    Stderr(String),
    System(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuildSummary {
    pub success: bool,
    pub cancelled: bool,
    pub exit_code: Option<i32>,
    pub duration_ms: u128,
}

#[derive(Debug, Clone, Default)]
pub struct CancellationToken {
    cancelled: Arc<AtomicBool>,
}

pub fn resolve_build_command(request: &BuildRequest) -> io::Result<ResolvedBuildCommand> {
    resolve_build_command_with_env(request, &std::env::vars().collect())
}

pub fn resolve_build_command_with_env(
    request: &BuildRequest,
    env: &BTreeMap<String, String>,
) -> io::Result<ResolvedBuildCommand> {
    let java_home = path_if_present(&request.runtime.java_home)
        .or_else(|| env.get("JAVA_HOME").map(PathBuf::from));
    let ant_home = path_if_present(&request.runtime.ant_home)
        .or_else(|| env.get("ANT_HOME").map(PathBuf::from));
    let java_executable = java_home
        .as_ref()
        .map(|home| home.join("bin").join(java_binary_name()));
    let ant_launcher = ant_home
        .as_ref()
        .map(|home| home.join("lib").join("ant-launcher.jar"));
    let ant_executable = ant_home
        .as_ref()
        .map(|home| home.join("bin").join(ant_binary_name()));
    let ant_from_path = find_executable_in_path(env, ant_binary_name());

    let (program, mut args) = match (
        java_executable.as_ref(),
        ant_launcher.as_ref(),
        ant_executable.as_ref(),
    ) {
        (Some(java), Some(launcher), _) if java.exists() && launcher.exists() => (
            java.clone(),
            vec![
                "-jar".to_string(),
                launcher.to_string_lossy().into_owned(),
                "-f".to_string(),
                request.build_file.to_string_lossy().into_owned(),
            ],
        ),
        (_, _, Some(ant)) if ant.exists() => (
            ant.clone(),
            vec![
                "-f".to_string(),
                request.build_file.to_string_lossy().into_owned(),
            ],
        ),
        (_, _, _) if ant_from_path.as_ref().is_some_and(|ant| ant.exists()) => (
            ant_from_path.expect("checked ant_from_path"),
            vec![
                "-f".to_string(),
                request.build_file.to_string_lossy().into_owned(),
            ],
        ),
        _ => {
            return Err(io::Error::new(
                io::ErrorKind::NotFound,
                "no supported Ant runtime configuration found",
            ))
        }
    };

    if let Some(target) = request.target.as_ref().filter(|value| !value.is_empty()) {
        args.push(target.clone());
    }

    let mut env = BTreeMap::new();
    if let Some(java_home) = java_home {
        env.insert(
            "JAVA_HOME".to_string(),
            java_home.to_string_lossy().into_owned(),
        );
    }
    if let Some(ant_home) = ant_home {
        env.insert(
            "ANT_HOME".to_string(),
            ant_home.to_string_lossy().into_owned(),
        );
    }

    Ok(ResolvedBuildCommand {
        program,
        args,
        working_directory: request
            .build_file
            .parent()
            .unwrap_or_else(|| Path::new("."))
            .to_path_buf(),
        env,
    })
}

pub fn execute_build_streaming(
    request: &BuildRequest,
    cancellation_token: CancellationToken,
    mut on_event: impl FnMut(BuildEvent),
) -> io::Result<BuildSummary> {
    let resolved = resolve_build_command(request)?;
    let start = Instant::now();

    let mut child = Command::new(&resolved.program)
        .args(&resolved.args)
        .current_dir(&resolved.working_directory)
        .envs(&resolved.env)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| io::Error::new(io::ErrorKind::BrokenPipe, "stdout pipe not available"))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| io::Error::new(io::ErrorKind::BrokenPipe, "stderr pipe not available"))?;

    let (sender, receiver) = mpsc::channel();
    let stdout_handle = spawn_reader(stdout, sender.clone(), BuildEvent::Stdout);
    let stderr_handle = spawn_reader(stderr, sender.clone(), BuildEvent::Stderr);
    drop(sender);

    let mut cancelled = false;
    let status = loop {
        while let Ok(event) = receiver.try_recv() {
            on_event(event);
        }

        if cancellation_token.is_cancelled() && !cancelled {
            cancelled = true;
            let _ = child.kill();
            on_event(BuildEvent::System("build cancelled".to_string()));
        }

        if let Some(status) = child.try_wait()? {
            break status;
        }

        thread::sleep(Duration::from_millis(25));
    };

    let _ = stdout_handle.join();
    let _ = stderr_handle.join();

    while let Ok(event) = receiver.try_recv() {
        on_event(event);
    }

    Ok(BuildSummary {
        success: !cancelled && status.success(),
        cancelled,
        exit_code: status.code(),
        duration_ms: start.elapsed().as_millis(),
    })
}

impl CancellationToken {
    pub fn new() -> Self {
        Self {
            cancelled: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::SeqCst);
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::SeqCst)
    }
}

fn path_if_present(value: &str) -> Option<PathBuf> {
    if value.trim().is_empty() {
        None
    } else {
        Some(PathBuf::from(value))
    }
}

fn java_binary_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "java.exe"
    } else {
        "java"
    }
}

fn ant_binary_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "ant.bat"
    } else {
        "ant"
    }
}

fn find_executable_in_path(
    env: &BTreeMap<String, String>,
    executable_name: &str,
) -> Option<PathBuf> {
    let path = env.get("PATH")?;
    std::env::split_paths(path)
        .map(|directory| directory.join(executable_name))
        .find(|candidate| candidate.exists())
}

fn spawn_reader<R>(
    reader: R,
    sender: mpsc::Sender<BuildEvent>,
    map: fn(String) -> BuildEvent,
) -> thread::JoinHandle<()>
where
    R: io::Read + Send + 'static,
{
    thread::spawn(move || {
        let buffered = io::BufReader::new(reader);
        for line in buffered.lines() {
            match line {
                Ok(value) => {
                    if sender.send(map(value)).is_err() {
                        break;
                    }
                }
                Err(_) => break,
            }
        }
    })
}
