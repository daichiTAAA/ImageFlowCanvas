import React, { useState, useCallback } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Drawer,
  List,
  ListItem,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Slider,
  Alert,
  CircularProgress
} from '@mui/material'
import { Save, PlayArrow, Upload } from '@mui/icons-material'
import { useQuery, useMutation } from 'react-query'
import { useAuth } from '../services/AuthContext'
import { apiService } from '../services/api'
import { ComponentDefinition, PipelineComponent } from '../types'

export const PipelineBuilder: React.FC = () => {
  const { isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  
  const [pipelineName, setPipelineName] = useState('')
  const [pipelineDescription, setPipelineDescription] = useState('')
  const [components, setComponents] = useState<PipelineComponent[]>([])
  const [selectedComponent, setSelectedComponent] = useState<ComponentDefinition | null>(null)
  const [parameterDialogOpen, setParameterDialogOpen] = useState(false)
  const [drawerOpen] = useState(true)
  const [testDialogOpen, setTestDialogOpen] = useState(false)
  const [testFiles, setTestFiles] = useState<File[]>([])

  // 認証の読み込み中は何も表示しない
  if (loading) {
    return <div>読み込み中...</div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const { data: availableComponents = [], error, isLoading } = useQuery<ComponentDefinition[], Error>(
    'components', 
    () => apiService.getComponents(),
    {
      enabled: isAuthenticated, // 認証済みの場合のみクエリを実行
      retry: 1,
      onError: (error) => {
        console.error('Components fetch error:', error)
      }
    }
  )

  // デバッグ用ログ
  console.log('Auth state:', { isAuthenticated, loading })
  console.log('API Service:', apiService)
  console.log('Components data:', availableComponents)
  console.log('Components error:', error)
  console.log('Components loading:', isLoading)

  const handleComponentDrop = useCallback((componentDef: ComponentDefinition) => {
    const newComponent: PipelineComponent = {
      id: `${componentDef.id}_${Date.now()}`,
      name: componentDef.name,
      component_type: componentDef.id as any,
      parameters: Object.entries(componentDef.parameters).reduce((acc, [key, param]) => {
        acc[key] = param.default
        return acc
      }, {} as Record<string, any>),
      dependencies: []
    }
    
    setComponents(prev => [...prev, newComponent])
  }, [])

  const handleComponentClick = (component: PipelineComponent) => {
    const componentDef = availableComponents.find(c => c.id === component.component_type)
    if (componentDef) {
      setSelectedComponent(componentDef)
      setParameterDialogOpen(true)
    }
  }

  const handleParameterSave = (parameters: Record<string, any>) => {
    if (!selectedComponent) return
    
    setComponents(prev => prev.map(comp => 
      comp.component_type === selectedComponent.id && comp.id === selectedComponent.id
        ? { ...comp, parameters }
        : comp
    ))
    setParameterDialogOpen(false)
    setSelectedComponent(null)
  }

  const handleSavePipeline = async () => {
    try {
      await apiService.createPipeline({
        name: pipelineName,
        description: pipelineDescription,
        components
      })
      navigate('/')
    } catch (error) {
      console.error('Failed to save pipeline:', error)
    }
  }

  const testExecutionMutation = useMutation(
    (files: File[]) => {
      // まずパイプラインを一時的に作成してからテスト実行
      const tempPipeline = {
        name: pipelineName || 'テスト用パイプライン',
        description: pipelineDescription || 'テスト実行用の一時パイプライン',
        components
      }
      return apiService.createPipeline(tempPipeline).then(pipeline => 
        apiService.executePipeline(pipeline.id, files)
      )
    },
    {
      onSuccess: (result) => {
        console.log('Test execution started:', result)
        setTestDialogOpen(false)
        setTestFiles([])
        // 実行監視画面に遷移する場合
        // navigate(`/execution-monitor/${result.execution_id}`)
      },
      onError: (error) => {
        console.error('Test execution failed:', error)
      }
    }
  )

  const handleTestExecution = () => {
    setTestDialogOpen(true)
  }

  const handleTestFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files) {
      setTestFiles(Array.from(files))
    }
  }

  const handleTestExecute = () => {
    if (testFiles.length > 0) {
      testExecutionMutation.mutate(testFiles)
    }
  }

  return (
    <Box sx={{ display: 'flex' }}>
      {/* コンポーネントパレット */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={drawerOpen}
        sx={{
          width: 300,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: 300,
            boxSizing: 'border-box',
            position: 'relative',
            height: 'auto'
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            コンポーネント
          </Typography>
          {isLoading && <Typography>読み込み中...</Typography>}
          {error && (
            <Typography color="error">
              コンポーネント読み込みエラー: {error.message}
            </Typography>
          )}
          {!isLoading && !error && availableComponents.length === 0 && (
            <Typography color="textSecondary">
              利用可能なコンポーネントがありません
            </Typography>
          )}
          <List>
            {availableComponents.map((component) => (
              <ListItem
                key={component.id}
                button
                onClick={() => handleComponentDrop(component)}
                sx={{ 
                  border: '1px solid #e0e0e0', 
                  borderRadius: 1, 
                  mb: 1,
                  '&:hover': { backgroundColor: '#f5f5f5' }
                }}
              >
                <ListItemText
                  primary={component.name}
                  secondary={component.description}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>

      {/* メインエリア */}
      <Box sx={{ flexGrow: 1, p: 3 }}>
        <Typography variant="h4" gutterBottom>
          パイプラインビルダー
        </Typography>

        <Grid container spacing={3}>
          {/* パイプライン設定 */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  パイプライン設定
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="パイプライン名"
                      value={pipelineName}
                      onChange={(e) => setPipelineName(e.target.value)}
                      required
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="説明"
                      multiline
                      rows={2}
                      value={pipelineDescription}
                      onChange={(e) => setPipelineDescription(e.target.value)}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* パイプラインキャンバス */}
          <Grid item xs={12}>
            <Card sx={{ minHeight: 400 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  パイプラインフロー
                </Typography>
                <Box 
                  sx={{ 
                    border: '2px dashed #ccc', 
                    borderRadius: 1, 
                    p: 2, 
                    minHeight: 300,
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 2
                  }}
                >
                  {components.length === 0 ? (
                    <Typography color="textSecondary" sx={{ margin: 'auto' }}>
                      左のパレットからコンポーネントを選択してください
                    </Typography>
                  ) : (
                    components.map((component, index) => (
                      <Card 
                        key={component.id}
                        sx={{ 
                          width: 200, 
                          cursor: 'pointer',
                          '&:hover': { backgroundColor: '#f5f5f5' }
                        }}
                        onClick={() => handleComponentClick(component)}
                      >
                        <CardContent>
                          <Typography variant="h6" fontSize="1rem">
                            {component.name}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            ステップ {index + 1}
                          </Typography>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* アクションボタン */}
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={handleSavePipeline}
                disabled={!pipelineName || components.length === 0}
              >
                保存
              </Button>
              <Button
                variant="outlined"
                startIcon={<PlayArrow />}
                disabled={!pipelineName || components.length === 0}
                onClick={handleTestExecution}
              >
                テスト実行
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* テスト実行ダイアログ */}
      <Dialog open={testDialogOpen} onClose={() => setTestDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          パイプラインテスト実行
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>
              テスト用のファイルを選択してください
            </Typography>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={handleTestFileSelect}
              style={{ display: 'none' }}
              id="test-file-input"
            />
            <label htmlFor="test-file-input">
              <Button
                component="span"
                variant="outlined"
                startIcon={<Upload />}
                fullWidth
                sx={{ mt: 1, mb: 2 }}
              >
                ファイルを選択
              </Button>
            </label>
            
            {testFiles.length > 0 && (
              <Box>
                <Typography variant="body2" gutterBottom>
                  選択されたファイル ({testFiles.length}件):
                </Typography>
                {testFiles.map((file, index) => (
                  <Typography key={index} variant="body2" color="textSecondary">
                    • {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </Typography>
                ))}
              </Box>
            )}
            
            {testExecutionMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                テスト実行に失敗しました: {testExecutionMutation.error instanceof Error 
                  ? testExecutionMutation.error.message 
                  : '不明なエラー'}
              </Alert>
            )}
            
            <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
              ※ テスト実行では一時的なパイプラインが作成され、実行されます
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTestDialogOpen(false)}>
            キャンセル
          </Button>
          <Button
            onClick={handleTestExecute}
            variant="contained"
            disabled={testFiles.length === 0 || testExecutionMutation.isLoading}
            startIcon={testExecutionMutation.isLoading ? <CircularProgress size={20} /> : <PlayArrow />}
          >
            テスト実行
          </Button>
        </DialogActions>
      </Dialog>

      {/* パラメータ設定ダイアログ */}
      <ParameterDialog
        open={parameterDialogOpen}
        onClose={() => setParameterDialogOpen(false)}
        component={selectedComponent}
        onSave={handleParameterSave}
      />
    </Box>
  )
}

interface ParameterDialogProps {
  open: boolean
  onClose: () => void
  component: ComponentDefinition | null
  onSave: (parameters: Record<string, any>) => void
}

const ParameterDialog: React.FC<ParameterDialogProps> = ({ open, onClose, component, onSave }) => {
  const [parameters, setParameters] = useState<Record<string, any>>({})

  React.useEffect(() => {
    if (component) {
      const defaultParams = Object.entries(component.parameters).reduce((acc, [key, param]) => {
        acc[key] = param.default
        return acc
      }, {} as Record<string, any>)
      setParameters(defaultParams)
    }
  }, [component])

  const handleSave = () => {
    onSave(parameters)
    onClose()
  }

  if (!component) return null

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{component.name} パラメータ設定</DialogTitle>
      <DialogContent>
        {Object.entries(component.parameters).map(([key, param]) => (
          <Box key={key} sx={{ mb: 2 }}>
            {param.type === 'string' && (
              param.options ? (
                <FormControl fullWidth>
                  <InputLabel>{param.description}</InputLabel>
                  <Select
                    value={parameters[key] || param.default}
                    onChange={(e) => setParameters(prev => ({ ...prev, [key]: e.target.value }))}
                  >
                    {param.options.map(option => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ) : (
                <TextField
                  fullWidth
                  label={param.description}
                  value={parameters[key] || param.default}
                  onChange={(e) => setParameters(prev => ({ ...prev, [key]: e.target.value }))}
                />
              )
            )}
            {param.type === 'integer' && (
              <TextField
                fullWidth
                type="number"
                label={param.description}
                value={parameters[key] || param.default}
                onChange={(e) => setParameters(prev => ({ ...prev, [key]: parseInt(e.target.value) }))}
              />
            )}
            {param.type === 'float' && (
              <Box>
                <Typography gutterBottom>{param.description}</Typography>
                <Slider
                  value={parameters[key] || param.default}
                  onChange={(_, value) => setParameters(prev => ({ ...prev, [key]: value }))}
                  min={param.min || 0}
                  max={param.max || 1}
                  step={0.1}
                  valueLabelDisplay="auto"
                />
              </Box>
            )}
            {param.type === 'boolean' && (
              <FormControlLabel
                control={
                  <Checkbox
                    checked={parameters[key] || param.default}
                    onChange={(e) => setParameters(prev => ({ ...prev, [key]: e.target.checked }))}
                  />
                }
                label={param.description}
              />
            )}
          </Box>
        ))}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>キャンセル</Button>
        <Button onClick={handleSave} variant="contained">保存</Button>
      </DialogActions>
    </Dialog>
  )
}