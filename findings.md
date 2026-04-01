# Findings & Decisions

## Requirements
- Rewrite the app to Rust + Tauri.
- Only keep the control-center experience.
- Remove registry installation, right-click launch, Python installer, and batch build.
- Do not preserve compatibility with the old `workspace.json`.
- Fix the development documentation now and record implementation progress in files.
- Use TDD for ongoing implementation.

## Research Findings
- The legacy app was broader than the original README implied: it had a single-file launcher, a full control center, Windows registry integration, installer scripts, single-instance logic, desktop shortcut creation, and PyInstaller packaging.
- The control-center behavior worth carrying forward is narrower: track build files, inspect targets, run one build, stream logs, cancel a running build, and persist lightweight workspace state.
- Current Tauri v2 CLI supports `npx tauri init` for existing directories.
- Official Tauri v2 single-instance plugin documentation says the plugin should be registered first and can focus the existing window when another instance launches.
- The dialog plugin can be added through the Tauri CLI and grants `dialog:default` capability in `src-tauri/capabilities/default.json`.
- The new workspace schema is now enforced by tests: missing file -> default workspace, and saved workspace -> JSON roundtrip with parent directory creation.
- `crates/ant-build-core` now exposes a happy-path Ant `build.xml` parser that extracts project name, default target, and target names.
- The core crate now also exposes build command resolution that prefers `JAVA_HOME + ANT_HOME/lib/ant-launcher.jar` when both are available.
- The core crate now executes builds with streamed stdout/stderr events and cooperative cancellation.
- Command resolution now falls back to `ANT_HOME/bin/ant` when `ant-launcher.jar` is absent.
- Command resolution now also falls back to `ant` from `PATH` when `ANT_HOME` is empty, which matches the current Ubuntu dev machine.
- The default Vite demo UI has been replaced with a project-library / selected-project / runtime / terminal layout aligned to the planned Tauri command contracts.
- The Tauri shell now exposes workspace commands plus build execution / cancellation wiring through `build-log` and `build-finished` events.
- Ubuntu 24.04 can run the Tauri shell locally after installing the official Linux dependency set; the previous GTK/WebKit blocker is gone.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use Vite + React + TypeScript for the desktop UI | Fast iteration and a straightforward fit for Tauri |
| Use Tauri v2 with `single-instance` and `dialog` plugins | Matches the retained control-center behavior and avoids hand-written native glue |
| Store workspace in a new app-specific JSON file | Clean break from the legacy schema and simpler Rust modeling |
| Keep runtime configuration inline in the control center | Avoids a second settings page while still handling Java / Ant path overrides |
| Drive the first tests at the Rust service layer | Easier to keep TDD disciplined than starting with UI automation |
| Introduce `crates/ant-build-core` as a pure Rust domain crate | Decouples tested behavior from Tauri's platform-specific build requirements |
| Keep `src-tauri` as a thin adapter over `ant-build-core` | The shell should own window/event/state wiring, not domain logic |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Root `src/` conflicted with Vite's default frontend `src/` directory | Removed the legacy Python `src/` on the rewrite branch and replaced it with the frontend source tree |
| The repository had no persistent planning files | Added `task_plan.md`, `findings.md`, and `progress.md` in the project root |
| Full `cargo test` for the Tauri crate fails on this Linux host because GTK/WebKit pkg-config libraries are absent | Shift TDD to a pure Rust core crate so backend behavior can be tested without desktop system dependencies |
| `cargo new` created an unwanted nested Git repository inside the new core crate | Removed `crates/ant-build-core/.git` immediately |
| The branch still contained stale Python runtime files and docs after the initial scaffold | Removed them and rewrote README/docs to describe only the Tauri rewrite |
| Full Tauri compilation was initially blocked by missing system libraries | Installed the required Ubuntu packages; shell tests now run locally |

## Resources
- Official Tauri single-instance docs: https://v2.tauri.app/es/plugin/single-instance/
- Rewrite branch: `codex/tauri-control-center-rewrite`
- Draft design doc: `docs/designs/tauri-control-center-rewrite.md`
- New Tauri config: `src-tauri/tauri.conf.json`

## Visual/Browser Findings
- The Tauri single-instance docs confirm the plugin callback receives `(app, args, cwd)` and show focusing the `"main"` window from the running instance.
- The docs note the single-instance plugin should be the first plugin registered.
