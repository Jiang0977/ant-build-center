# Task Plan: Rust + Tauri Control Center Rewrite

## Goal
Replace the legacy Python/Tk desktop app with a Rust + Tauri control-center-only app that manages Ant build files, runs a single build with live logs, and uses a fresh workspace format.

## Current Phase
Phase 7

## Phases

### Phase 1: Requirements & Discovery
- [x] Confirm rewrite scope and removals with the user
- [x] Inspect the current Python app and packaging flow
- [x] Capture findings in `findings.md`
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Create persistent planning files
- [x] Draft the rewrite design doc
- [x] Lock the first TDD vertical slice
- **Status:** complete

### Phase 3: Tauri Skeleton
- [x] Create the React/Vite frontend scaffold
- [x] Initialize Tauri v2 and required plugins
- [x] Replace generated demo code with app-specific structure
- **Status:** complete

### Phase 4: TDD Slice 1 - Workspace Persistence
- [x] Write a failing Rust test for empty workspace bootstrap
- [x] Implement minimal workspace storage and loading
- [x] Refactor only after GREEN
- **Status:** complete

### Phase 5: TDD Slice 2 - Project Parsing
- [x] Write a failing Rust test for parsing `build.xml` targets
- [x] Implement minimal parsing logic and project metadata refresh
- [x] Refactor only after GREEN
- **Status:** complete

### Phase 6: TDD Slice 3 - Build Execution
- [x] Write a failing Rust test for Ant command resolution / execution flow
- [x] Implement single-build execution with live log events and cancel support
- [x] Refactor only after GREEN
- **Status:** complete

### Phase 7: Frontend Integration & Verification
- [x] Wire the React UI to Rust commands and events
- [x] Run lint/build/tests
- [x] Remove obsolete Python runtime files and update docs
- **Status:** in_progress

## Key Questions
1. What is the smallest control-center feature set worth shipping in v0.1?
2. Which runtime settings must stay user-configurable in the first Tauri release?
3. How should live build output and cancellation be modeled so the UI stays simple and testable?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Only keep the control center | User explicitly dropped right-click entry, installer, registry integration, and batch build |
| Do not preserve `workspace.json` compatibility | User explicitly allowed a fresh storage format |
| Use a new branch `codex/tauri-control-center-rewrite` | Keeps `master` as the backup of the Python implementation |
| Put domain logic in Rust, not frontend | Keeps parsing, execution, persistence, and process state testable and independent from the UI |
| Use `doc-coauthoring` + `planning-with-files` + `tdd` together | User explicitly requested this process for the rewrite |
| Create a pure Rust core crate outside the Tauri shell | Allows backend TDD to proceed even when desktop system libraries are unavailable on the current Linux host |
| Use a single-build mutex plus cancellation token in the Tauri shell | Keeps concurrent state explicit and matches the simplified product scope |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `cargo tauri` missing | 1 | Installed `@tauri-apps/cli` and used `npx tauri` |
| Tauri crate tests initially required missing GTK/WebKit system libraries on this Linux host | 1 | Installed the Ubuntu Tauri dependencies (`libwebkit2gtk-4.1-dev`, GTK/AppIndicator stack, etc.); `src-tauri` tests now run |

## Notes
- `master` is the backup branch for the legacy Python implementation.
- Old Python runtime files are being removed on this rewrite branch and should not be reintroduced.
- The first TDD slice will target backend behavior before UI polish.
- The repository cleanup on this branch is intentional: README/docs now describe only the Rust + Tauri rewrite.
