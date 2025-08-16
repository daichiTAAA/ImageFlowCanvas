import React, { useState, useEffect } from "react";
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
} from "@mui/material";
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  QrCode as QrCodeIcon,
} from "@mui/icons-material";
import { inspectionApi } from "../services/api";

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

interface ProductTypeGroup {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export function InspectionMasters() {
  const [targets, setTargets] = useState<InspectionTarget[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<InspectionTarget | null>(
    null
  );
  const [targetInspectionItems, setTargetInspectionItems] = useState<
    InspectionItem[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingTarget, setEditingTarget] =
    useState<Partial<InspectionTarget> | null>(null);
  const [openItemDialog, setOpenItemDialog] = useState(false);
  const [editingItem, setEditingItem] =
    useState<Partial<InspectionItem> | null>(null);
  // 型式グループ
  const [groups, setGroups] = useState<ProductTypeGroup[]>([]);
  const [openGroupDialog, setOpenGroupDialog] = useState(false);
  const [editingGroup, setEditingGroup] =
    useState<Partial<ProductTypeGroup> | null>(null);
  const [groupMembers, setGroupMembers] = useState<string[]>([]);
  const [memberInput, setMemberInput] = useState("");
  // 検査基準
  const [criterias, setCriterias] = useState<any[]>([]);
  const [openCriteriaDialog, setOpenCriteriaDialog] = useState(false);
  const [editingCriteria, setEditingCriteria] = useState<any | null>(null);

  useEffect(() => {
    loadTargets();
    loadGroups();
    loadCriterias();
  }, []);

  const loadTargets = async () => {
    try {
      setLoading(true);
      // Fetch more rows to avoid missing older targets due to pagination (default 20)
      const response = await inspectionApi.listInspectionTargets({
        page_size: 200,
      });
      setTargets(response.items);
    } catch (error) {
      setError("検査対象の読み込みに失敗しました");
      console.error("Failed to load targets:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const resp = await inspectionApi.listProductTypeGroups({
        page_size: 200,
      });
      setGroups(resp.items);
    } catch (e) {
      console.error("Failed to load groups", e);
    }
  };

  const loadCriterias = async () => {
    try {
      const resp = await inspectionApi.listCriterias({ page_size: 200 });
      setCriterias(resp.items);
    } catch (e) {
      console.error("Failed to load criterias", e);
    }
  };

  const loadTargetInspectionItems = async (targetId: string) => {
    try {
      const response = await inspectionApi.listItems(targetId);
      setTargetInspectionItems(response.items);
    } catch (error) {
      console.error("Failed to load target items:", error);
    }
  };

  const handleTargetSelect = (target: InspectionTarget) => {
    setSelectedTarget(target);
    loadTargetInspectionItems(target.id);
  };

  const handleCreateTarget = () => {
    setEditingTarget({
      name: "",
      description: "",
      product_code: "",
      // group_id はダイアログで選択
      version: "1.0",
      metadata: {},
    });
    setOpenDialog(true);
  };

  const handleCreateItem = () => {
    if (!selectedTarget) return;
    setEditingItem({
      target_id: selectedTarget.id,
      name: "",
      description: "",
      type: "VISUAL_INSPECTION",
      pipeline_id: "",
      pipeline_params: {},
      execution_order: (targetInspectionItems?.length || 0) + 1,
      is_required: true,
      criteria_id: "",
    });
    setOpenItemDialog(true);
  };

  const handleSaveItem = async () => {
    if (!editingItem || !selectedTarget) return;
    try {
      setLoading(true);
      const payload: any = {
        target_id: selectedTarget.id,
        name: editingItem.name,
        description: editingItem.description,
        type: editingItem.type,
        pipeline_id: editingItem.pipeline_id || undefined,
        pipeline_params: editingItem.pipeline_params || {},
        execution_order: editingItem.execution_order || 1,
        is_required: editingItem.is_required ?? true,
        criteria_id: editingItem.criteria_id || undefined,
      };
      if (editingItem.id) {
        await inspectionApi.updateInspectionItem(editingItem.id, payload);
      } else {
        await inspectionApi.createInspectionItem(payload);
      }
      setOpenItemDialog(false);
      setEditingItem(null);
      await loadTargetInspectionItems(selectedTarget.id);
    } catch (error) {
      setError("検査項目の保存に失敗しました");
      console.error("Failed to save item:", error);
    } finally {
      setLoading(false);
    }
  };
  const handleEditItem = (item: InspectionItem) => {
    setEditingItem(item);
    setOpenItemDialog(true);
  };
  const handleDeleteItem = async (item: InspectionItem) => {
    if (!selectedTarget) return;
    if (!window.confirm("この項目を削除しますか？")) return;
    try {
      setLoading(true);
      await inspectionApi.deleteInspectionItem(item.id);
      await loadTargetInspectionItems(selectedTarget.id);
    } catch (e) {
      setError("検査項目の削除に失敗しました");
    } finally {
      setLoading(false);
    }
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
        await inspectionApi.updateInspectionTarget(
          editingTarget.id,
          editingTarget
        );
      } else {
        // 新規作成
        await inspectionApi.createInspectionTarget(editingTarget);
      }
      setOpenDialog(false);
      setEditingTarget(null);
      await loadTargets();
    } catch (error) {
      setError("検査対象の保存に失敗しました");
      console.error("Failed to save target:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTarget = async (targetId: string) => {
    if (!window.confirm("この検査対象を削除しますか？")) return;

    try {
      setLoading(true);
      await inspectionApi.deleteInspectionTarget(targetId);
      await loadTargets();
      if (selectedTarget?.id === targetId) {
        setSelectedTarget(null);
        setTargetInspectionItems([]);
      }
    } catch (error) {
      setError("検査対象の削除に失敗しました");
      console.error("Failed to delete target:", error);
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
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
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
                        sx={{ cursor: "pointer" }}
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
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Typography variant="h6">
                  検査項目 {selectedTarget && `- ${selectedTarget.name}`}
                </Typography>
                {selectedTarget && (
                  <Button
                    variant="outlined"
                    startIcon={<AddIcon />}
                    onClick={handleCreateItem}
                  >
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
                      {targetInspectionItems.map((item) => (
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
                              label={item.is_required ? "必須" : "任意"}
                              size="small"
                              color={item.is_required ? "error" : "default"}
                            />
                          </TableCell>
                          <TableCell>
                            <IconButton
                              size="small"
                              onClick={() => handleEditItem(item)}
                            >
                              <EditIcon />
                            </IconButton>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteItem(item)}
                            >
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
                      value={selectedTarget.description || ""}
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
                      value={new Date(
                        selectedTarget.created_at
                      ).toLocaleString()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="更新日時"
                      value={new Date(
                        selectedTarget.updated_at
                      ).toLocaleString()}
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
      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingTarget?.id ? "検査対象編集" : "検査対象新規作成"}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                label="型式コード product_code（グループ設定時は空で可）"
                value={editingTarget?.product_code || ""}
                onChange={(e) =>
                  setEditingTarget((prev) =>
                    prev ? { ...prev, product_code: e.target.value } : null
                  )
                }
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="型式名 product_name（任意・表示用）"
                value={(editingTarget as any)?.product_name || ""}
                onChange={(e) =>
                  setEditingTarget((prev) =>
                    prev ? { ...prev, product_name: e.target.value } : null
                  )
                }
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                select
                SelectProps={{ native: true }}
                label="型式グループ group_id"
                value={(editingTarget as any)?.group_id || ""}
                onChange={(e) =>
                  setEditingTarget((prev) =>
                    prev ? { ...prev, group_id: e.target.value } : null
                  )
                }
                fullWidth
                helperText="グループを選択すると group_name は自動で設定できます"
              >
                <option value="">（未選択）</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={6}>
              <Button
                variant="outlined"
                onClick={() => {
                  const gid = (editingTarget as any)?.group_id;
                  const g = groups.find((x) => x.id === gid);
                  if (g)
                    setEditingTarget((prev) =>
                      prev ? { ...prev, group_name: g.name } : prev
                    );
                }}
              >
                グループ名を自動設定
              </Button>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="グループ名 group_name（任意・表示用）"
                value={(editingTarget as any)?.group_name || ""}
                onChange={(e) =>
                  setEditingTarget((prev) =>
                    prev ? { ...prev, group_name: e.target.value } : null
                  )
                }
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="バージョン"
                value={editingTarget?.version || ""}
                onChange={(e) =>
                  setEditingTarget((prev) =>
                    prev ? { ...prev, version: e.target.value } : null
                  )
                }
                fullWidth
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="名前"
                value={editingTarget?.name || ""}
                onChange={(e) =>
                  setEditingTarget((prev) =>
                    prev ? { ...prev, name: e.target.value } : null
                  )
                }
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="説明"
                value={editingTarget?.description || ""}
                onChange={(e) =>
                  setEditingTarget((prev) =>
                    prev ? { ...prev, description: e.target.value } : null
                  )
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
            disabled={
              loading ||
              !editingTarget?.name ||
              (!editingTarget?.product_code &&
                !(editingTarget as any)?.group_id)
            }
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 型式グループ 管理（簡易） */}
      <Box mt={4}>
        <Typography variant="h5" gutterBottom>
          型式グループ管理
        </Typography>
        <Button
          variant="outlined"
          onClick={() => {
            setEditingGroup({ name: "", description: "" });
            setOpenGroupDialog(true);
          }}
        >
          グループ作成
        </Button>
        <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>名前</TableCell>
                <TableCell>説明</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {groups.map((g) => (
                <TableRow key={g.id}>
                  <TableCell>{g.name}</TableCell>
                  <TableCell>{g.description}</TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      onClick={async () => {
                        setEditingGroup(g);
                        try {
                          const m =
                            await inspectionApi.listProductTypeGroupMembers(
                              g.id
                            );
                          setGroupMembers(m.map((x: any) => x.product_code));
                        } catch {}
                        setOpenGroupDialog(true);
                      }}
                    >
                      編集
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={async () => {
                        if (confirm("削除しますか？")) {
                          await inspectionApi.deleteProductTypeGroup(g.id);
                          loadGroups();
                        }
                      }}
                    >
                      削除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* 型式グループ編集ダイアログ */}
      <Dialog
        open={openGroupDialog}
        onClose={() => setOpenGroupDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {editingGroup?.id ? "型式グループ編集" : "型式グループ作成"}
        </DialogTitle>
        <DialogContent>
          <TextField
            label="名前"
            value={editingGroup?.name || ""}
            onChange={(e) =>
              setEditingGroup((prev) =>
                prev ? { ...prev, name: e.target.value } : prev
              )
            }
            fullWidth
            sx={{ mt: 1 }}
          />
          <TextField
            label="説明"
            value={editingGroup?.description || ""}
            onChange={(e) =>
              setEditingGroup((prev) =>
                prev ? { ...prev, description: e.target.value } : prev
              )
            }
            fullWidth
            sx={{ mt: 1 }}
          />
          {editingGroup?.id && (
            <Box mt={2}>
              <Typography variant="subtitle1">メンバー型式コード</Typography>
              <Box display="flex" gap={1} mt={1}>
                <TextField
                  label="型式コード product_code を追加"
                  value={memberInput}
                  onChange={(e) => setMemberInput(e.target.value)}
                  fullWidth
                />
                <Button
                  onClick={async () => {
                    if (!memberInput) return;
                    await inspectionApi.addProductTypeGroupMember(
                      editingGroup.id!,
                      memberInput
                    );
                    setMemberInput("");
                    const m = await inspectionApi.listProductTypeGroupMembers(
                      editingGroup.id!
                    );
                    setGroupMembers(m.map((x: any) => x.product_code));
                  }}
                >
                  追加
                </Button>
              </Box>
              <Box mt={1}>
                {groupMembers.length ? (
                  groupMembers.map((code) => (
                    <Chip
                      key={code}
                      label={code}
                      onDelete={async () => {
                        await inspectionApi.deleteProductTypeGroupMember(
                          editingGroup.id!,
                          code
                        );
                        const m =
                          await inspectionApi.listProductTypeGroupMembers(
                            editingGroup.id!
                          );
                        setGroupMembers(m.map((x: any) => x.product_code));
                      }}
                      sx={{ mr: 1, mb: 1 }}
                    />
                  ))
                ) : (
                  <Typography color="textSecondary">未登録</Typography>
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenGroupDialog(false)}>閉じる</Button>
          <Button
            variant="contained"
            onClick={async () => {
              try {
                if (editingGroup?.id) {
                  await inspectionApi.updateProductTypeGroup(editingGroup.id, {
                    name: editingGroup.name,
                    description: editingGroup.description,
                  });
                } else {
                  await inspectionApi.createProductTypeGroup({
                    name: editingGroup?.name,
                    description: editingGroup?.description,
                  });
                }
                setOpenGroupDialog(false);
                await loadGroups();
              } catch (e) {
                console.error(e);
              }
            }}
            disabled={!editingGroup?.name}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 検査基準 管理 */}
      <Box mt={4}>
        <Typography variant="h5" gutterBottom>
          検査基準管理
        </Typography>
        <Button
          variant="outlined"
          onClick={() => {
            setEditingCriteria({
              name: "",
              description: "",
              judgment_type: "BINARY",
              spec: { binary: { expected_value: true } },
            });
            setOpenCriteriaDialog(true);
          }}
        >
          基準を追加
        </Button>
        <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>名称</TableCell>
                <TableCell>判定タイプ</TableCell>
                <TableCell>説明</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {criterias.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>{c.name}</TableCell>
                  <TableCell>{c.judgment_type}</TableCell>
                  <TableCell>{c.description}</TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      onClick={() => {
                        setEditingCriteria(c);
                        setOpenCriteriaDialog(true);
                      }}
                    >
                      編集
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={async () => {
                        if (confirm("削除しますか？")) {
                          await inspectionApi.deleteInspectionCriteria(c.id);
                          await loadCriterias();
                        }
                      }}
                    >
                      削除
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* 検査基準 編集ダイアログ（JSON簡易入力） */}
      <Dialog
        open={openCriteriaDialog}
        onClose={() => setOpenCriteriaDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {editingCriteria?.id ? "検査基準編集" : "検査基準追加"}
        </DialogTitle>
        <DialogContent>
          <TextField
            label="名称"
            value={editingCriteria?.name || ""}
            onChange={(e) =>
              setEditingCriteria((p: any) => ({
                ...(p || {}),
                name: e.target.value,
              }))
            }
            fullWidth
            sx={{ mt: 1 }}
          />
          <TextField
            label="説明"
            value={editingCriteria?.description || ""}
            onChange={(e) =>
              setEditingCriteria((p: any) => ({
                ...(p || {}),
                description: e.target.value,
              }))
            }
            fullWidth
            sx={{ mt: 1 }}
          />
          <TextField
            label="判定タイプ（BINARY/NUMERICAL/CATEGORICAL/THRESHOLD）"
            value={editingCriteria?.judgment_type || "BINARY"}
            onChange={(e) =>
              setEditingCriteria((p: any) => ({
                ...(p || {}),
                judgment_type: e.target.value,
              }))
            }
            fullWidth
            sx={{ mt: 1 }}
          />
          <TextField
            label="基準仕様（JSON）"
            value={JSON.stringify(editingCriteria?.spec || {}, null, 2)}
            onChange={(e) => {
              try {
                const v = JSON.parse(e.target.value);
                setEditingCriteria((p: any) => ({ ...(p || {}), spec: v }));
              } catch (_) {}
            }}
            fullWidth
            multiline
            rows={8}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCriteriaDialog(false)}>
            キャンセル
          </Button>
          <Button
            variant="contained"
            onClick={async () => {
              try {
                setLoading(true);
                const payload = {
                  name: editingCriteria.name,
                  description: editingCriteria.description,
                  judgment_type: editingCriteria.judgment_type,
                  spec: editingCriteria.spec,
                };
                if (editingCriteria.id) {
                  await inspectionApi.updateInspectionCriteria(
                    editingCriteria.id,
                    payload
                  );
                } else {
                  await inspectionApi.createInspectionCriteria(payload);
                }
                setOpenCriteriaDialog(false);
                await loadCriterias();
              } catch (e) {
                setError("検査基準の保存に失敗しました");
              } finally {
                setLoading(false);
              }
            }}
            disabled={!editingCriteria?.name || !editingCriteria?.judgment_type}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 検査項目編集ダイアログ（新規作成用の簡易版） */}
      <Dialog
        open={openItemDialog}
        onClose={() => setOpenItemDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>検査項目の追加</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                label="項目名"
                value={editingItem?.name || ""}
                onChange={(e) =>
                  setEditingItem((prev) =>
                    prev ? { ...prev, name: e.target.value } : prev
                  )
                }
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="説明"
                value={editingItem?.description || ""}
                onChange={(e) =>
                  setEditingItem((prev) =>
                    prev ? { ...prev, description: e.target.value } : prev
                  )
                }
                fullWidth
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="タイプ"
                value={editingItem?.type || "VISUAL_INSPECTION"}
                onChange={(e) =>
                  setEditingItem((prev) =>
                    prev ? { ...prev, type: e.target.value } : prev
                  )
                }
                fullWidth
                placeholder="VISUAL_INSPECTION"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                type="number"
                label="順序"
                value={editingItem?.execution_order ?? 1}
                onChange={(e) =>
                  setEditingItem((prev) =>
                    prev
                      ? { ...prev, execution_order: Number(e.target.value) }
                      : prev
                  )
                }
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="パイプラインID"
                value={editingItem?.pipeline_id || ""}
                onChange={(e) =>
                  setEditingItem((prev) =>
                    prev ? { ...prev, pipeline_id: e.target.value } : prev
                  )
                }
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="必須 (true/false)"
                value={(editingItem?.is_required ?? true).toString()}
                onChange={(e) =>
                  setEditingItem((prev) =>
                    prev
                      ? {
                          ...prev,
                          is_required: e.target.value.toLowerCase() === "true",
                        }
                      : prev
                  )
                }
                fullWidth
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenItemDialog(false)}>キャンセル</Button>
          <Button
            onClick={handleSaveItem}
            variant="contained"
            disabled={loading || !editingItem?.name}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>
      {error && (
        <Box mt={2}>
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        </Box>
      )}
    </Box>
  );
}
