export interface Pipeline {
  id: string
  name: string
  description?: string
  components: PipelineComponent[]
  created_at: string
  updated_at: string
}

export interface PipelineComponent {
  id: string
  name: string
  component_type: ComponentType
  parameters: Record<string, any>
  dependencies: string[]
}

export type ComponentType = 'resize' | 'ai_detection' | 'filter' | 'enhancement'

export interface ComponentDefinition {
  id: string
  name: string
  description: string
  parameters: Record<string, ParameterDefinition>
  input_types: string[]
  output_types: string[]
}

export interface ParameterDefinition {
  type: 'string' | 'integer' | 'float' | 'boolean'
  default?: any
  min?: number
  max?: number
  options?: string[]
  description: string
}

export interface Execution {
  execution_id: string
  pipeline_id: string
  status: ExecutionStatus
  progress: ExecutionProgress
  steps: ExecutionStep[]
  output_files: OutputFile[]
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
}

export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ExecutionProgress {
  current_step: string
  total_steps: number
  completed_steps: number
  percentage: number
}

export interface ExecutionStep {
  component_name: string
  status: StepStatus
  started_at?: string
  completed_at?: string
  error_message?: string
  resource_usage?: Record<string, any>
}

export type StepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'

export interface OutputFile {
  file_id: string
  filename: string
  download_url: string
  file_size: number
}

export interface User {
  username: string
  role: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}