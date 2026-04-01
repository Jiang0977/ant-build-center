use std::path::PathBuf;

use ant_build_core::workspace::{
    load_workspace, save_workspace, GroupRecord, ProjectRecord, RuntimeSettings, Workspace,
};
use tempfile::tempdir;

#[test]
fn loads_default_workspace_when_storage_file_is_missing() {
    let sandbox = tempdir().expect("create tempdir");
    let storage_path = PathBuf::from(sandbox.path()).join("workspace-v2.json");

    let workspace = load_workspace(&storage_path).expect("load default workspace");

    assert_eq!(workspace, Workspace::default());
    assert_eq!(workspace.version, 3);
    assert_eq!(
        workspace.groups,
        vec![GroupRecord {
            id: "default".to_string(),
            name: "Ungrouped".to_string(),
            expanded: true,
            system: true,
        }]
    );
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
        version: 3,
        runtime: RuntimeSettings {
            java_home: "C:/Java/jdk-21".to_string(),
            ant_home: "D:/Tools/apache-ant".to_string(),
        },
        groups: vec![
            GroupRecord {
                id: "default".to_string(),
                name: "Ungrouped".to_string(),
                expanded: true,
                system: true,
            },
            GroupRecord {
                id: "backend".to_string(),
                name: "Backend".to_string(),
                expanded: false,
                system: false,
            },
        ],
        projects: vec![ProjectRecord {
            id: "project-1".to_string(),
            path: "/tmp/example/build.xml".to_string(),
            name: "example".to_string(),
            default_target: "compile".to_string(),
            targets: vec!["compile".to_string(), "test".to_string()],
            last_status: "success".to_string(),
            last_run_at: Some("2026-04-01T16:30:00Z".to_string()),
            group_id: "backend".to_string(),
            order: 0,
        }],
    };

    save_workspace(&storage_path, &workspace).expect("save workspace");
    let loaded = load_workspace(&storage_path).expect("reload workspace");

    assert_eq!(loaded, workspace);
}

#[test]
fn upgrades_flat_v2_workspace_into_default_group() {
    let sandbox = tempdir().expect("create tempdir");
    let storage_path = PathBuf::from(sandbox.path()).join("workspace-v2.json");

    std::fs::write(
        &storage_path,
        r#"{
  "version": 2,
  "runtime": {
    "javaHome": "C:/Java/jdk-21",
    "antHome": "D:/Tools/apache-ant"
  },
  "projects": [
    {
      "id": "project-1",
      "path": "/tmp/example-a/build.xml",
      "name": "example-a",
      "defaultTarget": "compile",
      "targets": ["compile", "test"],
      "lastStatus": "idle",
      "lastRunAt": null
    },
    {
      "id": "project-2",
      "path": "/tmp/example-b/build.xml",
      "name": "example-b",
      "defaultTarget": "package",
      "targets": ["package"],
      "lastStatus": "success",
      "lastRunAt": "2026-04-01T16:30:00Z"
    }
  ]
}"#,
    )
    .expect("write flat workspace");

    let workspace = load_workspace(&storage_path).expect("upgrade workspace");

    assert_eq!(workspace.version, 3);
    assert_eq!(
        workspace.groups,
        vec![GroupRecord {
            id: "default".to_string(),
            name: "Ungrouped".to_string(),
            expanded: true,
            system: true,
        }]
    );
    assert_eq!(workspace.projects.len(), 2);
    assert_eq!(workspace.projects[0].group_id, "default");
    assert_eq!(workspace.projects[0].order, 0);
    assert_eq!(workspace.projects[1].group_id, "default");
    assert_eq!(workspace.projects[1].order, 1);
    assert_eq!(workspace.projects[1].last_status, "success");
    assert_eq!(
        workspace.projects[1].last_run_at.as_deref(),
        Some("2026-04-01T16:30:00Z")
    );
}

#[test]
fn preserves_reordered_group_positions_after_save_and_reload() {
    let sandbox = tempdir().expect("create tempdir");
    let storage_path = PathBuf::from(sandbox.path()).join("workspace-v3.json");

    let mut workspace = Workspace::default();
    workspace
        .create_group("backend", "Backend")
        .expect("create group");
    workspace
        .add_project_to_group(project("project-1", "example-a"), "backend")
        .expect("add project 1");
    workspace
        .add_project_to_group(project("project-2", "example-b"), "backend")
        .expect("add project 2");
    workspace
        .add_project_to_group(project("project-3", "example-c"), "backend")
        .expect("add project 3");
    workspace
        .move_projects(&["project-3".to_string()], "backend", 0)
        .expect("reorder group");

    save_workspace(&storage_path, &workspace).expect("save workspace");
    let loaded = load_workspace(&storage_path).expect("reload workspace");

    assert_eq!(find_project(&loaded, "project-3").order, 0);
    assert_eq!(find_project(&loaded, "project-1").order, 1);
    assert_eq!(find_project(&loaded, "project-2").order, 2);
}

#[test]
fn drops_duplicate_project_paths_when_loading_workspace() {
    let sandbox = tempdir().expect("create tempdir");
    let storage_path = PathBuf::from(sandbox.path()).join("workspace-v3.json");

    std::fs::write(
        &storage_path,
        r#"{
  "version": 3,
  "runtime": {
    "javaHome": "",
    "antHome": ""
  },
  "groups": [
    {
      "id": "default",
      "name": "Ungrouped",
      "expanded": true,
      "system": true
    },
    {
      "id": "backend",
      "name": "Backend",
      "expanded": true,
      "system": false
    }
  ],
  "projects": [
    {
      "id": "project-1",
      "path": "/tmp/example-a/build.xml",
      "name": "example-a",
      "defaultTarget": "compile",
      "targets": ["compile"],
      "lastStatus": "idle",
      "lastRunAt": null,
      "groupId": "backend",
      "order": 0
    },
    {
      "id": "project-2",
      "path": "/tmp/example-a/build.xml",
      "name": "example-a-duplicate",
      "defaultTarget": "test",
      "targets": ["test"],
      "lastStatus": "success",
      "lastRunAt": "2026-04-01T16:30:00Z",
      "groupId": "default",
      "order": 0
    }
  ]
}"#,
    )
    .expect("write duplicate workspace");

    let workspace = load_workspace(&storage_path).expect("load deduplicated workspace");

    assert_eq!(workspace.projects.len(), 1);
    assert_eq!(workspace.projects[0].id, "project-1");
    assert_eq!(workspace.projects[0].group_id, "backend");
    assert_eq!(workspace.projects[0].order, 0);
}

fn project(id: &str, name: &str) -> ProjectRecord {
    ProjectRecord {
        id: id.to_string(),
        path: format!("/tmp/{name}/build.xml"),
        name: name.to_string(),
        default_target: "compile".to_string(),
        targets: vec!["compile".to_string()],
        last_status: "idle".to_string(),
        last_run_at: None,
        group_id: "default".to_string(),
        order: 0,
    }
}

fn find_project<'a>(workspace: &'a Workspace, id: &str) -> &'a ProjectRecord {
    workspace
        .projects
        .iter()
        .find(|project| project.id == id)
        .expect("project to exist")
}
