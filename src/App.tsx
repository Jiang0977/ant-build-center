import {
  startTransition,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from 'react'

import './App.css'
import {
  addProjects,
  cancelBuild,
  getWorkspace,
  isTauriEnvironment,
  listenToBuildEvents,
  removeProject,
  runBuild,
  saveRuntime,
} from './lib/tauri'
import type {
  BuildFinishedEvent,
  BuildLogEvent,
  ProjectRecord,
  RuntimeSettings,
  Workspace,
} from './types'

const emptyWorkspace: Workspace = {
  version: 2,
  runtime: {
    javaHome: '',
    antHome: '',
  },
  projects: [],
}

function App() {
  const [workspace, setWorkspace] = useState<Workspace>(emptyWorkspace)
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [selectedTarget, setSelectedTarget] = useState('')
  const [runtimeDraft, setRuntimeDraft] = useState<RuntimeSettings>(emptyWorkspace.runtime)
  const [consoleLines, setConsoleLines] = useState<string[]>([
    isTauriEnvironment()
      ? 'Ant Build Center ready. Load a build.xml file to begin.'
      : 'Browser preview mode. Tauri commands are disabled outside the desktop shell.',
  ])
  const [, setStatusLine] = useState(
    isTauriEnvironment()
      ? 'Workspace loading…'
      : 'Browser preview mode: use the desktop shell for live commands.',
  )
  const [, setIsHydrating] = useState(true)
  const [isRunning, setIsRunning] = useState(false)
  const [isSavingRuntime, setIsSavingRuntime] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const consoleScreenRef = useRef<HTMLPreElement | null>(null)

  const selectedProject =
    workspace.projects.find((project) => project.id === selectedProjectId) ?? null

  function appendConsoleLine(line: string) {
    setConsoleLines((current) => {
      const next = [...current, line]
      return next.slice(-500)
    })
  }

  function applyWorkspace(nextWorkspace: Workspace) {
    startTransition(() => {
      setWorkspace(nextWorkspace)
      setRuntimeDraft(nextWorkspace.runtime)
      setSelectedProjectId((current) => {
        if (current && nextWorkspace.projects.some((project) => project.id === current)) {
          return current
        }
        return nextWorkspace.projects[0]?.id ?? null
      })
    })
  }

  const handleBuildLog = useEffectEvent((event: BuildLogEvent) => {
    const label =
      event.stream === 'stderr'
        ? '[stderr]'
        : event.stream === 'system'
          ? '[system]'
          : '[stdout]'
    appendConsoleLine(`${label} ${event.line}`)
  })

  const handleBuildFinished = useEffectEvent((event: BuildFinishedEvent) => {
    setIsRunning(false)
    setStatusLine(
      event.cancelled
        ? 'Build cancelled.'
        : event.success
          ? `Build finished in ${formatDuration(event.durationMs)}.`
          : 'Build failed.',
    )

    if (event.message) {
      appendConsoleLine(`[system] ${event.message}`)
    }

    void hydrateWorkspace()
  })

  const hydrateWorkspace = useEffectEvent(async () => {
    if (!isTauriEnvironment()) {
      setIsHydrating(false)
      return
    }

    try {
      const nextWorkspace = await getWorkspace()
      applyWorkspace(nextWorkspace)
      setStatusLine(
        nextWorkspace.projects.length > 0
          ? `${nextWorkspace.projects.length} projects loaded.`
          : 'No tracked build files yet.',
      )
    } catch (error) {
      setStatusLine('Failed to load workspace.')
      appendConsoleLine(`[system] ${(error as Error).message}`)
    } finally {
      setIsHydrating(false)
    }
  })

  useEffect(() => {
    void hydrateWorkspace()
  }, [])

  useEffect(() => {
    if (!selectedProject) {
      setSelectedTarget('')
      return
    }

    setSelectedTarget(selectedProject.defaultTarget || selectedProject.targets[0] || '')
  }, [selectedProject])

  useEffect(() => {
    if (!isTauriEnvironment()) {
      return
    }

    let cleanup = () => {}

    void listenToBuildEvents(handleBuildLog, handleBuildFinished).then((unsubscribe) => {
      cleanup = unsubscribe
    })

    return () => cleanup()
  }, [])

  useEffect(() => {
    if (!isRunning) {
      return
    }

    const screen = consoleScreenRef.current
    if (!screen) {
      return
    }

    screen.scrollTop = screen.scrollHeight
  }, [consoleLines, isRunning])

  useEffect(() => {
    if (!isSettingsOpen) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setRuntimeDraft(workspace.runtime)
        setIsSettingsOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isSettingsOpen, workspace.runtime])

  function openSettingsPanel() {
    setRuntimeDraft(workspace.runtime)
    setIsSettingsOpen(true)
  }

  function closeSettingsPanel() {
    setRuntimeDraft(workspace.runtime)
    setIsSettingsOpen(false)
  }

  async function handleAddProjects() {
    try {
      const nextWorkspace = await addProjects()
      applyWorkspace(nextWorkspace)
      setStatusLine(`${nextWorkspace.projects.length} tracked projects.`)
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to add projects.')
    }
  }

  async function handleRemoveProject(project: ProjectRecord) {
    try {
      const nextWorkspace = await removeProject(project.id)
      applyWorkspace(nextWorkspace)
      appendConsoleLine(`[system] Removed ${getProjectDisplayName(project)}.`)
      setStatusLine(`${nextWorkspace.projects.length} tracked projects.`)
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to remove project.')
    }
  }

  async function handleSaveRuntime() {
    setIsSavingRuntime(true)
    try {
      const nextWorkspace = await saveRuntime(runtimeDraft)
      applyWorkspace(nextWorkspace)
      appendConsoleLine('[system] Runtime settings saved.')
      setStatusLine('Runtime settings saved.')
      setIsSettingsOpen(false)
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to save runtime settings.')
    } finally {
      setIsSavingRuntime(false)
    }
  }

  async function handleRunBuild() {
    if (!selectedProject) {
      return
    }

    setConsoleLines([
      `[system] Starting ${getProjectDisplayName(selectedProject)} (${selectedTarget || 'default target'})`,
    ])
    setIsRunning(true)
    setStatusLine(`Running ${getProjectDisplayName(selectedProject)}…`)

    try {
      await runBuild(selectedProject.id, selectedTarget)
    } catch (error) {
      setIsRunning(false)
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to start build.')
    }
  }

  async function handleCancelBuild() {
    try {
      await cancelBuild()
      appendConsoleLine('[system] Cancel requested.')
      setStatusLine('Cancelling build…')
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to cancel build.')
    }
  }

  return (
    <div className="app-shell">
      <main className="control-grid">
        <aside className="project-rail">
          <div className="rail-head">
            <div className="rail-actions">
              <button
                className="action-button ghost"
                onClick={openSettingsPanel}
                type="button"
              >
                Settings
              </button>
              <button
                className="action-button primary"
                disabled={!isTauriEnvironment()}
                onClick={handleAddProjects}
                type="button"
              >
                Add files
              </button>
            </div>
          </div>

          <div className="project-list-frame">
            <div className="project-list">
              {workspace.projects.length === 0 ? (
                <div className="empty-card">
                  <p>No projects yet.</p>
                  <span>Use “Add files” to register one or more Ant build files.</span>
                </div>
              ) : null}

              {workspace.projects.map((project) => {
                const isActive = project.id === selectedProjectId
                return (
                  <button
                    key={project.id}
                    className={`project-card${isActive ? ' active' : ''}`}
                    onClick={() => setSelectedProjectId(project.id)}
                    title={project.path}
                    type="button"
                  >
                    <span className={`status-dot status-${project.lastStatus}`} />
                    <div className="project-card-copy">
                      <strong>{getProjectDisplayName(project)}</strong>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </aside>

        <section className="main-panel">
          <div className="panel-card focus-card">
            <div className="focus-head">
              <div>
                <p className="section-label">Selected File</p>
                <h2>
                  {selectedProject ? getProjectDisplayName(selectedProject) : 'Choose a build file'}
                </h2>
              </div>
              <div className="focus-actions">
                {selectedProject ? (
                  <span className={`status-pill status-${selectedProject.lastStatus}`}>
                    {formatBuildStatus(selectedProject.lastStatus)}
                  </span>
                ) : null}
                {selectedProject ? (
                  <button
                    className="action-button ghost"
                    disabled={!isTauriEnvironment() || isRunning}
                    onClick={() => void handleRemoveProject(selectedProject)}
                    type="button"
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            </div>

            {selectedProject ? (
              <div className="focus-grid">
                <dl className="meta-grid">
                  <div>
                    <dt>Path</dt>
                    <dd>{selectedProject.path}</dd>
                  </div>
                  <div>
                    <dt>Default target</dt>
                    <dd>{selectedProject.defaultTarget || 'Not defined'}</dd>
                  </div>
                  <div>
                    <dt>Last status</dt>
                    <dd>{selectedProject.lastStatus || 'idle'}</dd>
                  </div>
                  <div>
                    <dt>Last run</dt>
                    <dd>{selectedProject.lastRunAt || 'Never'}</dd>
                  </div>
                </dl>

                <div className="launch-strip">
                  <label className="field">
                    <span>Target</span>
                    <select
                      disabled={isRunning || selectedProject.targets.length === 0}
                      onChange={(event) => setSelectedTarget(event.target.value)}
                      value={selectedTarget}
                    >
                      <option value="">Use default target</option>
                      {selectedProject.targets.map((target) => (
                        <option key={target} value={target}>
                          {target}
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="launch-actions">
                    <button
                      className="action-button primary"
                      disabled={!isTauriEnvironment() || isRunning}
                      onClick={() => void handleRunBuild()}
                      type="button"
                    >
                      Run build
                    </button>
                    <button
                      className="action-button danger"
                      disabled={!isTauriEnvironment() || !isRunning}
                      onClick={() => void handleCancelBuild()}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-detail">
                Select a tracked project to inspect its path, targets, and build controls.
              </div>
            )}
          </div>

          <div className="panel-card terminal-card">
            <div className="terminal-head">
              <div>
                <p className="section-label">Live Output</p>
                <h2>Build console</h2>
              </div>
              <span className={`run-indicator${isRunning ? ' hot' : ''}`}>
                {isRunning ? 'RUNNING' : 'IDLE'}
              </span>
            </div>

            <pre className="terminal-screen" ref={consoleScreenRef}>
              {consoleLines.map((line, index) => (
                <code key={`${line}-${index}`}>{line}</code>
              ))}
            </pre>
          </div>
        </section>
      </main>

      {isSettingsOpen ? (
        <div
          className="modal-backdrop"
          onClick={closeSettingsPanel}
          role="presentation"
        >
          <div
            aria-labelledby="runtime-overrides-title"
            aria-modal="true"
            className="modal-card"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="modal-head">
              <div className="runtime-copy">
                <p className="section-label">Settings</p>
                <h2 id="runtime-overrides-title">Runtime Overrides</h2>
                <span>
                  These values override environment discovery. Leave them blank to
                  use `JAVA_HOME`, `ANT_HOME`, and `PATH`.
                </span>
              </div>
              <button
                aria-label="Close settings"
                className="action-button ghost icon-button"
                onClick={closeSettingsPanel}
                type="button"
              >
                Close
              </button>
            </div>

            <div className="runtime-form">
              <label className="field">
                <span>JAVA_HOME</span>
                <input
                  onChange={(event) =>
                    setRuntimeDraft((current) => ({
                      ...current,
                      javaHome: event.target.value,
                    }))
                  }
                  placeholder="C:/Program Files/Java/jdk-21"
                  value={runtimeDraft.javaHome}
                />
              </label>
              <label className="field">
                <span>ANT_HOME</span>
                <input
                  onChange={(event) =>
                    setRuntimeDraft((current) => ({
                      ...current,
                      antHome: event.target.value,
                    }))
                  }
                  placeholder="D:/Tools/apache-ant"
                  value={runtimeDraft.antHome}
                />
              </label>
            </div>

            <div className="runtime-actions">
              <button
                className="action-button ghost"
                onClick={closeSettingsPanel}
                type="button"
              >
                Cancel
              </button>
              <button
                className="action-button secondary"
                disabled={!isTauriEnvironment() || isSavingRuntime || isRunning}
                onClick={() => void handleSaveRuntime()}
                type="button"
              >
                {isSavingRuntime ? 'Saving…' : 'Save runtime'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function formatBuildStatus(status: ProjectRecord['lastStatus']) {
  switch (status) {
    case 'success':
      return 'Success'
    case 'failure':
      return 'Failure'
    case 'running':
      return 'Running'
    default:
      return 'Idle'
  }
}

function getProjectDisplayName(project: ProjectRecord) {
  const normalizedPath = project.path.replace(/\\/g, '/')
  const segments = normalizedPath.split('/')
  return segments[segments.length - 1] || project.name
}

function formatDuration(durationMs: number) {
  if (durationMs < 1000) {
    return `${durationMs}ms`
  }

  return `${(durationMs / 1000).toFixed(2)}s`
}

export default App
