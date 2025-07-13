import React, { useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
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
  Alert
} from '@mui/material'
import { Cancel, Download, Refresh } from '@mui/icons-material'
import { useQuery } from 'react-query'
import { useAuth } from '../services/AuthContext'
import { apiService } from '../services/api'
import { Execution } from '../types'

export const ExecutionMonitor: React.FC = () => {
  const { isAuthenticated } = useAuth()
  const { id } = useParams<{ id: string }>()
  const [, setWsConnection] = useState<WebSocket | null>(null)

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
      refetchInterval: (data) => data?.status === 'running' ? 2000 : false
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
      <Typography variant="h4" gutterBottom>
        実行監視
      </Typography>
      <Typography variant="subtitle1" color="textSecondary" gutterBottom>
        実行ID: {execution.execution_id}
      </Typography>

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

      {/* 出力ファイル */}
      {execution.output_files.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              出力ファイル
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>ファイル名</TableCell>
                    <TableCell>サイズ</TableCell>
                    <TableCell>アクション</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {execution.output_files.map((file) => (
                    <TableRow key={file.file_id}>
                      <TableCell>{file.filename}</TableCell>
                      <TableCell>
                        {(file.file_size / 1024 / 1024).toFixed(2)} MB
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<Download />}
                          onClick={() => handleDownload(file.file_id, file.filename)}
                        >
                          ダウンロード
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}