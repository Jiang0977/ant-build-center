use std::path::PathBuf;

use ant_build_core::workspace::{
    load_workspace, save_workspace, ProjectRecord, RuntimeSettings, Workspace,
};
use tempfile::tempdir;

#[test]
fn loads_default_workspace_when_storage_file_is_missing() {
    let sandbox = tempdir().expect("create tempdir");
    let storage_path = PathBuf::from(sandbox.path()).join("workspace-v2.json");

    let workspace = load_workspace(&storage_path).expect("load default workspace");

    assert_eq!(workspace, Workspace::default());
    assert_eq!(workspace.version, 2);
    assert!(workspace.projects.is_empty());
    assert_eq!(workspace.runtime.java_home, "");
    assert_eq!(workspace.runtime.ant_home, "");
}

#[test]
fn saves_workspace_and_loads_it_back() {
    let sandbox = tempdir().expect("create tempdir");
    let storage_path = PathBuf::from(sandbox.path())
        .join("nested")
        .join("workspace-v2.json");

    let workspace = Workspace {
        version: 2,
        runtime: RuntimeSettings {
            java_home: "C:/Java/jdk-21".to_string(),
            ant_home: "D:/Tools/apache-ant".to_string(),
        },
        projects: vec![ProjectRecord {
            id: "project-1".to_string(),
            path: "/tmp/example/build.xml".to_string(),
            name: "example".to_string(),
            default_target: "compile".to_string(),
            targets: vec!["compile".to_string(), "test".to_string()],
            last_status: "success".to_string(),
            last_run_at: Some("2026-04-01T16:30:00Z".to_string()),
        }],
    };

    save_workspace(&storage_path, &workspace).expect("save workspace");
    let loaded = load_workspace(&storage_path).expect("reload workspace");

    assert_eq!(loaded, workspace);
}
