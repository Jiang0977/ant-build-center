import {
  startTransition,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from 'react'
import type { DragEvent, MouseEvent } from 'react'

import './App.css'
import {
  addProjects,
  cancelBuild,
  createGroup,
  deleteGroup,
  getWorkspace,
  isTauriEnvironment,
  listenToBuildEvents,
  moveProjects,
  removeProject,
  removeProjects,
  renameGroup,
  runBuild,
  saveRuntime,
  setGroupExpanded,
} from './lib/tauri'
import type {
  BuildFinishedEvent,
  BuildLogEvent,
  GroupRecord,
  ProjectRecord,
  RuntimeSettings,
  Workspace,
} from './types'

type DropTarget = {
  groupId: string
  index: number
  kind: 'group' | 'before' | 'after'
  projectId?: string
}

type GroupDialogState =
  | {
      mode: 'create'
      name: string
    }
  | {
      mode: 'rename'
      groupId: string
      name: string
    }
  | {
      mode: 'delete'
      group: GroupRecord
      fileCount: number
    }

type ProjectContextMenuState = {
  x: number
  y: number
  projectIds: string[]
}

type GroupContextMenuState = {
  x: number
  y: number
  groupId: string
}

type ProjectDeleteDialogState = {
  projectIds: string[]
}

const emptyWorkspace: Workspace = {
  version: 3,
  runtime: {
    javaHome: '',
    antHome: '',
  },
  groups: [
    {
      id: 'default',
      name: 'Ungrouped',
      expanded: true,
      system: true,
    },
  ],
  projects: [],
}

function App() {
  const [workspace, setWorkspace] = useState<Workspace>(emptyWorkspace)
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([])
  const [selectionAnchorProjectId, setSelectionAnchorProjectId] = useState<string | null>(null)
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(
    emptyWorkspace.groups[0]?.id ?? null,
  )
  const [addTargetGroupId, setAddTargetGroupId] = useState(
    emptyWorkspace.groups[0]?.id ?? 'default',
  )
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
  const [groupDialog, setGroupDialog] = useState<GroupDialogState | null>(null)
  const [groupContextMenu, setGroupContextMenu] = useState<GroupContextMenuState | null>(null)
  const [projectContextMenu, setProjectContextMenu] = useState<ProjectContextMenuState | null>(null)
  const [projectDeleteDialog, setProjectDeleteDialog] = useState<ProjectDeleteDialogState | null>(
    null,
  )
  const [dragProjectIds, setDragProjectIds] = useState<string[]>([])
  const [dropTarget, setDropTarget] = useState<DropTarget | null>(null)
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
    const nextProjectIds = new Set(nextWorkspace.projects.map((project) => project.id))
    const nextGroupIds = new Set(nextWorkspace.groups.map((group) => group.id))
    const fallbackProjectId = nextWorkspace.projects[0]?.id ?? null
    const fallbackGroupId = nextWorkspace.groups[0]?.id ?? null

    startTransition(() => {
      setWorkspace(nextWorkspace)
      setRuntimeDraft(nextWorkspace.runtime)
      setSelectedProjectId((current) =>
        current && nextProjectIds.has(current) ? current : fallbackProjectId,
      )
      setSelectedProjectIds((current) => {
        const remaining = current.filter((projectId) => nextProjectIds.has(projectId))
        if (remaining.length > 0) {
          return remaining
        }
        return fallbackProjectId ? [fallbackProjectId] : []
      })
      setSelectionAnchorProjectId((current) =>
        current && nextProjectIds.has(current) ? current : fallbackProjectId,
      )
      setSelectedGroupId((current) =>
        current && nextGroupIds.has(current) ? current : fallbackGroupId,
      )
      setAddTargetGroupId((current) =>
        current && nextGroupIds.has(current) ? current : fallbackGroupId ?? 'default',
      )
    })
  }

  function selectOnlyProject(project: ProjectRecord) {
    setSelectedProjectId(project.id)
    setSelectedProjectIds([project.id])
    setSelectionAnchorProjectId(project.id)
    setSelectedGroupId(project.groupId)
    setAddTargetGroupId(project.groupId)
  }

  function selectGroup(group: GroupRecord) {
    setSelectedGroupId(group.id)
    setAddTargetGroupId(group.id)
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
      applyWorkspace(emptyWorkspace)
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
    if (
      !isSettingsOpen &&
      !groupDialog &&
      !groupContextMenu &&
      !projectDeleteDialog &&
      !projectContextMenu
    ) {
      return
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsSettingsOpen(false)
        setGroupDialog(null)
        setGroupContextMenu(null)
        setProjectDeleteDialog(null)
        setProjectContextMenu(null)
        setRuntimeDraft(workspace.runtime)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [
    groupContextMenu,
    groupDialog,
    isSettingsOpen,
    projectContextMenu,
    projectDeleteDialog,
    workspace.runtime,
  ])

  function openSettingsPanel() {
    setRuntimeDraft(workspace.runtime)
    setIsSettingsOpen(true)
  }

  function closeSettingsPanel() {
    setRuntimeDraft(workspace.runtime)
    setIsSettingsOpen(false)
  }

  function closeGroupDialog() {
    setGroupDialog(null)
  }

  function closeGroupContextMenu() {
    setGroupContextMenu(null)
  }

  function closeProjectContextMenu() {
    setProjectContextMenu(null)
  }

  function closeProjectDeleteDialog() {
    setProjectDeleteDialog(null)
  }

  function openCreateGroupDialog() {
    setGroupDialog({
      mode: 'create',
      name: '',
    })
  }

  function openRenameGroupDialog(groupId = selectedGroupId) {
    const group =
      workspace.groups.find((item) => item.id === groupId) ?? null

    if (!group || group.system) {
      return
    }

    closeGroupContextMenu()
    setGroupDialog({
      mode: 'rename',
      groupId: group.id,
      name: group.name,
    })
  }

  function openDeleteGroupDialog(groupId = selectedGroupId) {
    const group =
      workspace.groups.find((item) => item.id === groupId) ?? null

    if (!group || group.system) {
      return
    }

    closeGroupContextMenu()
    setGroupDialog({
      mode: 'delete',
      group,
      fileCount: getProjectsForGroup(workspace, group.id).length,
    })
  }

  function updateGroupDialogName(name: string) {
    setGroupDialog((current) => {
      if (!current || current.mode === 'delete') {
        return current
      }

      return {
        ...current,
        name,
      }
    })
  }

  async function handleConfirmGroupDialog() {
    if (!groupDialog) {
      return
    }

    if (groupDialog.mode === 'create') {
      const name = groupDialog.name

      try {
        const currentGroupIds = new Set(workspace.groups.map((group) => group.id))
        const nextWorkspace = await createGroup(name)
        const nextGroup =
          nextWorkspace.groups.find((group) => !currentGroupIds.has(group.id)) ?? null
        applyWorkspace(nextWorkspace)
        if (nextGroup) {
          setSelectedGroupId(nextGroup.id)
          setAddTargetGroupId(nextGroup.id)
        }
        setStatusLine(`Created group "${name.trim()}".`)
        closeGroupDialog()
      } catch (error) {
        appendConsoleLine(`[system] ${(error as Error).message}`)
        setStatusLine('Failed to create group.')
      }

      return
    }

    if (groupDialog.mode === 'rename') {
      const name = groupDialog.name

      try {
        const nextWorkspace = await renameGroup(groupDialog.groupId, name)
        applyWorkspace(nextWorkspace)
        setSelectedGroupId(groupDialog.groupId)
        setAddTargetGroupId(groupDialog.groupId)
        setStatusLine(`Renamed group to "${name.trim()}".`)
        closeGroupDialog()
      } catch (error) {
        appendConsoleLine(`[system] ${(error as Error).message}`)
        setStatusLine('Failed to rename group.')
      }

      return
    }

    try {
      const nextWorkspace = await deleteGroup(groupDialog.group.id)
      applyWorkspace(nextWorkspace)
      setStatusLine(`Deleted group "${groupDialog.group.name}".`)
      closeGroupDialog()
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to delete group.')
    }
  }

  function openProjectDeleteDialog(projectIds: string[]) {
    closeProjectContextMenu()
    setProjectDeleteDialog({
      projectIds,
    })
  }

  async function handleConfirmProjectDeleteDialog() {
    if (!projectDeleteDialog) {
      return
    }

    const projectIds = projectDeleteDialog.projectIds

    try {
      const nextWorkspace =
        projectIds.length === 1
          ? await removeProject(projectIds[0])
          : await removeProjects(projectIds)
      applyWorkspace(nextWorkspace)
      setStatusLine(
        `Removed ${projectIds.length} tracked file${projectIds.length === 1 ? '' : 's'}.`,
      )
      closeProjectDeleteDialog()
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to remove files.')
    }
  }

  async function handleAddProjects() {
    try {
      const nextWorkspace = await addProjects(addTargetGroupId)
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

  function handleProjectClick(project: ProjectRecord, event: MouseEvent<HTMLButtonElement>) {
    closeGroupContextMenu()
    closeProjectContextMenu()

    if (event.shiftKey && selectionAnchorProjectId) {
      const rangeSelection = getProjectRangeSelection(
        workspace,
        project.groupId,
        selectionAnchorProjectId,
        project.id,
      )
      if (rangeSelection.length > 0) {
        setSelectedProjectIds(rangeSelection)
      } else {
        setSelectedProjectIds([project.id])
      }
    } else if (event.metaKey || event.ctrlKey) {
      setSelectedProjectIds((current) => toggleProjectSelection(current, project.id))
    } else {
      setSelectedProjectIds([project.id])
    }

    setSelectedProjectId(project.id)
    setSelectionAnchorProjectId(project.id)
    setSelectedGroupId(project.groupId)
    setAddTargetGroupId(project.groupId)
  }

  function handleProjectDragStart(project: ProjectRecord, event: DragEvent<HTMLButtonElement>) {
    if (!isTauriEnvironment()) {
      return
    }

    closeGroupContextMenu()
    closeProjectContextMenu()

    const nextSelectedIds = selectedProjectIds.includes(project.id)
      ? selectedProjectIds
      : [project.id]
    const orderedIds = getProjectIdsInVisualOrder(workspace, nextSelectedIds)

    if (!selectedProjectIds.includes(project.id)) {
      selectOnlyProject(project)
    }

    setDragProjectIds(orderedIds)
    setDropTarget(null)
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', orderedIds.join(','))
  }

  function handleProjectDragEnd() {
    setDragProjectIds([])
    setDropTarget(null)
  }

  function handleProjectContextMenu(
    project: ProjectRecord,
    event: MouseEvent<HTMLButtonElement>,
  ) {
    event.preventDefault()
    event.stopPropagation()
    closeGroupContextMenu()

    const menuProjectIds = selectedProjectIds.includes(project.id)
      ? getProjectIdsInVisualOrder(workspace, selectedProjectIds)
      : [project.id]

    if (!selectedProjectIds.includes(project.id)) {
      selectOnlyProject(project)
    } else {
      setSelectedProjectId(project.id)
      setSelectionAnchorProjectId(project.id)
      setSelectedGroupId(project.groupId)
      setAddTargetGroupId(project.groupId)
    }

    setProjectContextMenu({
      x: event.clientX,
      y: event.clientY,
      projectIds: menuProjectIds,
    })
  }

  function handleGroupContextMenu(group: GroupRecord, event: MouseEvent<HTMLDivElement>) {
    event.preventDefault()
    event.stopPropagation()

    closeProjectContextMenu()
    selectGroup(group)

    if (group.system) {
      closeGroupContextMenu()
      return
    }

    setGroupContextMenu({
      x: event.clientX,
      y: event.clientY,
      groupId: group.id,
    })
  }

  async function handleToggleGroupExpanded(
    group: GroupRecord,
    event: MouseEvent<HTMLButtonElement>,
  ) {
    event.stopPropagation()

    if (!isTauriEnvironment()) {
      applyWorkspace({
        ...workspace,
        groups: workspace.groups.map((item) =>
          item.id === group.id ? { ...item, expanded: !item.expanded } : item,
        ),
      })
      return
    }

    try {
      const nextWorkspace = await setGroupExpanded(group.id, !group.expanded)
      applyWorkspace(nextWorkspace)
      setSelectedGroupId(group.id)
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to update group state.')
    }
  }

  function handleGroupDragOver(group: GroupRecord, event: DragEvent<HTMLDivElement>) {
    if (dragProjectIds.length === 0) {
      return
    }

    event.preventDefault()
    event.stopPropagation()
    setDropTarget({
      groupId: group.id,
      index: getAppendIndexForGroup(workspace, group.id, dragProjectIds),
      kind: 'group',
    })
  }

  function handleProjectDragOver(
    project: ProjectRecord,
    event: DragEvent<HTMLButtonElement>,
  ) {
    if (dragProjectIds.length === 0 || dragProjectIds.includes(project.id)) {
      return
    }

    event.preventDefault()
    event.stopPropagation()
    const rect = event.currentTarget.getBoundingClientRect()
    const insertAfter = event.clientY > rect.top + rect.height / 2
    const remainingProjects = getProjectsForGroup(workspace, project.groupId).filter(
      (item) => !dragProjectIds.includes(item.id),
    )
    const baseIndex = remainingProjects.findIndex((item) => item.id === project.id)

    if (baseIndex < 0) {
      return
    }

    setDropTarget({
      groupId: project.groupId,
      index: baseIndex + (insertAfter ? 1 : 0),
      kind: insertAfter ? 'after' : 'before',
      projectId: project.id,
    })
  }

  async function handleMoveDrop(target: DropTarget | null) {
    if (!target || dragProjectIds.length === 0 || !isTauriEnvironment()) {
      setDragProjectIds([])
      setDropTarget(null)
      return
    }

    const movingIds = [...dragProjectIds]

    try {
      const nextWorkspace = await moveProjects(
        movingIds,
        target.groupId,
        target.index,
      )
      applyWorkspace(nextWorkspace)
      setSelectedProjectIds(movingIds)
      setSelectedProjectId(movingIds[0] ?? null)
      setSelectionAnchorProjectId(movingIds[0] ?? null)
      setSelectedGroupId(target.groupId)
      setAddTargetGroupId(target.groupId)
      setStatusLine(`Moved ${movingIds.length} file${movingIds.length === 1 ? '' : 's'}.`)
    } catch (error) {
      appendConsoleLine(`[system] ${(error as Error).message}`)
      setStatusLine('Failed to move files.')
    } finally {
      setDragProjectIds([])
      setDropTarget(null)
    }
  }

  return (
    <div
      className="app-shell"
      onClick={() => {
        closeGroupContextMenu()
        closeProjectContextMenu()
      }}
    >
      <main className="control-grid">
        <aside className="project-rail">
          <div className="rail-head">
            <div className="rail-copy">
              <p className="section-label">Workspace</p>
              <h2 className="rail-title">File Groups</h2>
              <span className="rail-caption">
                {workspace.groups.length} groups · {workspace.projects.length} files
              </span>
            </div>

            <button
              className="action-button ghost"
              onClick={openSettingsPanel}
              type="button"
            >
              Settings
            </button>
          </div>

          <div className="rail-toolbar">
            <span className="rail-toolbar-hint">Right-click a group name for actions</span>
          </div>

          <div className="rail-toolbar rail-toolbar-add">
            <label className="field compact">
              <span>Add To</span>
              <select
                onChange={(event) => setAddTargetGroupId(event.target.value)}
                value={addTargetGroupId}
              >
                {workspace.groups.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </label>

            <button
              className="action-button secondary"
              disabled={!isTauriEnvironment()}
              onClick={openCreateGroupDialog}
              type="button"
            >
              New group
            </button>

            <button
              className="action-button primary"
              disabled={!isTauriEnvironment()}
              onClick={() => void handleAddProjects()}
              type="button"
            >
              Add files
            </button>
          </div>

          <div className="project-list-frame">
            <div className="project-groups">
              {workspace.projects.length === 0 ? (
                <div className="empty-card">
                  <p>No projects yet.</p>
                  <span>
                    Use “Add files” to register one or more Ant build files in a selected
                    group.
                  </span>
                </div>
              ) : null}

              {workspace.groups.map((group) => {
                const groupProjects = getProjectsForGroup(workspace, group.id)
                const isGroupActive = group.id === selectedGroupId
                const isGroupDropTarget =
                  dropTarget?.groupId === group.id && dropTarget.kind === 'group'

                return (
                  <section
                    key={group.id}
                    className={`group-section${isGroupActive ? ' active' : ''}${
                      isGroupDropTarget ? ' drop' : ''
                    }`}
                  >
                    <div
                      className="group-row"
                      onClick={() => selectGroup(group)}
                      onContextMenu={(event) => handleGroupContextMenu(group, event)}
                      onDragOver={(event) => handleGroupDragOver(group, event)}
                      onDrop={(event) => {
                        event.preventDefault()
                        void handleMoveDrop(dropTarget)
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="group-row-copy">
                        <button
                          aria-label={group.expanded ? 'Collapse group' : 'Expand group'}
                          className="group-toggle"
                          onClick={(event) => void handleToggleGroupExpanded(group, event)}
                          type="button"
                        >
                          <span className={`group-toggle-icon${group.expanded ? ' open' : ''}`}>
                            ^
                          </span>
                        </button>
                        <span className="group-badge">
                          {group.system ? 'System' : 'Group'}
                        </span>
                        <strong>{group.name}</strong>
                      </div>
                      <span className="group-count">{groupProjects.length}</span>
                    </div>

                    {group.expanded ? (
                      <div
                        className="group-projects"
                        onDragOver={(event) => handleGroupDragOver(group, event)}
                        onDrop={(event) => {
                          event.preventDefault()
                          event.stopPropagation()
                          void handleMoveDrop(dropTarget)
                        }}
                      >
                        {groupProjects.length === 0 ? (
                          <div className="empty-group">
                            <div className="empty-group-title">Drop files into this group</div>
                            <span>
                              Empty groups now accept direct drag-and-drop, or you can pick this
                              group before adding files.
                            </span>
                          </div>
                        ) : null}

                        {groupProjects.map((project) => {
                          const isFocused = project.id === selectedProjectId
                          const isSelected = selectedProjectIds.includes(project.id)
                          const isProjectDropTarget = dropTarget?.projectId === project.id

                        return (
                          <button
                            key={project.id}
                            className={`project-card${isFocused ? ' active' : ''}${
                              isSelected ? ' selected' : ''
                              }${
                                isProjectDropTarget
                                  ? dropTarget?.kind === 'before'
                                    ? ' drop-before'
                                    : ' drop-after'
                                  : ''
                              }`}
                              draggable={isTauriEnvironment()}
                            onClick={(event) => handleProjectClick(project, event)}
                            onContextMenu={(event) => handleProjectContextMenu(project, event)}
                            onDragEnd={handleProjectDragEnd}
                              onDragOver={(event) => handleProjectDragOver(project, event)}
                              onDragStart={(event) => handleProjectDragStart(project, event)}
                              onDrop={(event) => {
                                event.preventDefault()
                                event.stopPropagation()
                                void handleMoveDrop(dropTarget)
                              }}
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
                    ) : null}
                  </section>
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
                    <dt>Group</dt>
                    <dd>{workspace.groups.find((group) => group.id === selectedProject.groupId)?.name ?? 'Ungrouped'}</dd>
                  </div>
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
                  <div>
                    <dt>Multi-select</dt>
                    <dd>{selectedProjectIds.length} file(s) selected</dd>
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

      {groupDialog ? (
        <div
          className="modal-backdrop"
          onClick={closeGroupDialog}
          role="presentation"
        >
          <div
            aria-labelledby="group-dialog-title"
            aria-modal="true"
            className="modal-card modal-card-compact group-dialog-card"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="group-dialog-accent" />
            <div className="modal-head">
              <div className="runtime-copy">
                <p className="section-label">
                  {groupDialog.mode === 'delete' ? 'Delete Group' : 'Group Setup'}
                </p>
                <h2 id="group-dialog-title">
                  {groupDialog.mode === 'create'
                    ? 'Create a new group'
                    : groupDialog.mode === 'rename'
                      ? 'Rename selected group'
                      : 'Review delete impact'}
                </h2>
                <span>
                  {groupDialog.mode === 'create'
                    ? 'Give the rail a new bucket with a clean, durable label.'
                    : groupDialog.mode === 'rename'
                      ? 'Update the label without changing the tracked files inside it.'
                      : `Deleting "${groupDialog.group.name}" will keep every tracked file, but it will move them into Ungrouped.`}
                </span>
              </div>
              <button
                aria-label="Close group dialog"
                className="action-button ghost icon-button"
                onClick={closeGroupDialog}
                type="button"
              >
                Close
              </button>
            </div>

            {groupDialog.mode === 'delete' ? (
              <div className="dialog-warning-card">
                <div className="dialog-warning-count">{groupDialog.fileCount}</div>
                <div>
                  <strong>
                    {groupDialog.fileCount === 0
                      ? 'This group is empty.'
                      : `Tracked file${groupDialog.fileCount === 1 ? '' : 's'} will move to Ungrouped.`}
                  </strong>
                  <span>
                    {groupDialog.fileCount === 0
                      ? 'Only the group label will be removed.'
                      : 'No build.xml file is deleted from disk. Only the workspace grouping changes.'}
                  </span>
                </div>
              </div>
            ) : (
              <label className="field dialog-field">
                <span>Group Name</span>
                <input
                  autoFocus
                  onChange={(event) => updateGroupDialogName(event.target.value)}
                  placeholder="Release builds"
                  value={groupDialog.name}
                />
              </label>
            )}

            <div className="runtime-actions">
              <button
                className="action-button ghost"
                onClick={closeGroupDialog}
                type="button"
              >
                Cancel
              </button>
              <button
                className={`action-button ${
                  groupDialog.mode === 'delete' ? 'danger' : 'secondary'
                }`}
                disabled={
                  groupDialog.mode !== 'delete' && groupDialog.name.trim().length === 0
                }
                onClick={() => void handleConfirmGroupDialog()}
                type="button"
              >
                {groupDialog.mode === 'create'
                  ? 'Create group'
                  : groupDialog.mode === 'rename'
                    ? 'Save name'
                    : 'Delete group'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {projectDeleteDialog ? (
        <div
          className="modal-backdrop"
          onClick={closeProjectDeleteDialog}
          role="presentation"
        >
          <div
            aria-labelledby="project-delete-dialog-title"
            aria-modal="true"
            className="modal-card modal-card-compact group-dialog-card"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="group-dialog-accent group-dialog-accent-danger" />
            <div className="modal-head">
              <div className="runtime-copy">
                <p className="section-label">Remove Files</p>
                <h2 id="project-delete-dialog-title">Remove selected tracked files</h2>
                <span>
                  This only removes the files from the workspace. The actual `build.xml`
                  files stay on disk.
                </span>
              </div>
              <button
                aria-label="Close remove files dialog"
                className="action-button ghost icon-button"
                onClick={closeProjectDeleteDialog}
                type="button"
              >
                Close
              </button>
            </div>

            <div className="dialog-warning-card">
              <div className="dialog-warning-count">{projectDeleteDialog.projectIds.length}</div>
              <div>
                <strong>
                  Remove {projectDeleteDialog.projectIds.length} tracked file
                  {projectDeleteDialog.projectIds.length === 1 ? '' : 's'}?
                </strong>
                <span>
                  Group placement and build history in the workspace will be removed for the
                  selected entries. No file is deleted from the filesystem.
                </span>
              </div>
            </div>

            <div className="runtime-actions">
              <button
                className="action-button ghost"
                onClick={closeProjectDeleteDialog}
                type="button"
              >
                Cancel
              </button>
              <button
                className="action-button danger"
                onClick={() => void handleConfirmProjectDeleteDialog()}
                type="button"
              >
                Remove files
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {projectContextMenu ? (
        <div
          className="context-menu"
          onClick={(event) => event.stopPropagation()}
          role="menu"
          style={{
            left: projectContextMenu.x,
            top: projectContextMenu.y,
          }}
        >
          <button
            className="context-menu-item danger"
            onClick={() => {
              openProjectDeleteDialog(projectContextMenu.projectIds)
              closeProjectContextMenu()
            }}
            type="button"
          >
            Remove {projectContextMenu.projectIds.length > 1 ? 'selected files' : 'file'}
          </button>
        </div>
      ) : null}

      {groupContextMenu ? (
        <div
          className="context-menu"
          onClick={(event) => event.stopPropagation()}
          role="menu"
          style={{
            left: groupContextMenu.x,
            top: groupContextMenu.y,
          }}
        >
          <button
            className="context-menu-item"
            onClick={() => openRenameGroupDialog(groupContextMenu.groupId)}
            type="button"
          >
            Rename group
          </button>
          <button
            className="context-menu-item danger"
            onClick={() => openDeleteGroupDialog(groupContextMenu.groupId)}
            type="button"
          >
            Delete group
          </button>
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

function getProjectsForGroup(workspace: Workspace, groupId: string) {
  return workspace.projects
    .filter((project) => project.groupId === groupId)
    .sort((left, right) => left.order - right.order)
}

function getProjectRangeSelection(
  workspace: Workspace,
  groupId: string,
  anchorProjectId: string,
  targetProjectId: string,
) {
  const groupProjects = getProjectsForGroup(workspace, groupId)
  const anchorIndex = groupProjects.findIndex((project) => project.id === anchorProjectId)
  const targetIndex = groupProjects.findIndex((project) => project.id === targetProjectId)

  if (anchorIndex < 0 || targetIndex < 0) {
    return []
  }

  const start = Math.min(anchorIndex, targetIndex)
  const end = Math.max(anchorIndex, targetIndex)
  return groupProjects.slice(start, end + 1).map((project) => project.id)
}

function toggleProjectSelection(current: string[], projectId: string) {
  if (current.includes(projectId)) {
    if (current.length === 1) {
      return [projectId]
    }
    return current.filter((id) => id !== projectId)
  }

  return [...current, projectId]
}

function getProjectIdsInVisualOrder(workspace: Workspace, projectIds: string[]) {
  const groupOrder = new Map(workspace.groups.map((group, index) => [group.id, index]))
  const selectedIds = new Set(projectIds)

  return workspace.projects
    .filter((project) => selectedIds.has(project.id))
    .sort((left, right) => {
      const leftGroupIndex = groupOrder.get(left.groupId) ?? Number.MAX_SAFE_INTEGER
      const rightGroupIndex = groupOrder.get(right.groupId) ?? Number.MAX_SAFE_INTEGER

      if (leftGroupIndex !== rightGroupIndex) {
        return leftGroupIndex - rightGroupIndex
      }

      if (left.order !== right.order) {
        return left.order - right.order
      }

      return left.id.localeCompare(right.id)
    })
    .map((project) => project.id)
}

function getAppendIndexForGroup(
  workspace: Workspace,
  groupId: string,
  movingProjectIds: string[],
) {
  const movingIds = new Set(movingProjectIds)
  return getProjectsForGroup(workspace, groupId).filter(
    (project) => !movingIds.has(project.id),
  ).length
}

function formatDuration(durationMs: number) {
  if (durationMs < 1000) {
    return `${durationMs}ms`
  }

  return `${(durationMs / 1000).toFixed(2)}s`
}

export default App
