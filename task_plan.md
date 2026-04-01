# Task Plan: Rust + Tauri Control Center Rewrite

## Goal
Replace the legacy Python/Tk desktop app with a Rust + Tauri control-center-only app that manages Ant build files, runs a single build with live logs, and uses a fresh workspace format.

## Current Feature Focus
Design and implement a grouped file-management experience for the left file rail: persisted groups, group rename, multi-select drag and drop, guarded group deletion, and group-aware file adding.

## Current Phase
Phase 8

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

### Phase 8: Grouped File Management Design
- [x] Inspect the current React/Tauri workspace model and the prior Python grouped-tree behavior
- [x] Decide whether grouping becomes first-class persisted workspace state in v2
- [x] Choose the interaction model for multi-select drag/drop, grouped add flow, and delete-group safeguards
- [x] Update the design docs / implementation plan before code changes
- **Status:** complete

### Phase 9: Grouped File Management Implementation
- [x] TDD slice 1: grouped workspace defaults and flat-v2 upgrade path
- [x] TDD slice 2: group create / rename / delete behavior
- [x] TDD slice 3: grouped add-project and move-project behavior
- [x] TDD slice 4: grouped left-rail UI with rename and guarded deletion
- [ ] Run verification and manual smoke coverage
- **Status:** in_progress

## Key Questions
1. What is the smallest control-center feature set worth shipping in v0.1?
2. Which runtime settings must stay user-configurable in the first Tauri release?
3. How should live build output and cancellation be modeled so the UI stays simple and testable?
4. Should groups be first-class persisted workspace entities or only a UI projection over a flat file list?
5. What should happen to files when a non-empty group is deleted?
6. How should the add-file flow assign a target group without slowing the common path?
7. Which thin TDD slice should land first so grouped file management can grow without destabilizing build execution?

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
| Treat grouped file management as a workspace-model change, not a UI-only patch | The current Tauri rewrite stores a flat `projects[]`; drag/drop between groups and add-into-group semantics require persisted grouping state |
| Handle the grouping request as an internal-project feature decision, not product-opportunity discovery | The user explicitly said this is an existing-project evolution and wants a design that can be implemented correctly and shipped quickly |
| Revise the existing rewrite design doc instead of creating a separate addendum | The user chose to keep one authoritative design baseline and update scope in place |
| Persist groups as first-class workspace state, keep files as the buildable unit, require guarded non-empty group deletion, and support group-aware add-file flows | The user agreed to the premise set that locks the feature boundary before implementation |
| Use Approach A: flat `projects[]` plus first-class `groups[]`, with each project carrying `groupId` and per-group `order` | This preserves the current `projectId`-driven build path while still delivering persisted grouping and drag/drop organization |
| Support user-created group renaming in the first grouped release | The user explicitly approved rename support before implementation started |

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
- The current design baseline still lists grouping and drag/drop sorting as out of scope, so this feature needs an explicit design update before implementation.
- Manual desktop smoke coverage for the new grouped rail has not been run yet in this session; automated verification is green.
