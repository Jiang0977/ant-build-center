# Development Workflow

This rewrite follows three explicit rules:

1. `doc-coauthoring`: keep design and development documentation current
2. `planning-with-files`: track work in `task_plan.md`, `findings.md`, and `progress.md`
3. `tdd`: implement one behavior slice at a time using `RED -> GREEN -> REFACTOR`

## Source Of Truth

- Design: `docs/designs/tauri-control-center-rewrite.md`
- Plan: `task_plan.md`
- Findings: `findings.md`
- Progress log: `progress.md`

If the chat context and these files diverge, update the files first.

## TDD Rules

- Prefer testing backend behavior in `crates/ant-build-core` before wiring Tauri or UI.
- Each slice should prove one public behavior.
- Do not batch future slices into the current test.
- Only refactor after the slice is green.

Current vertical slices:

1. Workspace bootstrap
2. Workspace save/load roundtrip
3. `build.xml` happy-path parsing
4. Build command resolution
5. Next: process execution + cancellation
6. Then: Tauri command adapter
7. Then: UI wiring

## Validation Commands

Frontend:

```bash
npm run build
```

Core crate:

```bash
cd crates/ant-build-core
cargo test
```

Tauri shell:

```bash
cd src-tauri
cargo test
```

Note: the current Linux host is missing Tauri GTK/WebKit system libraries, so the last command is expected to fail until that environment is available.

## Editing Policy

- Keep the Tauri shell thin.
- Keep domain logic in `crates/ant-build-core`.
- Keep UI state and visual layout in `src/`.
- Do not revive legacy Python entrypoints on this branch.

## Documentation Update Triggers

Update the design doc when any of these change:

- retained scope
- workspace schema
- Rust/Tauri module boundaries
- test strategy
- user-visible workflow

Update the planning files when any of these happen:

- a phase changes status
- a new discovery changes the approach
- a test goes red or green
- an environment or build blocker appears
