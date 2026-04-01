use ant_build_core::workspace::{ProjectRecord, Workspace};

#[test]
fn adds_a_project_to_the_end_of_the_target_group() {
    let mut workspace = Workspace::default();
    workspace
        .create_group("backend", "Backend")
        .expect("create group");

    workspace
        .add_project_to_group(project("project-1", "example-a"), "backend")
        .expect("add first project");
    workspace
        .add_project_to_group(project("project-2", "example-b"), "backend")
        .expect("add second project");

    assert_eq!(workspace.projects[0].group_id, "backend");
    assert_eq!(workspace.projects[0].order, 0);
    assert_eq!(workspace.projects[1].group_id, "backend");
    assert_eq!(workspace.projects[1].order, 1);
}

#[test]
fn moves_selected_projects_as_a_block_into_the_target_group() {
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
        .add_project_to_group(project("project-3", "example-c"), "default")
        .expect("add project 3");

    workspace
        .move_projects(
            &["project-1".to_string(), "project-2".to_string()],
            "default",
            0,
        )
        .expect("move projects");

    assert_project(&workspace, "project-1", "default", 0);
    assert_project(&workspace, "project-2", "default", 1);
    assert_project(&workspace, "project-3", "default", 2);
}

#[test]
fn removing_a_project_keeps_remaining_group_order_compact() {
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
        .remove_project("project-1")
        .expect("remove project");

    assert_project(&workspace, "project-2", "backend", 0);
}

#[test]
fn ignores_a_project_with_a_duplicate_path_when_adding() {
    let mut workspace = Workspace::default();
    workspace
        .create_group("backend", "Backend")
        .expect("create group");

    workspace
        .add_project_to_group(project("project-1", "example-a"), "backend")
        .expect("add first project");
    workspace
        .add_project_to_group(project("project-2", "example-a"), "default")
        .expect("skip duplicate project");

    assert_eq!(workspace.projects.len(), 1);
    assert_project(&workspace, "project-1", "backend", 0);
}

#[test]
fn removes_multiple_selected_projects_and_compacts_each_group() {
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
        .add_project_to_group(project("project-3", "example-c"), "default")
        .expect("add project 3");
    workspace
        .add_project_to_group(project("project-4", "example-d"), "default")
        .expect("add project 4");

    workspace
        .remove_projects(&["project-1".to_string(), "project-3".to_string()])
        .expect("remove selected projects");

    assert_eq!(workspace.projects.len(), 2);
    assert_project(&workspace, "project-2", "backend", 0);
    assert_project(&workspace, "project-4", "default", 0);
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

fn assert_project(workspace: &Workspace, id: &str, group_id: &str, order: usize) {
    let project = workspace
        .projects
        .iter()
        .find(|project| project.id == id)
        .expect("project to exist");

    assert_eq!(project.group_id, group_id);
    assert_eq!(project.order, order);
}
