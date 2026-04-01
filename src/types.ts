export type BuildStatus = 'idle' | 'running' | 'success' | 'failure'

export interface RuntimeSettings {
  javaHome: string
  antHome: string
}

export interface ProjectRecord {
  id: string
  path: string
  name: string
  defaultTarget: string
  targets: string[]
  lastStatus: BuildStatus
  lastRunAt: string | null
}

export interface Workspace {
  version: number
  runtime: RuntimeSettings
  projects: ProjectRecord[]
}

export interface BuildLogEvent {
  projectId: string
  stream: 'stdout' | 'stderr' | 'system'
  line: string
}

export interface BuildFinishedEvent {
  projectId: string
  success: boolean
  cancelled: boolean
  durationMs: number
  message?: string
}
