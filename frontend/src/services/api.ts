import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { Pipeline, Execution, ComponentDefinition, LoginRequest, LoginResponse, User } from '../types'

class ApiService {
  private api!: AxiosInstance

  constructor() {
    console.log('=== API Service Constructor Start ===')
    console.log('Constructor called at:', new Date().toISOString())
    
    this.initializeApi()
  }

  private initializeApi() {
    try {
      console.log('Initializing API Service with axios:', axios)
      console.log('Axios create method:', axios?.create)
      
      if (!axios) {
        throw new Error('Axios is not available')
      }
      
      if (!axios.create) {
        throw new Error('Axios.create is not available')
      }
      
      this.api = axios.create({
        baseURL: '/api',
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 10000,
      })
      
      console.log('Axios instance baseURL:', this.api.defaults.baseURL)
      console.log('Current origin:', window.location.origin)
      
      console.log('API instance created:', this.api)
      console.log('API instance type:', typeof this.api)
      console.log('API instance get method:', this.api?.get)
      
      if (!this.api) {
        throw new Error('Failed to create API instance')
      }
      
      if (!this.api.get) {
        throw new Error('API instance missing get method')
      }
      
      this.setupInterceptors()
      console.log('=== API Service Constructor Success ===')
    } catch (error) {
      console.error('=== API Service Constructor Error ===', error)
      throw error
    }
  }

  private setupInterceptors() {
    // Request interceptor to add auth token and debug URL
    this.api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      console.log('=== Request Interceptor ===')
      console.log('Request URL:', config.url)
      console.log('Request baseURL:', config.baseURL)
      console.log('Full URL will be:', `${config.baseURL}${config.url}`)
      
      const token = localStorage.getItem('access_token')
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // Response interceptor to handle auth errors
    this.api.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError) => {
        console.error('API Error:', error)
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token')
          // Avoid infinite redirect loop by checking current location
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      }
    )
  }

  // Ensure API is initialized before use
  private ensureApiInitialized() {
    if (!this.api || !this.api.get) {
      console.error('API instance not properly initialized, reinitializing...')
      this.initializeApi()
    }
    return this.api
  }

  // Auth APIs
  async login(loginData: LoginRequest): Promise<LoginResponse> {
    const api = this.ensureApiInitialized()
    const response = await api.post('/auth/login', loginData)
    return response.data
  }

  async logout(): Promise<void> {
    const api = this.ensureApiInitialized()
    await api.post('/auth/logout')
  }

  async getCurrentUser(): Promise<User> {
    const api = this.ensureApiInitialized()
    const response = await api.get('/auth/me')
    return response.data
  }

  // Pipeline APIs
  async getPipelines(): Promise<Pipeline[]> {
    try {
      const api = this.ensureApiInitialized()
      console.log('API Service - getPipelines using API instance:', !!api)
      
      const response = await api.get('/pipelines/')
      console.log('Pipelines response:', response.data)
      return response.data
    } catch (error) {
      console.error('Error in getPipelines:', error)
      throw error
    }
  }

  async getPipeline(id: string): Promise<Pipeline> {
    const api = this.ensureApiInitialized()
    const response = await api.get(`/pipelines/${id}`)
    return response.data
  }

  async createPipeline(pipeline: Omit<Pipeline, 'id' | 'created_at' | 'updated_at'>): Promise<Pipeline> {
    const api = this.ensureApiInitialized()
    const response = await api.post('/pipelines/', pipeline)
    return response.data
  }

  async updatePipeline(id: string, pipeline: Partial<Pipeline>): Promise<Pipeline> {
    const api = this.ensureApiInitialized()
    const response = await api.put(`/pipelines/${id}`, pipeline)
    return response.data
  }

  async deletePipeline(id: string): Promise<void> {
    const api = this.ensureApiInitialized()
    await api.delete(`/pipelines/${id}`)
  }

  // Execution APIs
  async executePipeline(pipelineId: string, files: File[], parameters: Record<string, any> = {}, priority: string = 'normal'): Promise<{ execution_id: string; status: string }> {
    const api = this.ensureApiInitialized()
    const formData = new FormData()
    formData.append('pipeline_id', pipelineId)
    formData.append('priority', priority)
    formData.append('parameters', JSON.stringify(parameters))
    
    files.forEach((file) => {
      formData.append('input_files', file)
    })

    const response = await api.post('/executions/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async getExecution(id: string): Promise<Execution> {
    const api = this.ensureApiInitialized()
    const response = await api.get(`/executions/${id}`)
    return response.data
  }

  async getExecutions(limit: number = 100, offset: number = 0): Promise<Execution[]> {
    try {
      const api = this.ensureApiInitialized()
      console.log('API Service - getExecutions using API instance:', !!api)
      
      const response = await api.get(`/executions/?limit=${limit}&offset=${offset}`)
      console.log('Executions response:', response.data)
      return response.data
    } catch (error) {
      console.error('Error in getExecutions:', error)
      throw error
    }
  }

  async cancelExecution(id: string): Promise<void> {
    const api = this.ensureApiInitialized()
    await api.post(`/executions/${id}/cancel`)
  }

  // Component APIs
  async getComponents(): Promise<ComponentDefinition[]> {
    try {
      const api = this.ensureApiInitialized()
      console.log('API Service - getComponents using API instance:', !!api)
      console.log('Attempting to call GET /components')
      
      const response = await api.get('/components/')
      console.log('Components response:', response.data)
      return response.data
    } catch (error) {
      console.error('Error in getComponents:', error)
      throw error
    }
  }

  async getComponent(id: string): Promise<ComponentDefinition> {
    const api = this.ensureApiInitialized()
    const response = await api.get(`/components/${id}`)
    return response.data
  }

  // File APIs
  async uploadFile(file: File): Promise<{ file_id: string; filename: string; content_type: string }> {
    const api = this.ensureApiInitialized()
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/files/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async getFiles(): Promise<any[]> {
    const api = this.ensureApiInitialized()
    const response = await api.get('/files/')
    return response.data.files || response.data
  }

  async getFileContent(fileId: string): Promise<any> {
    const api = this.ensureApiInitialized()
    const response = await api.get(`/files/${fileId}/preview`)
    return response.data
  }

  async downloadFile(fileId: string): Promise<Blob> {
    const api = this.ensureApiInitialized()
    const response = await api.get(`/files/${fileId}`, {
      responseType: 'blob',
    })
    return response.data
  }

  async deleteFile(fileId: string): Promise<void> {
    const api = this.ensureApiInitialized()
    await api.delete(`/files/${fileId}`)
  }

  // gRPC Services APIs
  async getGrpcServicesHealth(): Promise<any[]> {
    const api = this.ensureApiInitialized()
    const response = await api.get('/grpc-services/health')
    return response.data
  }

  async getGrpcServiceHealth(serviceName: string): Promise<any> {
    const api = this.ensureApiInitialized()
    const response = await api.get(`/grpc-services/${serviceName}/health`)
    return response.data
  }

  async getGrpcServicesInfo(): Promise<any[]> {
    const api = this.ensureApiInitialized()
    const response = await api.get('/grpc-services/')
    return response.data
  }

  async restartGrpcService(serviceName: string): Promise<any> {
    const api = this.ensureApiInitialized()
    const response = await api.post(`/grpc-services/${serviceName}/restart`)
    return response.data
  }
}

export const apiService = new ApiService()