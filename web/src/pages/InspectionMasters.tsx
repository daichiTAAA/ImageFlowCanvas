import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  IconButton,
  Fab,
  Alert,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  QrCode as QrCodeIcon,
} from '@mui/icons-material';
import { inspectionApi } from '../services/api';

interface InspectionTarget {
  id: string;
  name: string;
  description?: string;
  product_code: string;
  version: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface InspectionItem {
  id: string;
  target_id: string;
  name: string;
  description?: string;
  type: string;
  pipeline_id?: string;
  pipeline_params?: Record<string, any>;
  execution_order: number;
  is_required: boolean;
  criteria_id?: string;
}

export function InspectionMasters() {
  const [targets, setTargets] = useState<InspectionTarget[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<InspectionTarget | null>(null);
  const [targetItems, setTargetItems] = useState<InspectionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingTarget, setEditingTarget] = useState<Partial<InspectionTarget> | null>(null);

  useEffect(() => {
    loadTargets();
  }, []);

  const loadTargets = async () => {
    try {
      setLoading(true);
      const response = await inspectionApi.listTargets();
      setTargets(response.items);
    } catch (error) {
      setError('検査対象の読み込みに失敗しました');
      console.error('Failed to load targets:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTargetItems = async (targetId: string) => {
    try {
      const response = await inspectionApi.listItems(targetId);
      setTargetItems(response.items);
    } catch (error) {
      console.error('Failed to load target items:', error);
    }
  };

  const handleTargetSelect = (target: InspectionTarget) => {
    setSelectedTarget(target);
    loadTargetItems(target.id);
  };

  const handleCreateTarget = () => {
    setEditingTarget({
      name: '',
      description: '',
      product_code: '',
      version: '1.0',
      metadata: {}
    });
    setOpenDialog(true);
  };

  const handleEditTarget = (target: InspectionTarget) => {
    setEditingTarget(target);
    setOpenDialog(true);
  };

  const handleSaveTarget = async () => {
    if (!editingTarget) return;

    try {
      setLoading(true);
      if (editingTarget.id) {
        // 更新
        await inspectionApi.updateTarget(editingTarget.id, editingTarget);
      } else {
        // 新規作成
        await inspectionApi.createTarget(editingTarget);
      }
      setOpenDialog(false);
      setEditingTarget(null);
      await loadTargets();
    } catch (error) {
      setError('検査対象の保存に失敗しました');
      console.error('Failed to save target:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTarget = async (targetId: string) => {
    if (!window.confirm('この検査対象を削除しますか？')) return;

    try {
      setLoading(true);
      await inspectionApi.deleteTarget(targetId);
      await loadTargets();
      if (selectedTarget?.id === targetId) {
        setSelectedTarget(null);
        setTargetItems([]);
      }
    } catch (error) {
      setError('検査対象の削除に失敗しました');
      console.error('Failed to delete target:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        検査マスタ管理
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* 検査対象一覧 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">検査対象</Typography>
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={handleCreateTarget}
                  disabled={loading}
                >
                  新規作成
                </Button>
              </Box>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>製品コード</TableCell>
                      <TableCell>名前</TableCell>
                      <TableCell>バージョン</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {targets.map((target) => (
                      <TableRow
                        key={target.id}
                        selected={selectedTarget?.id === target.id}
                        hover
                        onClick={() => handleTargetSelect(target)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>{target.product_code}</TableCell>
                        <TableCell>{target.name}</TableCell>
                        <TableCell>{target.version}</TableCell>
                        <TableCell>
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditTarget(target);
                            }}
                          >
                            <EditIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteTarget(target.id);
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* 検査項目一覧 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  検査項目 {selectedTarget && `- ${selectedTarget.name}`}
                </Typography>
                {selectedTarget && (
                  <Button variant="outlined" startIcon={<AddIcon />}>
                    項目追加
                  </Button>
                )}
              </Box>

              {selectedTarget ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>順序</TableCell>
                        <TableCell>名前</TableCell>
                        <TableCell>タイプ</TableCell>
                        <TableCell>必須</TableCell>
                        <TableCell>操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {targetItems.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell>{item.execution_order}</TableCell>
                          <TableCell>{item.name}</TableCell>
                          <TableCell>
                            <Chip
                              label={item.type}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={item.is_required ? '必須' : '任意'}
                              size="small"
                              color={item.is_required ? 'error' : 'default'}
                            />
                          </TableCell>
                          <TableCell>
                            <IconButton size="small">
                              <EditIcon />
                            </IconButton>
                            <IconButton size="small" color="error">
                              <DeleteIcon />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="textSecondary" textAlign="center" py={4}>
                  検査対象を選択してください
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 検査対象詳細・統計 */}
        {selectedTarget && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  検査対象詳細
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="製品コード"
                      value={selectedTarget.product_code}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="名前"
                      value={selectedTarget.name}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="説明"
                      value={selectedTarget.description || ''}
                      fullWidth
                      multiline
                      rows={2}
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="バージョン"
                      value={selectedTarget.version}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="作成日時"
                      value={new Date(selectedTarget.created_at).toLocaleString()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="更新日時"
                      value={new Date(selectedTarget.updated_at).toLocaleString()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* 検査対象編集ダイアログ */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingTarget?.id ? '検査対象編集' : '検査対象新規作成'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                label="製品コード"
                value={editingTarget?.product_code || ''}
                onChange={(e) =>
                  setEditingTarget(prev => prev ? { ...prev, product_code: e.target.value } : null)
                }
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="バージョン"
                value={editingTarget?.version || ''}
                onChange={(e) =>
                  setEditingTarget(prev => prev ? { ...prev, version: e.target.value } : null)
                }
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="名前"
                value={editingTarget?.name || ''}
                onChange={(e) =>
                  setEditingTarget(prev => prev ? { ...prev, name: e.target.value } : null)
                }
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="説明"
                value={editingTarget?.description || ''}
                onChange={(e) =>
                  setEditingTarget(prev => prev ? { ...prev, description: e.target.value } : null)
                }
                fullWidth
                multiline
                rows={3}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>キャンセル</Button>
          <Button
            onClick={handleSaveTarget}
            variant="contained"
            disabled={loading || !editingTarget?.name || !editingTarget?.product_code}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}