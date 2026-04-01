# Ant Build Center Tauri Rewrite

## 1. Overview

This document fixes the implementation direction for rewriting `ant-build-menu` as a Rust + Tauri desktop application.

The rewrite still intentionally narrows scope:

- Keep only the control-center experience.
- Add lightweight grouped file management inside the left rail.
- Remove right-click launch, registry integration, installer/uninstaller, Python runtime, and batch build.
- Do not preserve compatibility with the legacy Python `workspace.json`.

The existing `master` branch is the backup of the Python implementation. This rewrite happens only on `codex/tauri-control-center-rewrite`.

## 2. Product Goal

Ship a desktop control center that lets a user:

1. Create lightweight groups in the left rail.
2. Rename user-created groups.
3. Add one or more `build.xml` files into a chosen group.
4. Reorganize files with Ctrl/Cmd or Shift multi-select plus drag-and-drop.
5. Inspect the project name and available targets.
6. Choose one target and run a single Ant build.
7. Watch live build output.
8. Cancel a running build.
9. Persist grouped workspace state and runtime settings.

## 3. Non-Goals

- Windows Explorer right-click menu integration
- Registry writes or protocol stubs
- Installer / uninstaller flows
- Batch build or group-level batch build
- Nested groups or arbitrary tree depth
- Group color management or advanced metadata
- Legacy Python `workspace.json` migration
- Feature parity with the old Tk app outside the retained control-center use case

## 4. User Story

As a developer who works with multiple Ant projects, I want one desktop app that remembers my tracked `build.xml` files, lets me organize them into simple groups, and still runs one chosen target with live logs, so I do not need to manage builds manually in terminals.

## 5. Primary UX

```text
App launch
  -> load workspace
  -> if needed, upgrade flat workspace draft into grouped workspace
  -> render group list + tracked files

Add files
  -> user clicks "Add files"
  -> app asks which group should receive the files
  -> native file dialog returns one or more build.xml paths
  -> backend validates + parses targets
  -> backend deduplicates by normalized path
  -> backend assigns group + per-group order
  -> updated workspace returns to UI

Organize files
  -> user selects files with Ctrl/Cmd or Shift
  -> user drags the selection onto a group or relative to another file
  -> backend updates group membership + order
  -> UI re-renders without affecting build state

Run build
  -> user selects one file + target
  -> user starts build
  -> Rust process runner emits live logs
  -> UI shows success / failure / cancel state
```

Key interaction rules:

- The detail panel remains single-file focused even when the left rail has a multi-selection.
- Only file items participate in multi-select drag. Group headers are drop targets, not draggable items.
- Ctrl/Cmd toggles individual files.
- Shift selects a contiguous range of files within the current expanded group.
- Dropping on a group header appends to the end of that group.
- Dropping on a file inserts before or after that file based on pointer position.

## 6. Architecture

### 6.1 High-level split

```text
React UI
  -> invoke Tauri commands
  -> listen for build events
  -> manage rail selection + drag state

Rust application layer
  -> workspace storage
  -> grouped file membership + ordering
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
  - Group-tree layout, expanded state, single focus, and multi-select state
  - Drag indicator, drop highlighting, and confirmation modals
  - Group-aware add-file flow
  - Log rendering and build controls

- Rust backend
  - Workspace persistence and schema upgrade
  - Group CRUD with default-group invariants
  - File membership updates and per-group order normalization
  - XML parsing and target extraction
  - Ant / Java discovery
  - Running one build at a time
  - Streaming stdout / stderr lines to the UI
  - Cancelling the running build

### 6.3 Selected Approach

Selected implementation approach: keep `projects[]` as the buildable flat entity list, add first-class `groups[]`, and store each project's `groupId` plus per-group `order`.

Why this approach:

- It preserves the existing `projectId`-driven build execution path.
- It minimizes churn in `run_build`, `remove_project`, and build event handling.
- It still gives fully persisted groups, predictable drag-and-drop behavior, and room for future extension.

Alternatives considered:

- Nested `groups[].files[]`: clearer tree ownership, but higher backend churn for every build-state update.
- Separate membership tables: flexible, but unnecessary complexity for the current scope.

## 7. Data Model

Fresh grouped workspace schema:

```json
{
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
      "id": "uuid",
      "path": "/abs/path/build.xml",
      "name": "project-name",
      "defaultTarget": "compile",
      "targets": ["compile", "test"],
      "lastStatus": "idle",
      "lastRunAt": null,
      "groupId": "backend",
      "order": 0
    }
  ]
}
```

Notes:

- `version: 3` supersedes the earlier flat `version: 2` draft for this rewrite.
- A lightweight upgrade path is allowed from the current rewrite's flat v2 draft: synthesize the default group and preserve current file order there.
- This still does not imply any migration from the legacy Python `workspace.json`.
- Every project must belong to exactly one existing group.
- The default `Ungrouped` system group always exists and cannot be deleted.
- Deleting a non-empty user group moves its files into `Ungrouped` after explicit confirmation.
- `order` is normalized per group after add, move, and delete-group operations.

## 8. Runtime Behavior

### 8.1 Load workspace

```text
Frontend requests workspace
  -> Rust loads grouped workspace file
  -> if only flat v2 draft exists, Rust upgrades it into v3 with the default group
  -> Rust guarantees default group invariant
  -> grouped workspace returned to UI
```

### 8.2 Add group

```text
Frontend invokes create_group(name)
  -> Rust trims + validates name
  -> Rust appends a new user group
  -> workspace saved
  -> updated workspace returned
```

Group rules:

- New groups start expanded.
- Group names must be non-empty after trimming.
- The default system group is not deletable.

### 8.3 Rename group

```text
Frontend invokes rename_group(group_id, name)
  -> Rust validates that the target group exists and is user-editable
  -> Rust trims + validates name
  -> Rust updates the group name
  -> workspace saved
  -> updated workspace returned
```

Rename rules:

- User-defined groups can be renamed.
- The default system group keeps its fixed name.
- Empty names after trimming are rejected.

### 8.4 Add projects into a group

```text
Frontend opens an in-app group picker
  -> default target group = selected group, else Ungrouped
  -> native file dialog selects one or more XML files
  -> selected paths + target_group_id sent to Rust
  -> Rust validates XML + Ant project shape
  -> Rust deduplicates by normalized path
  -> Rust assigns groupId + next order in that group
  -> workspace saved
  -> updated workspace returned to UI
```

### 8.5 Move projects by drag-and-drop

```text
Frontend computes selected project ids in visual order
  -> user drags onto a group header or a file row
  -> frontend invokes move_projects(project_ids, target_group_id, target_index)
  -> Rust removes those projects from their prior group order
  -> Rust inserts them into the target group at the target index
  -> Rust normalizes per-group order values
  -> workspace saved
  -> updated workspace returned to UI
```

Rules:

- Moving within the same group is a reorder operation.
- Moving across groups changes both `groupId` and `order`.
- Dragging a selected file moves the entire file selection, not just the item under the cursor.

### 8.6 Delete group

```text
Frontend invokes delete_group(group_id)
  -> if group is empty, standard confirmation is enough
  -> if group contains files, UI shows an emphasized warning:
     "Delete group X? N files will move to Ungrouped."
  -> Rust moves the files to the default group
  -> Rust deletes the group
  -> Rust normalizes default-group order
  -> workspace saved
  -> updated workspace returned to UI
```

This guarantees that deleting a group never deletes the tracked files themselves.

### 8.7 Run build

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
- `src-tauri` already adapts that behavior to `build-log` and `build-finished` events with a single-build mutex.
- The grouped file-management work should preserve this build path rather than redesign it.

### 8.8 Cancel build

```text
Frontend invokes cancel_build()
  -> Rust checks running process handle
  -> Rust terminates child process
  -> Rust emits cancelled completion event
```

## 9. TDD Plan

Implementation follows thin vertical slices:

1. Grouped workspace schema
   - RED: loading flat v2 draft upgrades into grouped v3 state
   - GREEN: minimal group model + persistence invariants
   - REFACTOR: centralize default-group guarantees

2. Group CRUD
   - RED: create/rename/delete group behavior, including non-empty delete move-to-default
   - GREEN: minimal command handlers and order normalization
   - REFACTOR: isolate workspace mutation helpers

3. Multi-project move semantics
   - RED: move selected files across groups and within a group
   - GREEN: deterministic insertion logic in backend
   - REFACTOR: stabilize ordering helpers and edge cases

4. Frontend grouped rail
   - Add UI only after backend slices are green
   - Implement single focus + multi-select + drag feedback without changing build execution contracts

## 10. Test Strategy

- Rust unit/integration tests for grouped workspace storage and upgrade behavior
- Rust tests for group CRUD, delete-group move semantics, and multi-project reordering
- Existing Rust tests for command resolution and runner behavior
- Frontend lint/build verification
- Manual smoke test with grouped interactions plus a sample `build.xml`

Critical manual smoke path:

```text
Launch app
  -> create a new group
  -> add sample build.xml files into a chosen group
  -> Ctrl/Cmd select multiple files and drag them into another group
  -> Shift select a range within one group and reorder it
  -> delete a non-empty group and confirm the warning moves files to Ungrouped
  -> select one file, run build, and see live logs
  -> cancel or finish
  -> relaunch app and confirm groups + file placement persist
```

## 11. Success Criteria

- Users can create at least one additional group beyond `Ungrouped`.
- Users can rename any user-created group.
- Users can add files directly into a chosen group.
- Ctrl/Cmd multi-select and Shift range-select work predictably in the left rail.
- Dragging selected files persists both cross-group moves and within-group reordering.
- Deleting a non-empty group never deletes files and clearly states that files move to `Ungrouped`.
- Existing single-file build execution remains unchanged in behavior.

## 12. Risks

| Risk | Mitigation |
|------|------------|
| Schema upgrade from flat draft state introduces invalid group references | Centralize the default-group invariant and test the v2 -> v3 upgrade path |
| Multi-select and single-focus state diverge in the React rail | Keep focused project separate from selected project ids and test edge cases manually |
| Reordering logic becomes inconsistent after repeated drag operations | Normalize per-group order after every write and test cross-group / same-group moves explicitly |
| Group-management UI adds too much friction to the common add-file flow | Preselect the current group and keep `Ungrouped` as a one-click fallback |
| Build status updates drift from the selected grouped model | Preserve the existing flat `projectId` build path and only extend workspace metadata |

## 13. Open Questions

- Should folder import return as a group-aware follow-up feature, or should the grouped release stay file-picker-only?
