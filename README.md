# Ant Build Center

Rust + Tauri rewrite of the old `ant-build-menu` project.

This branch intentionally narrows the product:

- Keep only the control-center experience.
- Drop registry integration, Explorer right-click launch, installer/uninstaller, and batch build.
- Start with a fresh workspace format instead of migrating the old Python `workspace.json`.

`master` remains the backup of the legacy Python/Tk implementation. Active rewrite work happens on `codex/tauri-control-center-rewrite`.

## Current Status

The rewrite is in progress. The repository now contains:

- A Vite + React + TypeScript desktop UI scaffold
- A Tauri v2 shell scaffold
- A pure Rust core crate developed with TDD
- Persistent planning and progress files in the project root
- A formal design doc in `docs/designs/`

## Architecture

```text
React UI
  -> invoke Tauri commands
  -> listen for build-log / build-finished events

Tauri shell
  -> adapts frontend commands to the core crate
  -> owns native integrations (window, dialog, single-instance)

ant-build-core
  -> workspace persistence
  -> build.xml parsing
  -> build command resolution
```

## Repository Guide

- `docs/designs/tauri-control-center-rewrite.md`
  Current technical design baseline
- `docs/development.md`
  Development workflow, TDD slices, and validation commands
- `task_plan.md`
  Phase tracking
- `findings.md`
  Research and technical decisions
- `progress.md`
  Chronological implementation log
- `crates/ant-build-core`
  Pure Rust domain crate under active TDD
- `src`
  React UI for the new control center
- `src-tauri`
  Tauri v2 shell
- `examples`
  Sample Ant files useful for parsing and smoke tests

## Development

Install frontend dependencies:

```bash
npm install
```

Run frontend build verification:

```bash
npm run build
```

Run core crate tests:

```bash
cd crates/ant-build-core
cargo test
```

## Linux Host Note

On the current Linux host, full `cargo test` inside `src-tauri` is blocked by missing GTK/WebKit pkg-config libraries required by Tauri. Core behavior is therefore being developed test-first in `crates/ant-build-core`, then adapted into the Tauri shell.

## Scope Rules For This Rewrite

- No Python runtime path is kept as an active codepath on this branch.
- No attempt is made to preserve the old installer/registry model.
- No compatibility guarantee is made for the old workspace storage.
- UI and backend behavior should be added in thin TDD slices.
