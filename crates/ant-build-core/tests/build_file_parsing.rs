use ant_build_core::ant_project::inspect_build_file;
use tempfile::tempdir;

#[test]
fn extracts_project_name_default_target_and_targets_from_build_xml() {
    let sandbox = tempdir().expect("create tempdir");
    let build_file = sandbox.path().join("build.xml");

    std::fs::write(
        &build_file,
        r#"
        <project name="demo-project" default="compile">
          <target name="clean" />
          <target name="compile" />
          <target name="test" description="Run tests" />
        </project>
        "#,
    )
    .expect("write build.xml");

    let metadata = inspect_build_file(&build_file).expect("parse build file");

    assert_eq!(metadata.project_name, "demo-project");
    assert_eq!(metadata.default_target, "compile");
    assert_eq!(metadata.targets, vec!["clean", "compile", "test"]);
}
