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
- Repository/app naming is already standardized in package metadata on `Ant Build Center`, but some docs, repository URLs, and example XML content had stale `ant-build-menu` / `Ant Build Menu` references that should be removed together.
- The GitHub repository can be renamed in place with `gh repo rename ant-build-center --yes`; after rename, the local `origin` remote automatically follows the new `git@github.com:Jiang0977/ant-build-center.git` path.

## Grouped File Management Discovery (2026-04-01)
- The current React/Tauri app still renders the left rail from a flat `workspace.projects` list in `src/App.tsx`.
- The Rust core workspace model in `crates/ant-build-core/src/workspace.rs` only stores `projects`; it has no group entity, no ordering metadata, and no parent-child relationship for files.
- The frontend `addProjects()` flow in `src/lib/tauri.ts` opens a native multi-select XML dialog and invokes `add_projects(paths)` with no group assignment.
- The current rewrite design doc `docs/designs/tauri-control-center-rewrite.md` explicitly lists grouping and drag-and-drop sorting as non-goals, so this request changes the rewrite baseline rather than extending an already-approved scope item.
- The legacy Python implementation at commit `ea80b9c` already supported group trees, Ctrl/Shift multi-select, drag feedback/highlighting, moving multiple files into groups or relative file positions, add-files-into-group, and stronger delete-group prompts.
- Conclusion: adding groups to the Tauri rewrite is not a cosmetic list enhancement. It is a data-model and interaction-model decision that should be designed first, then implemented.
- User confirmed the work mode is `Internal initiative`: this is an existing-project feature evolution and the optimization target is "do it right and land it quickly," not broad product exploration.
- User chose to revise `docs/designs/tauri-control-center-rewrite.md` directly rather than create a second design doc, so the rewrite baseline should be updated in place.
- User confirmed the premise set:
  - groups are persisted workspace entities
  - files remain the buildable unit
  - deleting a non-empty group must never silently delete files
  - add-file flow must support explicit target-group assignment plus a default-group path
- User selected `Approach A`: keep `projects[]` flat for build execution, add first-class `groups[]`, and model grouping with `project.groupId` plus per-group `order`.
- User approved user-created group renaming as part of the first grouped release.
- Old Python behavior confirms that deleting a non-empty group previously moved files into the default "Ungrouped" bucket rather than deleting them.
- Old Python config behavior also confirms that a default group invariant already existed and is a good fit for the Tauri rewrite.
- During TDD implementation, a real persistence bug appeared: same-group reorder operations were being lost after save/reload because workspace normalization rewrote order from raw vector position. A regression test now locks this down and normalization preserves stored order with original insertion order only as a tie-breaker.
- The first grouped rail shipped with browser-native `prompt` / `confirm`, which broke the visual language of the rest of the app. This round replaced them with project-styled modal dialogs and added a persisted expand/collapse command for groups.
- Duplicate tracked files were still possible because path uniqueness was only weakly enforced at add time. The workspace layer now treats project `path` as globally unique, skips duplicate adds, and deduplicates old duplicate paths while loading the workspace.
- Grouped rail multi-select now has a matching destructive action: users can right-click selected files and remove them as a batch. The backend now exposes a true bulk-remove path so per-group ordering stays compact after multi-delete.
- Group rename/delete entry points now live on the group itself instead of the top toolbar. Right-clicking a group row opens the action menu, which reduces rail chrome and keeps destructive actions attached to the object they affect.

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
| Put grouped workspace mutations into `ant-build-core::workspace::Workspace` methods | This let Tauri stay a thin command adapter and kept the TDD surface on public behavior rather than UI internals |
| Persist group expanded/collapsed state through the backend instead of keeping it as frontend-only UI state | The grouped workspace schema already carries `expanded`, and users expect the rail shape to survive reloads |

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
- The persisted desktop workspace on this machine stores `lastRunAt` as a Unix timestamp string like `"1775050174"`, not as an ISO datetime. Frontend display code needs to parse numeric strings as epoch seconds or milliseconds before formatting them.
- Manual smoke verification against the locally installed `.deb` confirms the `Selected File` panel now renders `LAST RUN` in the requested `yyyy-mm-dd hh-mm-ss` shape. On this host, the selected `build_x-web-new.xml` entry shows `2026-04-01 21-29-34`.
- The Linux dock icon issue matched an existing local-memory pattern exactly: on GNOME/Wayland, Tauri's default desktop file name derived from `productName` (`Ant Build Center.desktop`) did not align with the runtime GTK app id `io.github.jiang0977.ant-build-center`, so the running window could not be mapped back to the correct launcher/icon reliably.
- The fix on this project is to keep `app.enableGTKAppId = true`, hide Tauri's default generated desktop file with `NoDisplay=true`, and add a second visible desktop file named `io.github.jiang0977.ant-build-center.desktop` via `bundle.linux.deb.files`.
- After reinstalling the `.deb`, the system contains both `/usr/share/applications/Ant Build Center.desktop` (hidden) and `/usr/share/applications/io.github.jiang0977.ant-build-center.desktop` (visible). Launching with `gtk-launch io.github.jiang0977.ant-build-center` registers the expected bus name `io.github.jiang0977.ant-build-center`.

## Prior Design Docs
- `docs/designs/tauri-control-center-rewrite.md` (2026-04-01 17:05:26 +0800): current rewrite baseline; now partially outdated for left-rail scope because it treats grouping as out of scope.
