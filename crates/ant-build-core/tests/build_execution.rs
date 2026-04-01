#![cfg(unix)]

use std::sync::{Arc, Mutex};

use ant_build_core::runner::{
    execute_build_streaming, BuildEvent, BuildRequest, CancellationToken,
};
use ant_build_core::workspace::RuntimeSettings;
use tempfile::tempdir;

#[test]
fn streams_stdout_and_stderr_and_reports_success() {
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
    std::fs::write(ant_lib_dir.join("ant-launcher.jar"), "").expect("write ant launcher");
    write_fake_java(
        &java_bin_dir.join(java_binary_name()),
        r#"printf 'build-started\n'; printf 'warn-line\n' >&2"#,
    );

    let request = BuildRequest {
        build_file,
        target: Some("compile".to_string()),
        runtime: RuntimeSettings {
            java_home: java_home.to_string_lossy().into_owned(),
            ant_home: ant_home.to_string_lossy().into_owned(),
        },
    };

    let events = Arc::new(Mutex::new(Vec::new()));
    let event_sink = Arc::clone(&events);
    let summary = execute_build_streaming(
        &request,
        CancellationToken::new(),
        move |event| {
            event_sink.lock().expect("lock events").push(event);
        },
    )
    .expect("execute build");

    let captured = events.lock().expect("lock events");

    assert!(summary.success);
    assert!(!summary.cancelled);
    assert_eq!(summary.exit_code, Some(0));
    assert!(captured.contains(&BuildEvent::Stdout("build-started".to_string())));
    assert!(captured.contains(&BuildEvent::Stderr("warn-line".to_string())));
}

#[test]
fn cancels_running_process_after_first_output_line() {
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
    std::fs::write(ant_lib_dir.join("ant-launcher.jar"), "").expect("write ant launcher");
    write_fake_java(
        &java_bin_dir.join(java_binary_name()),
        r#"printf 'first-line\n'; sleep 3; printf 'second-line\n'"#,
    );

    let request = BuildRequest {
        build_file,
        target: None,
        runtime: RuntimeSettings {
            java_home: java_home.to_string_lossy().into_owned(),
            ant_home: ant_home.to_string_lossy().into_owned(),
        },
    };

    let cancel_token = CancellationToken::new();
    let cancel_clone = cancel_token.clone();
    let events = Arc::new(Mutex::new(Vec::new()));
    let event_sink = Arc::clone(&events);

    let summary = execute_build_streaming(&request, cancel_token, move |event| {
        if matches!(&event, BuildEvent::Stdout(line) if line == "first-line") {
            cancel_clone.cancel();
        }
        event_sink.lock().expect("lock events").push(event);
    })
    .expect("execute build");

    let captured = events.lock().expect("lock events");

    assert!(!summary.success);
    assert!(summary.cancelled);
    assert!(captured.contains(&BuildEvent::Stdout("first-line".to_string())));
    assert!(!captured.contains(&BuildEvent::Stdout("second-line".to_string())));
}

fn write_fake_java(path: &std::path::Path, body: &str) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;

        let script = format!("#!/bin/sh\n{body}\n");
        std::fs::write(path, script).expect("write fake java");
        let mut permissions = std::fs::metadata(path)
            .expect("metadata fake java")
            .permissions();
        permissions.set_mode(0o755);
        std::fs::set_permissions(path, permissions).expect("chmod fake java");
    }

    #[cfg(windows)]
    {
        let script = format!("@echo off\r\n{body}\r\n");
        std::fs::write(path, script).expect("write fake java");
    }
}

fn java_binary_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "java.exe"
    } else {
        "java"
    }
}
