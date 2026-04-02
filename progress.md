# Progress Log

## Session: 2026-04-01

### Phase 1: Requirements & Discovery
- **Status:** complete
- **Started:** 2026-04-01 15:40
- Actions taken:
  - Reviewed the Python/Tk implementation, packaging, installer, registry, and control-center flows.
  - Assessed rewrite feasibility and scope reduction options.
  - Confirmed the user wants a control-center-only Rust + Tauri rewrite on a new branch.
- Files created/modified:
  - `.context/test-plans/jiang-master-test-plan-20260401-160037.md` (created)

### Phase 2: Planning & Structure
- **Status:** complete
- Actions taken:
  - Created branch `codex/tauri-control-center-rewrite`.
  - Read and switched to `frontend-design`, `doc-coauthoring`, `planning-with-files`, and `tdd` workflows.
  - Drafted planning files and the rewrite design doc.
- Files created/modified:
  - `task_plan.md` (created)
  - `findings.md` (created)
  - `progress.md` (created)
  - `docs/designs/tauri-control-center-rewrite.md` (created)

### Phase 3: Tauri Skeleton
- **Status:** complete
- Actions taken:
  - Scaffolded a React/TypeScript frontend with Vite.
  - Installed `@tauri-apps/cli`, initialized Tauri v2, and added `single-instance` and `dialog` plugins.
  - Replaced the legacy Python `src/` tree with the frontend `src/` tree on this rewrite branch.
  - Replaced the Vite starter UI with an app-specific control-center layout and Tauri API wrapper.
  - Removed the remaining legacy Python runtime entrypoints and outdated docs from this branch.
- Files created/modified:
  - `package.json`
  - `package-lock.json`
  - `index.html`
  - `vite.config.ts`
  - `src/`
  - `src-tauri/`
  - `.gitignore`
  - `docs/designs/tauri-control-center-rewrite.md`
  - `README.md`
  - `docs/development.md`

### Phase 4: TDD Slice 1 - Workspace Persistence
- **Status:** complete
- Actions taken:
  - Created `crates/ant-build-core` as a pure Rust domain crate.
  - Wrote an integration test asserting that a missing workspace file returns a version-2 default workspace.
  - Implemented the minimum `workspace` module needed to make that test pass.
  - Added a second integration test for workspace save/load roundtrip.
  - Implemented JSON persistence and parent directory creation for workspace storage.
- Files created/modified:
  - `crates/ant-build-core/Cargo.toml`
  - `crates/ant-build-core/src/lib.rs`
  - `crates/ant-build-core/src/workspace.rs`
  - `crates/ant-build-core/tests/workspace_bootstrap.rs`

### Phase 5: TDD Slice 2 - Project Parsing
- **Status:** complete
- Actions taken:
  - Wrote an integration test for parsing a valid `build.xml`.
  - Added `ant_project::inspect_build_file()` to the core crate.
  - Verified extraction of project name, default target, and target names.
- Files created/modified:
  - `crates/ant-build-core/src/ant_project.rs`
  - `crates/ant-build-core/src/lib.rs`
  - `crates/ant-build-core/Cargo.toml`
  - `crates/ant-build-core/tests/build_file_parsing.rs`

### Phase 6: TDD Slice 3 - Build Execution
- **Status:** complete
- Actions taken:
  - Wrote an integration test for Java + Ant launcher command resolution.
  - Added a minimal `runner` module that resolves the program, args, working directory, and environment variables for a build request.
  - Added integration tests for streamed stdout/stderr output and cancellation.
  - Implemented blocking build execution with line-by-line event callbacks and cancellation support.
  - Added fallback from `ant-launcher.jar` to `ANT_HOME/bin/ant`.
  - Added fallback from `ANT_HOME` lookup to `ant` discovered in `PATH`.
- Files created/modified:
  - `crates/ant-build-core/src/runner.rs`
  - `crates/ant-build-core/src/lib.rs`
  - `crates/ant-build-core/tests/build_command_resolution.rs`
  - `crates/ant-build-core/tests/build_execution.rs`

### Phase 7: Frontend Integration & Verification
- **Status:** in_progress
- Actions taken:
  - Replaced the starter React UI with a control-center layout and Tauri API wrapper.
  - Added Tauri shell commands for workspace loading, add/remove, and runtime saving.
  - Replaced Tauri build stubs with a single-build runtime state, build-log emission, build-finished emission, and cancellation wiring.
  - Installed the Ubuntu Tauri GTK/WebKit dependency stack and verified the shell now compiles/tests locally.
  - Added runtime discovery from `JAVA_HOME` / `ANT_HOME` when explicit overrides are empty.
  - Formatted the Tauri Rust code with `cargo fmt`.
- Files created/modified:
  - `src/App.tsx`
  - `src/App.css`
  - `src/index.css`
  - `src/lib/tauri.ts`
  - `src/types.ts`
  - `src-tauri/Cargo.toml`
  - `src-tauri/src/lib.rs`

### Phase 8: Grouped File Management Design Discovery
- **Status:** complete
- Actions taken:
  - Switched to the `planning-with-files` workflow for this feature discussion so discovery state is persisted in the repo.
  - Read the current React frontend, TS types, Rust workspace storage, and Tauri command adapters to identify where grouping would have to land.
  - Compared the current Tauri rewrite against the old Python implementation at commit `ea80b9c`, which already had grouped tree behavior and Ctrl/Shift multi-select drag/drop.
  - Confirmed the current rewrite uses a flat `projects[]` workspace, so this feature requires a workspace-schema and UX decision before code changes.
  - Ran the planning skill's session-catchup script; it reported no additional unsynced context for this workspace.
  - Confirmed with the user that this is an internal-project feature evolution; the decision bar is "ship correctly and quickly", not product-market validation.
  - Confirmed with the user that the existing design doc should be revised in place instead of creating a separate grouping addendum.
  - Confirmed the premise set for implementation planning: persisted groups, file-centric build actions, guarded non-empty group deletion, and group-aware add-file behavior.
  - Compared grouped-behavior details in the old Python implementation and confirmed two reusable rules: keep a default group invariant and move files there when deleting a non-empty group.
  - Revised `docs/designs/tauri-control-center-rewrite.md` to adopt Approach A, upgrade the workspace schema to grouped `version: 3`, and specify drag/drop, add-file, and delete-group behavior.
  - Confirmed that user-created groups must support rename in the first grouped release and updated the design doc accordingly.
- Files created/modified:
  - `docs/designs/tauri-control-center-rewrite.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### Phase 9: Grouped File Management Implementation
- **Status:** in_progress
- Actions taken:
  - Used `tdd` to drive the implementation in thin vertical slices instead of landing one large grouped-rail patch.
  - RED/GREEN slice 1: added failing workspace tests for grouped defaults and flat-v2 upgrade, then implemented grouped `version: 3` workspace loading with a default `Ungrouped` system group.
  - RED/GREEN slice 2: added failing group-management tests for create, rename, and delete, then implemented `Workspace::create_group`, `rename_group`, and `delete_group`.
  - RED/GREEN slice 3: added failing project-grouping tests for grouped add, grouped move, and grouped remove, then implemented `Workspace::add_project_to_group`, `move_projects`, and `remove_project`.
  - RED/GREEN slice 4: updated the Tauri command surface to expose group CRUD and grouped file moves, then rewrote the React left rail to render groups, select files with Ctrl/Cmd or Shift, drag selected files, choose an add target group, rename groups, and show a strong delete warning for non-empty groups.
  - Added a persistence regression test for same-group reorder after save/reload and fixed workspace normalization so stored `order` survives reloads.
  - Follow-up polish: replaced native `prompt` / `confirm` with project-styled group dialogs, added a persisted `set_group_expanded` command, and made empty expanded groups accept drag-and-drop through their full body area.
  - Follow-up bug fix: added regression tests for duplicate file paths, then enforced path uniqueness in the workspace layer so duplicate adds are ignored and older duplicate entries are compacted on load.
  - Follow-up interaction: added a bulk `remove_projects` workspace/Tauri path, then wired a custom right-click menu in the grouped rail so multi-selected files can be removed together with one confirmation dialog.
  - Follow-up interaction: removed the top-level rename/delete group buttons and moved those actions onto a group-row right-click context menu, keeping only `New group` in the toolbar.
- Files created/modified:
  - `crates/ant-build-core/src/workspace.rs`
  - `crates/ant-build-core/tests/workspace_bootstrap.rs`
  - `crates/ant-build-core/tests/group_management.rs`
  - `crates/ant-build-core/tests/project_grouping.rs`
  - `src-tauri/src/lib.rs`
  - `src/types.ts`
  - `src/lib/tauri.ts`
  - `src/App.tsx`
  - `src/App.css`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Tauri CLI availability | `npx tauri --help` | CLI usable in repo | Command succeeded | ✓ |
| Initial Rust test baseline | `cargo test` in `src-tauri` | Test harness starts | Blocked by missing `glib-2.0`, `gio-2.0`, `gdk-pixbuf-2.0` pkg-config libs | ✗ |
| Workspace bootstrap TDD | `cargo test` in `crates/ant-build-core` | Missing workspace file returns default workspace | 1 integration test passed | ✓ |
| Workspace persistence TDD | `cargo test` in `crates/ant-build-core` | Saved workspace reloads unchanged | 2 integration tests passed | ✓ |
| Build XML parsing TDD | `cargo test` in `crates/ant-build-core` | Valid Ant file yields project metadata and targets | 3 integration tests passed | ✓ |
| Build command resolution TDD | `cargo test` in `crates/ant-build-core` | Java launcher and ant-script fallback both resolve deterministically | 5 integration tests passed | ✓ |
| Runtime env discovery TDD | `cargo test --test build_command_resolution` in `crates/ant-build-core` | Empty runtime config resolves from `JAVA_HOME` / `ANT_HOME` | 3 command-resolution tests passed | ✓ |
| PATH fallback TDD | `cargo test --test build_command_resolution` in `crates/ant-build-core` | Empty `ANT_HOME` still resolves when `ant` exists in `PATH` | 4 command-resolution tests passed | ✓ |
| Build execution TDD | `cargo test` in `crates/ant-build-core` | Streamed output and cancellation both work | 7 integration tests passed | ✓ |
| Frontend lint | `npm run lint` | No React/TypeScript lint issues after UI rewrite | Succeeded | ✓ |
| Frontend production build | `npm run build` | React/Vite app compiles after UI rewrite and cleanup | Build succeeded | ✓ |
| Tauri shell formatting | `cargo fmt` in `src-tauri` | Rust shell source formats cleanly after command integration | Succeeded | ✓ |
| Tauri shell tests | `cargo test` in `src-tauri` | Desktop shell compiles on Ubuntu after system deps install | Succeeded | ✓ |
| Grouped workspace TDD | `cargo test --test workspace_bootstrap` in `crates/ant-build-core` | Grouped defaults, v2 upgrade, and reordered persistence all hold | 4 tests passed | ✓ |
| Group CRUD TDD | `cargo test --test group_management` in `crates/ant-build-core` | Create, rename, and delete-group move behavior all work | 3 tests passed | ✓ |
| Project grouping TDD | `cargo test --test project_grouping` in `crates/ant-build-core` | Grouped add, grouped move, and grouped remove keep order valid | 3 tests passed | ✓ |
| Group expanded-state TDD | `cargo test --test group_management` in `crates/ant-build-core` | Collapsed / expanded state persists through the workspace layer | 4 tests passed | ✓ |
| Duplicate path regression | `cargo test --test project_grouping` and `cargo test --test workspace_bootstrap` in `crates/ant-build-core` | Duplicate add attempts are ignored and duplicate saved paths are deduplicated on load | Passed | ✓ |
| Multi-delete regression | `cargo test --test project_grouping` in `crates/ant-build-core` | Removing multiple selected files keeps each group's remaining order compact | Passed | ✓ |
| Group action entrypoint update | `cargo test` in `src-tauri`, `npm run lint`, `npm run build` | Group rename/delete now triggered from right-click menu without breaking the grouped rail build | Passed | ✓ |
| Repository naming sweep | `rg -n "ant-build-menu|Ant Build Menu|AntBuildMenu|ant build menu" -S . --glob '!**/Cargo.lock' --glob '!package-lock.json'` | Only intentional historical references remain in planning notes | Passed | ✓ |
| Frontend build after rename alignment | `npm run build` | React/Vite app still builds after naming-only changes | Succeeded | ✓ |
| GitHub repository rename | `gh repo rename ant-build-center --yes`, `gh repo view --json nameWithOwner,url`, `git remote -v` | Remote repo slug and local `origin` both use `ant-build-center` | Succeeded | ✓ |
| Tauri shell maximize regression | `cargo test -q --manifest-path src-tauri/Cargo.toml --lib` | Config regression and maximize activation order both pass | 2 tests passed | ✓ |
| Post-bundle lint stability | `npm run lint` | ESLint stays green even after Tauri generated `src-tauri/target` assets exist | Succeeded | ✓ |
| Maximized startup package build | `npx tauri build --bundles deb` | Linux `.deb` rebuilt as `1.1.1` with maximized startup defaults | Succeeded | ✓ |
| Local package reinstall | `sudo dpkg -i 'src-tauri/target/release/bundle/deb/Ant Build Center_1.1.1_amd64.deb'` | Installed system package upgraded/reinstalled to corrected `1.1.1` build | Succeeded | ✓ |
| Desktop maximize smoke | `/usr/bin/ant-build-center`, `gnome-screenshot -w`, `gnome-screenshot`, `xrandr` | Installed app opens maximized, not fullscreen, on a 1920x1080 monitor | Active window captured at 1872x1048 with title bar visible | ✓ |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-04-01 16:06 | `cargo tauri` unavailable | 1 | Installed `@tauri-apps/cli` and used `npx tauri` |
| 2026-04-01 16:27 | Tauri crate required missing GTK/WebKit system libraries on this Linux host | 1 | Installed the official Ubuntu dependency set and unblocked local shell compilation |

## Session: 2026-04-02

### Maximized Default + Release 1.1.1
- **Status:** in_progress
- Actions taken:
  - Created branch `codex/default-maximized-release` from `master` before making release-scoped changes.
  - Inspected the Tauri window config and confirmed the app does not yet start maximized by default.
  - Inspected the single-instance activation path and confirmed it only focuses the existing window without restoring maximized state.
  - Verified GitHub publication prerequisites: `gh` is installed/authenticated, `origin` points at `Jiang0977/ant-build-center`, and the latest release is `v1.1.0`.
  - Updated the planning files to track this patch-release scope.
  - Confirmed from the local Tauri schema that `maximized` window config and `maximize()` runtime APIs are available.
  - Corrected the implementation target from fullscreen to maximized before commit/release, based on the user's clarification.
  - Added shell-level regression coverage for the default window config and the maximize-before-focus activation path.
  - Switched the startup behavior to maximized at both the Tauri config layer and the single-instance/setup activation path.
  - Added `src-tauri/target` to the global ESLint ignore list so `npm run lint` stays green after local bundle builds.
  - Rebuilt the Linux `.deb`, reinstalled `ant-build-center 1.1.1` locally, and verified the installed app opens maximized via GNOME screenshots.
- Files created/modified:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
  - `docs/designs/tauri-control-center-rewrite.md`
  - `src-tauri/src/lib.rs`
  - `src-tauri/tauri.conf.json`
  - `src-tauri/Cargo.toml`
  - `src-tauri/Cargo.lock`
  - `package.json`
  - `package-lock.json`
  - `eslint.config.js`

### Repository Naming Alignment
- **Status:** complete
- Actions taken:
  - Audited user-facing strings and metadata for stale `ant-build-menu` / `Ant Build Menu` references.
  - Updated README and design-doc wording to use `Ant Build Center` as the current repository/app name.
  - Updated Tauri/Cargo repository URLs to point at the renamed `ant-build-center` repository path.
  - Updated the sample Ant XML files so their example project name and help text match `Ant Build Center`.
  - Renamed the GitHub repository slug to `ant-build-center` with `gh repo rename ant-build-center --yes`.
  - Verified `origin` now points at `git@github.com:Jiang0977/ant-build-center.git`.
- Files created/modified:
  - `README.md`
  - `docs/designs/tauri-control-center-rewrite.md`
  - `src-tauri/tauri.conf.json`
  - `src-tauri/Cargo.toml`
  - `examples/build.xml`
  - `examples/sample_build.xml`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 7: core crate behavior is green, Tauri shell compiles locally, remaining work is product polish and manual smoke coverage |
| Where am I going? | Add manual smoke verification and tighten runtime discovery / UX edge cases |
| What's the goal? | Ship a Rust + Tauri control-center-only rewrite with fresh workspace storage |
| What have I learned? | See `findings.md` |
| What have I done? | See above; the next active discovery item is Phase 8 grouped file management |

### Last Run Display Fix
- **Status:** complete
- Actions taken:
  - Updated the `Selected File` panel to format `lastRunAt` as `yyyy-mm-dd hh-mm-ss` instead of showing the raw stored value.
  - Corrected the formatter to handle the real persisted shape in `~/.config/ant-build-center/workspace-v2.json`, where `lastRunAt` is stored as a Unix timestamp string rather than an ISO datetime.
  - Rebuilt the frontend, rebuilt the Tauri `.deb`, and reinstalled `ant-build-center` on the local Ubuntu 24.04 host.
  - Ran a manual smoke check against the installed app and verified the `LAST RUN` field now renders `2026-04-01 21-29-34` for the selected `build_x-web-new.xml` entry.
- Files created/modified:
  - `src/App.tsx`
  - `progress.md`
  - `findings.md`
  - `task_plan.md`

### Linux Dock Icon Fix
- **Status:** complete
- Actions taken:
  - Searched local memory and found the prior Tauri/GNOME dock icon fix pattern.
  - Updated Debian bundling so the default `Ant Build Center.desktop` entry is hidden and an additional visible desktop file named `io.github.jiang0977.ant-build-center.desktop` is installed.
  - Rebuilt and reinstalled the local `.deb`, then verified the installed desktop files and runtime bus name alignment on Ubuntu 24.04 / GNOME / Wayland.
  - Added a cross-project Linux desktop identity checklist to `~/.codex/AGENTS.md` so future Tauri packaging work checks this class of issue before handoff.
- Files created/modified:
  - `src-tauri/tauri.conf.json`
  - `src-tauri/bundle/linux/ant-build-center.desktop.hbs`
  - `src-tauri/bundle/linux/io.github.jiang0977.ant-build-center.desktop`
  - `progress.md`
  - `findings.md`
  - `task_plan.md`
