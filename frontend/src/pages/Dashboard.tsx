import React from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material'
import { Add, PlayArrow, Timeline } from '@mui/icons-material'
import { useQuery } from 'react-query'
import { useAuth } from '../services/AuthContext'
import { apiService } from '../services/api'

export const Dashboard: React.FC = () => {
  const { isAuthenticated, user } = useAuth()
  const navigate = useNavigate()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const { data: pipelines = [] } = useQuery('pipelines', () => apiService.getPipelines())
  const { data: executions = [] } = useQuery('executions', () => apiService.getExecutions(10))

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

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        ダッシュボード
      </Typography>
      <Typography variant="subtitle1" color="textSecondary" gutterBottom>
        ようこそ、{user?.username}さん
      </Typography>

      <Grid container spacing={3}>
        {/* 統計カード */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                パイプライン数
              </Typography>
              <Typography variant="h4">
                {pipelines.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                実行中
              </Typography>
              <Typography variant="h4">
                {executions.filter(e => e.status === 'running').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                完了
              </Typography>
              <Typography variant="h4">
                {executions.filter(e => e.status === 'completed').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                失敗
              </Typography>
              <Typography variant="h4">
                {executions.filter(e => e.status === 'failed').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* アクションボタン */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => navigate('/pipeline-builder')}
            >
              新しいパイプライン
            </Button>
            <Button
              variant="outlined"
              startIcon={<Timeline />}
              onClick={() => {/* TODO: 監視画面へ */}}
            >
              実行監視
            </Button>
          </Box>
        </Grid>

        {/* パイプライン一覧 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                パイプライン一覧
              </Typography>
              {pipelines.length === 0 ? (
                <Typography color="textSecondary">
                  パイプラインがありません
                </Typography>
              ) : (
                pipelines.map((pipeline) => (
                  <Box key={pipeline.id} sx={{ mb: 2, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                    <Typography variant="subtitle1">
                      {pipeline.name}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {pipeline.description}
                    </Typography>
                    <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PlayArrow />}
                        onClick={() => {/* TODO: 実行画面へ */}}
                      >
                        実行
                      </Button>
                    </Box>
                  </Box>
                ))
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 最近の実行履歴 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                最近の実行履歴
              </Typography>
              {executions.length === 0 ? (
                <Typography color="textSecondary">
                  実行履歴がありません
                </Typography>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>ID</TableCell>
                        <TableCell>ステータス</TableCell>
                        <TableCell>進捗</TableCell>
                        <TableCell>作成日時</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {executions.slice(0, 5).map((execution) => (
                        <TableRow key={execution.execution_id}>
                          <TableCell>
                            {execution.execution_id.substring(0, 8)}...
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={getStatusText(execution.status)}
                              color={getStatusColor(execution.status) as any}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            {execution.progress.percentage.toFixed(0)}%
                          </TableCell>
                          <TableCell>
                            {new Date(execution.created_at).toLocaleString()}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}