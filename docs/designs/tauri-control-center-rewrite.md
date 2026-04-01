# Ant Build Center Tauri Rewrite

## 1. Overview

This document fixes the implementation direction for rewriting `ant-build-menu` as a Rust + Tauri desktop application.

The rewrite intentionally narrows scope:

- Keep only the control-center experience.
- Remove right-click launch, registry integration, installer/uninstaller, Python runtime, and batch build.
- Do not preserve compatibility with the legacy `workspace.json`.

The existing `master` branch is the backup of the Python implementation. This rewrite happens only on `codex/tauri-control-center-rewrite`.

## 2. Product Goal

Ship a desktop control center that lets a user:

1. Add one or more `build.xml` files.
2. Inspect the project name and available targets.
3. Choose one target and run a single Ant build.
4. Watch live build output.
5. Cancel a running build.
6. Persist the tracked projects and runtime settings.

## 3. Non-Goals

- Windows Explorer right-click menu integration
- Registry writes or protocol stubs
- Installer / uninstaller flows
- Batch build
- Grouping, drag-and-drop sorting, and desktop shortcut creation
- Legacy `workspace.json` migration
- Feature parity with the old Tk app outside the retained control-center use case

## 4. User Story

As a developer who works with multiple Ant projects, I want one desktop app that remembers my tracked `build.xml` files and lets me run a chosen target with live logs, so I do not need to manage builds manually in terminals.

## 5. Primary UX

```text
App launch
  -> load workspace
  -> render tracked projects
  -> user adds build.xml files
  -> backend validates + parses targets
  -> user selects project + target
  -> user starts build
  -> Rust process runner emits live logs
  -> UI shows success / failure / cancel state
```

## 6. Architecture

### 6.1 High-level split

```text
React UI
  -> invoke Tauri commands
  -> listen for build events

Rust application layer
  -> workspace storage
  -> Ant file parsing
  -> Ant command resolution
  -> build process supervision
  -> event emission

Filesystem / OS
  -> workspace JSON
  -> build.xml files
  -> Java / Ant executables
```

### 6.2 Responsibilities

- Frontend
  - Layout, selection state, forms, and log rendering
  - Native file picker trigger
  - Displaying execution status and validation errors

- Rust backend
  - Workspace persistence
  - XML parsing and target extraction
  - Ant / Java discovery
  - Running one build at a time
  - Streaming stdout / stderr lines to the UI
  - Cancelling the running build

## 7. Data Model

Fresh workspace schema:

```json
{
  "version": 2,
  "runtime": {
    "javaHome": "",
    "antHome": ""
  },
  "projects": [
    {
      "id": "uuid",
      "path": "/abs/path/build.xml",
      "name": "project-name",
      "defaultTarget": "compile",
      "targets": ["compile", "test"],
      "lastStatus": "idle",
      "lastRunAt": null
    }
  ]
}
```

Notes:

- `version: 2` is a fresh namespace, not a migration from the Python file.
- `targets` are cached after parsing and refreshed when the project is re-read.
- `lastStatus` is UI-facing state only.

## 8. Runtime Behavior

### 8.1 Add project

```text
Frontend opens native file dialog
  -> selected paths sent to Rust
  -> Rust validates XML + Ant project shape
  -> Rust deduplicates by normalized path
  -> workspace saved
  -> updated workspace returned to UI
```

### 8.2 Run build

```text
Frontend invokes run_build(project_id, target)
  -> Rust resolves Java / Ant command
  -> Rust starts child process in build.xml parent directory
  -> Rust emits build-log events for stdout/stderr
  -> Rust polls child status
  -> Rust emits build-finished event
  -> Rust updates workspace lastStatus / lastRunAt
```

Current implementation status:

- `ant-build-core` already supports build command resolution, streamed execution, and cancellation.
- `src-tauri` now adapts that behavior to `build-log` and `build-finished` events with a single-build mutex.
- The Ubuntu 24.04 development host has the required GTK/WebKit stack installed and `src-tauri` tests now compile locally.

### 8.3 Cancel build

```text
Frontend invokes cancel_build()
  -> Rust checks running process handle
  -> Rust terminates child process
  -> Rust emits cancelled completion event
```

## 9. TDD Plan

Implementation follows thin vertical slices:

1. Workspace bootstrap
   - RED: empty storage loads default workspace
   - GREEN: minimal storage module
   - REFACTOR: clean file/path helpers

2. Ant project parsing
   - RED: valid `build.xml` returns project name/default target/targets
   - GREEN: minimal XML parser
   - REFACTOR: isolate validation rules

3. Build execution
   - RED: command resolution and process result behavior
   - GREEN: streamed runner, cancellation token, and event payloads
   - REFACTOR: narrow process supervision API

4. Frontend integration
   - Add UI only after Rust slices are green

## 10. Test Strategy

- Rust unit tests for workspace storage and XML parsing
- Rust tests for command resolution and runner behavior where possible
- Frontend lint/build verification
- Manual smoke test with a sample `build.xml`

Critical manual smoke path:

```text
Launch app
  -> add sample build.xml
  -> select target
  -> run build
  -> see live logs
  -> cancel or finish
  -> relaunch app and confirm project persists
```

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Tauri event API mismatch while streaming logs | Keep the event contract small and verify with a build smoke test early |
| Process cancellation behaves differently by OS | Start with single-process semantics and verify on the current dev OS first |
| XML validation rules drift from the old app | Add characterization tests using sample `build.xml` files in the repo |
| UI and backend diverge during rewrite | Frontend only consumes typed workspace and build-event contracts from Rust |

## 12. Open Questions

- Should runtime settings default strictly to environment variables, or should we also expose explicit path fields in the UI from v0.1?
- Should removing a project also clear any cached last run metadata immediately, or keep a short activity history elsewhere?
