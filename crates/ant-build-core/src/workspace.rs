use std::fs;
use std::io;
use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Workspace {
    pub version: u32,
    pub runtime: RuntimeSettings,
    pub projects: Vec<ProjectRecord>,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct RuntimeSettings {
    pub java_home: String,
    pub ant_home: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProjectRecord {
    pub id: String,
    pub path: String,
    pub name: String,
    pub default_target: String,
    pub targets: Vec<String>,
    pub last_status: String,
    pub last_run_at: Option<String>,
}

impl Default for Workspace {
    fn default() -> Self {
        Self {
            version: 2,
            runtime: RuntimeSettings::default(),
            projects: Vec::new(),
        }
    }
}

pub fn load_workspace(path: &Path) -> io::Result<Workspace> {
    if !path.exists() {
        return Ok(Workspace::default());
    }

    let content = fs::read_to_string(path)?;
    serde_json::from_str(&content).map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))
}

pub fn save_workspace(path: &Path, workspace: &Workspace) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    let payload = serde_json::to_string_pretty(workspace)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    fs::write(path, payload)
}
