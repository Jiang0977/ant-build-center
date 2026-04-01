use ant_build_core::workspace::{ProjectRecord, Workspace};

#[test]
fn creates_a_user_group_with_a_trimmed_name() {
    let mut workspace = Workspace::default();

    workspace
        .create_group("backend", "  Backend Services  ")
        .expect("create group");

    assert_eq!(workspace.groups.len(), 2);
    assert_eq!(workspace.groups[1].id, "backend");
    assert_eq!(workspace.groups[1].name, "Backend Services");
    assert!(workspace.groups[1].expanded);
    assert!(!workspace.groups[1].system);
}

#[test]
fn renames_a_user_group() {
    let mut workspace = Workspace::default();
    workspace
        .create_group("backend", "Backend")
        .expect("create group");

    workspace
        .rename_group("backend", "  Release Builds  ")
        .expect("rename group");

    assert_eq!(workspace.groups[1].name, "Release Builds");
}

#[test]
fn deleting_a_non_empty_group_moves_projects_into_default_group() {
    let mut workspace = Workspace::default();
    workspace
        .create_group("backend", "Backend")
        .expect("create group");
    workspace.projects.push(ProjectRecord {
        id: "project-1".to_string(),
        path: "/tmp/example/build.xml".to_string(),
        name: "example".to_string(),
        default_target: "compile".to_string(),
        targets: vec!["compile".to_string()],
        last_status: "idle".to_string(),
        last_run_at: None,
        group_id: "backend".to_string(),
        order: 0,
    });

    workspace.delete_group("backend").expect("delete group");

    assert_eq!(workspace.groups.len(), 1);
    assert_eq!(workspace.groups[0].id, "default");
    assert_eq!(workspace.projects[0].group_id, "default");
    assert_eq!(workspace.projects[0].order, 0);
}

#[test]
fn updates_group_expanded_state() {
    let mut workspace = Workspace::default();
    workspace
        .create_group("backend", "Backend")
        .expect("create group");

    workspace
        .set_group_expanded("backend", false)
        .expect("collapse group");

    assert!(!workspace.groups[1].expanded);
}
