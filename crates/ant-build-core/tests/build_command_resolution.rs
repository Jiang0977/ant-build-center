use ant_build_core::runner::{resolve_build_command_with_env, BuildRequest};
use ant_build_core::workspace::RuntimeSettings;
use tempfile::tempdir;

#[test]
fn uses_java_launcher_when_java_and_ant_launcher_are_available() {
    let sandbox = tempdir().expect("create tempdir");
    let build_file = sandbox.path().join("build.xml");
    let java_home = sandbox.path().join("java-home");
    let ant_home = sandbox.path().join("ant-home");
    let java_bin_dir = java_home.join("bin");
    let ant_lib_dir = ant_home.join("lib");

    std::fs::create_dir_all(&java_bin_dir).expect("create java bin");
    std::fs::create_dir_all(&ant_lib_dir).expect("create ant lib");
    std::fs::write(&build_file, "<project name=\"demo\" default=\"compile\" />")
        .expect("write build file");
    std::fs::write(java_bin_dir.join(java_binary_name()), "").expect("write java binary");
    std::fs::write(ant_lib_dir.join("ant-launcher.jar"), "").expect("write ant launcher");

    let request = BuildRequest {
        build_file: build_file.clone(),
        target: Some("test".to_string()),
        runtime: RuntimeSettings {
            java_home: java_home.to_string_lossy().into_owned(),
            ant_home: ant_home.to_string_lossy().into_owned(),
        },
    };

    let command = resolve_build_command_with_env(&request, &std::collections::BTreeMap::new())
        .expect("resolve build command");

    assert_eq!(command.program, java_bin_dir.join(java_binary_name()));
    assert_eq!(
        command.args,
        vec![
            "-jar".to_string(),
            ant_lib_dir
                .join("ant-launcher.jar")
                .to_string_lossy()
                .into_owned(),
            "-f".to_string(),
            build_file.to_string_lossy().into_owned(),
            "test".to_string(),
        ]
    );
    assert_eq!(command.working_directory, sandbox.path());
    assert_eq!(
        command
            .env
            .get("JAVA_HOME")
            .expect("JAVA_HOME env")
            .as_str(),
        java_home.to_string_lossy().as_ref()
    );
    assert_eq!(
        command
            .env
            .get("ANT_HOME")
            .expect("ANT_HOME env")
            .as_str(),
        ant_home.to_string_lossy().as_ref()
    );
}

#[test]
fn falls_back_to_ant_script_when_launcher_is_missing() {
    let sandbox = tempdir().expect("create tempdir");
    let build_file = sandbox.path().join("build.xml");
    let ant_home = sandbox.path().join("ant-home");
    let ant_bin_dir = ant_home.join("bin");

    std::fs::create_dir_all(&ant_bin_dir).expect("create ant bin");
    std::fs::write(&build_file, "<project name=\"demo\" default=\"compile\" />")
        .expect("write build file");
    std::fs::write(ant_bin_dir.join(ant_binary_name()), "").expect("write ant binary");

    let request = BuildRequest {
        build_file: build_file.clone(),
        target: Some("package".to_string()),
        runtime: RuntimeSettings {
            java_home: String::new(),
            ant_home: ant_home.to_string_lossy().into_owned(),
        },
    };

    let command = resolve_build_command_with_env(&request, &std::collections::BTreeMap::new())
        .expect("resolve ant script command");

    assert_eq!(command.program, ant_bin_dir.join(ant_binary_name()));
    assert_eq!(
        command.args,
        vec![
            "-f".to_string(),
            build_file.to_string_lossy().into_owned(),
            "package".to_string(),
        ]
    );
    assert!(!command.env.contains_key("JAVA_HOME"));
    assert_eq!(
        command
            .env
            .get("ANT_HOME")
            .expect("ANT_HOME env")
            .as_str(),
        ant_home.to_string_lossy().as_ref()
    );
}

#[test]
fn discovers_java_and_ant_from_environment_variables() {
    let sandbox = tempdir().expect("create tempdir");
    let build_file = sandbox.path().join("build.xml");
    let java_home = sandbox.path().join("java-home");
    let ant_home = sandbox.path().join("ant-home");
    let java_bin_dir = java_home.join("bin");
    let ant_bin_dir = ant_home.join("bin");

    std::fs::create_dir_all(&java_bin_dir).expect("create java bin");
    std::fs::create_dir_all(&ant_bin_dir).expect("create ant bin");
    std::fs::write(&build_file, "<project name=\"demo\" default=\"compile\" />")
        .expect("write build file");
    std::fs::write(java_bin_dir.join(java_binary_name()), "").expect("write java binary");
    std::fs::write(ant_bin_dir.join(ant_binary_name()), "").expect("write ant binary");

    let request = BuildRequest {
        build_file: build_file.clone(),
        target: None,
        runtime: RuntimeSettings {
            java_home: String::new(),
            ant_home: String::new(),
        },
    };

    let env = std::collections::BTreeMap::from([
        (
            "JAVA_HOME".to_string(),
            java_home.to_string_lossy().into_owned(),
        ),
        (
            "ANT_HOME".to_string(),
            ant_home.to_string_lossy().into_owned(),
        ),
    ]);

    let command =
        resolve_build_command_with_env(&request, &env).expect("resolve command from env");

    assert_eq!(command.program, ant_bin_dir.join(ant_binary_name()));
    assert_eq!(
        command
            .env
            .get("JAVA_HOME")
            .expect("JAVA_HOME env")
            .as_str(),
        java_home.to_string_lossy().as_ref()
    );
    assert_eq!(
        command
            .env
            .get("ANT_HOME")
            .expect("ANT_HOME env")
            .as_str(),
        ant_home.to_string_lossy().as_ref()
    );
}

#[test]
fn falls_back_to_ant_from_path_when_ant_home_is_missing() {
    let sandbox = tempdir().expect("create tempdir");
    let build_file = sandbox.path().join("build.xml");
    let bin_dir = sandbox.path().join("bin");

    std::fs::create_dir_all(&bin_dir).expect("create bin dir");
    std::fs::write(&build_file, "<project name=\"demo\" default=\"compile\" />")
        .expect("write build file");
    std::fs::write(bin_dir.join(ant_binary_name()), "").expect("write ant binary");

    let request = BuildRequest {
        build_file: build_file.clone(),
        target: Some("release".to_string()),
        runtime: RuntimeSettings {
            java_home: String::new(),
            ant_home: String::new(),
        },
    };

    let env = std::collections::BTreeMap::from([(
        "PATH".to_string(),
        bin_dir.to_string_lossy().into_owned(),
    )]);

    let command =
        resolve_build_command_with_env(&request, &env).expect("resolve command from PATH");

    assert_eq!(command.program, bin_dir.join(ant_binary_name()));
    assert_eq!(
        command.args,
        vec![
            "-f".to_string(),
            build_file.to_string_lossy().into_owned(),
            "release".to_string(),
        ]
    );
    assert!(!command.env.contains_key("ANT_HOME"));
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
