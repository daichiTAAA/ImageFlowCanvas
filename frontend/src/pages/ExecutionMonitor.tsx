import React, { useEffect, useState } from 'react'
import { Navigate, useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Alert,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab
} from '@mui/material'
import { Cancel, Download, Refresh, ArrowBack, Visibility } from '@mui/icons-material'
import { useQuery } from 'react-query'
import { useAuth } from '../services/AuthContext'
import { apiService } from '../services/api'
import { Execution } from '../types'

export const ExecutionMonitor: React.FC = () => {
  const { isAuthenticated } = useAuth()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [, setWsConnection] = useState<WebSocket | null>(null)
  const [previewDialog, setPreviewDialog] = useState<{
    open: boolean
    fileId: string
    filename: string
    imageUrl: string
  }>({ open: false, fileId: '', filename: '', imageUrl: '' })
  const [resultsTabValue, setResultsTabValue] = useState(0)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!id) {
    return <Navigate to="/" replace />
  }

  const { data: execution, refetch } = useQuery<Execution>(
    ['execution', id],
    () => apiService.getExecution(id),
    {
      refetchInterval: (data) => 
        data?.status === 'running' || data?.status === 'pending' ? 2000 : false
    }
  )

  useEffect(() => {
    // WebSocket接続を設定
    const token = localStorage.getItem('access_token')
    if (token) {
      const ws = new WebSocket(`ws://localhost:8000/v1/ws`)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        // 認証メッセージを送信
        ws.send(JSON.stringify({
          type: 'auth',
          token
        }))
        
        // 実行監視を開始
        ws.send(JSON.stringify({
          type: 'watch',
          execution_id: id
        }))
      }

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data)
        if (message.type === 'progress' && message.execution_id === id) {
          refetch()
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
      }

      setWsConnection(ws)

      return () => {
        ws.close()
      }
    }
  }, [id, refetch])

  const handleCancel = async () => {
    try {
      await apiService.cancelExecution(id)
      refetch()
    } catch (error) {
      console.error('Failed to cancel execution:', error)
    }
  }

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const blob = await apiService.downloadFile(fileId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Failed to download file:', error)
    }
  }

  const handlePreview = async (fileId: string, filename: string) => {
    try {
      const blob = await apiService.downloadFile(fileId)
      const imageUrl = window.URL.createObjectURL(blob)
      setPreviewDialog({
        open: true,
        fileId,
        filename,
        imageUrl
      })
    } catch (error) {
      console.error('Failed to preview file:', error)
    }
  }

  const handleClosePreview = () => {
    if (previewDialog.imageUrl) {
      window.URL.revokeObjectURL(previewDialog.imageUrl)
    }
    setPreviewDialog({ open: false, fileId: '', filename: '', imageUrl: '' })
  }

  const isImageFile = (filename: string) => {
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return imageExtensions.some(ext => filename.toLowerCase().endsWith(ext))
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'running': return 'primary'
      case 'failed': return 'error'
      case 'cancelled': return 'default'
      default: return 'warning'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return '待機中'
      case 'running': return '実行中'
      case 'completed': return '完了'
      case 'failed': return '失敗'
      case 'cancelled': return 'キャンセル'
      default: return status
    }
  }

  if (!execution) {
    return <Typography>読み込み中...</Typography>
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Button
          variant="outlined"
          startIcon={<ArrowBack />}
          onClick={() => navigate('/executions')}
        >
          実行監視一覧に戻る
        </Button>
        <Box>
          <Typography variant="h4">
            実行監視
          </Typography>
          <Typography variant="subtitle1" color="textSecondary">
            実行ID: {execution.execution_id}
          </Typography>
        </Box>
      </Box>

      {/* 実行状況サマリ */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              実行状況
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip
                label={getStatusText(execution.status)}
                color={getStatusColor(execution.status) as any}
              />
              {execution.status === 'running' && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Cancel />}
                  onClick={handleCancel}
                >
                  キャンセル
                </Button>
              )}
              <Button
                variant="outlined"
                size="small"
                startIcon={<Refresh />}
                onClick={() => refetch()}
              >
                更新
              </Button>
            </Box>
          </Box>

          <Typography variant="body2" gutterBottom>
            進捗: {execution.progress.current_step} ({execution.progress.completed_steps}/{execution.progress.total_steps})
          </Typography>
          
          <LinearProgress
            variant="determinate"
            value={execution.progress.percentage}
            sx={{ mb: 2 }}
          />
          
          <Typography variant="body2" color="textSecondary">
            {execution.progress.percentage.toFixed(1)}% 完了
          </Typography>

          {execution.error_message && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {execution.error_message}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* ステップ詳細 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            ステップ詳細
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>コンポーネント</TableCell>
                  <TableCell>ステータス</TableCell>
                  <TableCell>開始時刻</TableCell>
                  <TableCell>完了時刻</TableCell>
                  <TableCell>リソース使用量</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {execution.steps.map((step, index) => (
                  <TableRow key={index}>
                    <TableCell>{step.component_name}</TableCell>
                    <TableCell>
                      <Chip
                        label={getStatusText(step.status)}
                        color={getStatusColor(step.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {step.started_at ? new Date(step.started_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      {step.completed_at ? new Date(step.completed_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      {step.resource_usage ? (
                        <Typography variant="body2">
                          CPU: {step.resource_usage.cpu_usage}%
                          {step.resource_usage.memory_usage && `, MEM: ${step.resource_usage.memory_usage}MB`}
                          {step.resource_usage.gpu_usage && `, GPU: ${step.resource_usage.gpu_usage}%`}
                        </Typography>
                      ) : '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            処理結果
          </Typography>
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs value={resultsTabValue} onChange={(_, newValue) => setResultsTabValue(newValue)}>
              <Tab 
                label={`画像プレビュー ${execution.output_files.filter(f => isImageFile(f.filename)).length > 0 ? `(${execution.output_files.filter(f => isImageFile(f.filename)).length})` : ''}`}
              />
              <Tab 
                label={`ファイル一覧 ${execution.output_files.length > 0 ? `(${execution.output_files.length})` : ''}`}
              />
              <Tab label="処理詳細" />
            </Tabs>
          </Box>

          {/* 画像プレビュータブ */}
          {resultsTabValue === 0 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                処理結果画像
              </Typography>
              {execution.output_files.length === 0 ? (
                <Alert severity="info">
                  処理結果ファイルがまだ生成されていません。実行が完了するまでお待ちください。
                </Alert>
              ) : execution.output_files.filter(file => isImageFile(file.filename)).length === 0 ? (
                <Alert severity="warning">
                  画像ファイルが見つかりませんでした。「ファイル一覧」タブで他の出力ファイルを確認してください。
                </Alert>
              ) : (
                <Grid container spacing={2}>
                  {execution.output_files
                    .filter(file => isImageFile(file.filename))
                    .map((file) => (
                      <Grid item xs={12} sm={6} md={4} key={file.file_id}>
                        <Card>
                          <CardContent>
                            <Typography variant="subtitle2" gutterBottom noWrap>
                              {file.filename}
                            </Typography>
                            <Box
                              sx={{
                                width: '100%',
                                height: 200,
                                backgroundColor: '#f5f5f5',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                border: '1px dashed #ccc',
                                borderRadius: 1
                              }}
                              onClick={() => handlePreview(file.file_id, file.filename)}
                            >
                              <Typography color="textSecondary">
                                クリックで画像を表示
                              </Typography>
                            </Box>
                            <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<Visibility />}
                                onClick={() => handlePreview(file.file_id, file.filename)}
                              >
                                プレビュー
                              </Button>
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<Download />}
                                onClick={() => handleDownload(file.file_id, file.filename)}
                              >
                                DL
                              </Button>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                </Grid>
              )}
            </Box>
          )}

          {/* ファイル一覧タブ */}
          {resultsTabValue === 1 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                出力ファイル一覧
              </Typography>
              {execution.output_files.length === 0 ? (
                <Alert severity="info">
                  処理結果ファイルがまだ生成されていません。実行が完了するまでお待ちください。
                </Alert>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>ファイル名</TableCell>
                        <TableCell>タイプ</TableCell>
                        <TableCell>サイズ</TableCell>
                        <TableCell>アクション</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {execution.output_files.map((file) => (
                        <TableRow key={file.file_id}>
                          <TableCell>{file.filename}</TableCell>
                          <TableCell>
                            <Chip
                              label={isImageFile(file.filename) ? '画像' : 'その他'}
                              color={isImageFile(file.filename) ? 'primary' : 'default'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            {(file.file_size / 1024 / 1024).toFixed(2)} MB
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              {isImageFile(file.filename) && (
                                <Button
                                  variant="outlined"
                                  size="small"
                                  startIcon={<Visibility />}
                                  onClick={() => handlePreview(file.file_id, file.filename)}
                                >
                                  プレビュー
                                </Button>
                              )}
                              <Button
                                variant="outlined"
                                size="small"
                                startIcon={<Download />}
                                onClick={() => handleDownload(file.file_id, file.filename)}
                              >
                                ダウンロード
                              </Button>
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}

          {/* 処理詳細タブ */}
          {resultsTabValue === 2 && (
            <Box>
                <Typography variant="h6" gutterBottom>
                  処理詳細情報
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          実行統計
                        </Typography>
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="body2">
                            総実行時間: {execution.completed_at && execution.started_at 
                              ? `${Math.round((new Date(execution.completed_at).getTime() - new Date(execution.started_at).getTime()) / 1000)}秒`
                              : '実行中または未開始'
                            }
                          </Typography>
                          <Typography variant="body2">
                            処理ステップ数: {execution.steps.length}
                          </Typography>
                          <Typography variant="body2">
                            完了ステップ数: {execution.steps.filter(s => s.status === 'completed').length}
                          </Typography>
                          <Typography variant="body2">
                            出力ファイル数: {execution.output_files.length}
                          </Typography>
                          <Typography variant="body2">
                            総出力サイズ: {(execution.output_files.reduce((sum, f) => sum + f.file_size, 0) / 1024 / 1024).toFixed(2)} MB
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          リソース使用量
                        </Typography>
                        <Box sx={{ mt: 2 }}>
                          {execution.steps.some(s => s.resource_usage) ? (
                            execution.steps
                              .filter(s => s.resource_usage)
                              .map((step, index) => (
                                <Box key={index} sx={{ mb: 1 }}>
                                  <Typography variant="body2" fontWeight="bold">
                                    {step.component_name}:
                                  </Typography>
                                  <Typography variant="body2" color="textSecondary">
                                    CPU: {step.resource_usage?.cpu_usage}%
                                    {step.resource_usage?.memory_usage && `, MEM: ${step.resource_usage.memory_usage}MB`}
                                    {step.resource_usage?.gpu_usage && `, GPU: ${step.resource_usage.gpu_usage}%`}
                                  </Typography>
                                </Box>
                              ))
                          ) : (
                            <Typography variant="body2" color="textSecondary">
                              リソース使用量データがありません
                            </Typography>
                          )}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* 画像プレビューダイアログ */}
      <Dialog
        open={previewDialog.open}
        onClose={handleClosePreview}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {previewDialog.filename}
        </DialogTitle>
        <DialogContent>
          {previewDialog.imageUrl && (
            <Box
              component="img"
              src={previewDialog.imageUrl}
              alt={previewDialog.filename}
              sx={{
                width: '100%',
                height: 'auto',
                maxHeight: '70vh',
                objectFit: 'contain'
              }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePreview}>
            閉じる
          </Button>
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={() => {
              handleDownload(previewDialog.fileId, previewDialog.filename)
              handleClosePreview()
            }}
          >
            ダウンロード
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}