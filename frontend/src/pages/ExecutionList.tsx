import React from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  IconButton
} from '@mui/material'
import { Visibility, Refresh } from '@mui/icons-material'
import { useQuery } from 'react-query'
import { useAuth } from '../services/AuthContext'
import { apiService } from '../services/api'
import { Execution } from '../types'

export const ExecutionList: React.FC = () => {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const { data: executions = [], refetch } = useQuery<Execution[]>(
    'executions',
    () => apiService.getExecutions(50),
    {
      refetchInterval: 5000 // 5秒ごとに更新
    }
  )

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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          実行監視
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => refetch()}
        >
          更新
        </Button>
      </Box>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            実行履歴
          </Typography>
          {executions.length === 0 ? (
            <Typography color="textSecondary">
              実行履歴がありません
            </Typography>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>実行ID</TableCell>
                    <TableCell>パイプライン名</TableCell>
                    <TableCell>ステータス</TableCell>
                    <TableCell>進捗</TableCell>
                    <TableCell>作成日時</TableCell>
                    <TableCell>完了日時</TableCell>
                    <TableCell>アクション</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {executions.map((execution) => (
                    <TableRow key={execution.execution_id}>
                      <TableCell>
                        {execution.execution_id.substring(0, 8)}...
                      </TableCell>
                      <TableCell>
                        {execution.pipeline_id}
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
                      <TableCell>
                        {execution.completed_at 
                          ? new Date(execution.completed_at).toLocaleString() 
                          : '-'
                        }
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => navigate(`/execution/${execution.execution_id}`)}
                          title="詳細を表示"
                        >
                          <Visibility />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}