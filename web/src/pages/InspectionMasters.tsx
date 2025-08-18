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
  Tooltip,
  Switch,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
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
  // group/process based targeting
  group_id?: string;
  process_code?: string;
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
  group_code?: string;
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
  const [groupMembersMap, setGroupMembersMap] = useState<Record<string, string[]>>({});
  const [aliasMap, setAliasMap] = useState<Record<string, string>>(() => {
    try {
      const raw = localStorage.getItem('productCodeAliases');
      return raw ? JSON.parse(raw) : {};
    } catch { return {}; }
  });
  const [memberInput, setMemberInput] = useState("");
  // 検査基準
  const [criterias, setCriterias] = useState<any[]>([]);
  const [openCriteriaDialog, setOpenCriteriaDialog] = useState(false);
  const [editingCriteria, setEditingCriteria] = useState<any | null>(null);
  const [targetSearch, setTargetSearch] = useState("");
  const [processes, setProcesses] = useState<any[]>([]);
  const [openProcessDialog, setOpenProcessDialog] = useState(false);
  const [editingProcess, setEditingProcess] = useState<any | null>(null);

  // 検査基準のバリデーション（保存ボタン制御用）
  const isCriteriaValid = React.useMemo(() => {
    if (!editingCriteria) return false;
    if (!editingCriteria.name || !editingCriteria.judgment_type) return false;
    const jt = String(editingCriteria.judgment_type || 'BINARY').toUpperCase();
    const spec = editingCriteria.spec || {};
    try {
      if (jt === 'BINARY') {
        return typeof spec.binary?.expected_value === 'boolean';
      }
      if (jt === 'THRESHOLD') {
        const th = spec.threshold?.threshold;
        const op = spec.threshold?.operator;
        return typeof th === 'number' && isFinite(th) && typeof op === 'string' && op.length > 0;
      }
      if (jt === 'CATEGORICAL') {
        return Array.isArray(spec.categorical?.allowed_categories);
      }
      if (jt === 'NUMERICAL') {
        const mn = spec.numerical?.min_value;
        const mx = spec.numerical?.max_value;
        return typeof mn === 'number' && isFinite(mn) && typeof mx === 'number' && isFinite(mx);
      }
      return true;
    } catch {
      return false;
    }
  }, [editingCriteria]);

  useEffect(() => {
    loadTargets();
    loadGroups();
    loadCriterias();
    loadProcesses();
  }, []);

  const loadTargets = async () => {
    try {
      setLoading(true);
      // Fetch more rows but within backend limit (<= 100)
      const response = await inspectionApi.listInspectionTargets({
        page_size: 100,
      });
      setTargets(response.items);
    } catch (error) {
      setError("検査対象マスタの読み込みに失敗しました");
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
      const items = resp.items || [];
      setGroups(items);
      // load members for each group to display in table
      const map: Record<string, string[]> = {};
      await Promise.all(
        items.map(async (g: any) => {
          try {
            const ms = await inspectionApi.listProductTypeGroupMembers(g.id);
            map[g.id] = (ms || []).map((x: any) => x.product_code);
          } catch {}
        })
      );
      setGroupMembersMap(map);
    } catch (e) {
      console.error("Failed to load groups", e);
    }
  };

  const loadCriterias = async () => {
    try {
      const resp = await inspectionApi.listCriterias({ page_size: 100 });
      setCriterias(resp.items);
    } catch (e) {
      console.error("Failed to load criterias", e);
    }
  };

  const loadProcesses = async () => {
    try {
      const resp = await inspectionApi.listProcesses({ page_size: 200 });
      setProcesses(resp.items || []);
    } catch (e) {
      console.error("Failed to load processes", e);
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
      setError("検査対象マスタの保存に失敗しました");
      console.error("Failed to save target:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTarget = async (targetId: string) => {
    if (!window.confirm("この検査対象マスタを削除しますか？")) return;

    try {
      setLoading(true);
      await inspectionApi.deleteInspectionTarget(targetId);
      await loadTargets();
      if (selectedTarget?.id === targetId) {
        setSelectedTarget(null);
        setTargetInspectionItems([]);
      }
    } catch (error) {
      setError("検査対象マスタの削除に失敗しました");
      console.error("Failed to delete target:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        検査対象マスタ管理
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* 検査対象マスタ一覧 */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
                gap={1}
              >
                <Typography variant="h6">検査対象マスタ</Typography>
                <Box display="flex" gap={1}>
                  <TextField
                    size="small"
                    placeholder="型式グループ/工程/検査対象マスタ名で検索"
                    value={targetSearch}
                    onChange={(e) => setTargetSearch(e.target.value)}
                  />
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleCreateTarget}
                    disabled={loading}
                  >
                    検査対象マスタを新規作成
                  </Button>
                </Box>
              </Box>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>型式グループ</TableCell>
                      <TableCell>工程</TableCell>
                      <TableCell>検査対象マスタ名</TableCell>
                      <TableCell>バージョン</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {targets
                      .filter((t) => {
                        const q = targetSearch.trim().toLowerCase();
                        if (!q) return true;
                        // Lookup group and process labels for filtering
                        const group = groups.find((g) => g.id === (t as any).group_id);
                        const groupText = group ? `${(group as any).group_code || ''} ${group.name || ''}`.toLowerCase() : '';
                        const process = processes.find((p: any) => p.process_code === (t as any).process_code);
                        const processText = process ? `${process.process_code || ''} ${process.process_name || ''}`.toLowerCase() : '';
                        const nameText = (t.name || '').toLowerCase();
                        return groupText.includes(q) || processText.includes(q) || nameText.includes(q);
                      })
                      .map((target) => (
                        <TableRow
                          key={target.id}
                          selected={selectedTarget?.id === target.id}
                          hover
                          onClick={() => handleTargetSelect(target)}
                          sx={{ cursor: "pointer" }}
                        >
                          <TableCell>
                            {(() => {
                              const gid = (target as any).group_id as string | undefined;
                              const g = gid ? groups.find((x) => x.id === gid) : undefined;
                              if (g) return `${(g as any).group_code || g.id} (${g.name})`;
                              return gid || '-';
                            })()}
                          </TableCell>
                          <TableCell>
                            {(() => {
                              const code = (target as any).process_code as string | undefined;
                              const p = code ? (processes as any[]).find((x) => x.process_code === code) : undefined;
                              if (p) return `${p.process_name} (${p.process_code})`;
                              return code || '-';
                            })()}
                          </TableCell>
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
                <Tooltip
                  title={
                    selectedTarget ? "" : "左の検査対象マスタを選択してください"
                  }
                >
                  <span>
                    <Button
                      variant="contained"
                      startIcon={<AddIcon />}
                      onClick={handleCreateItem}
                      disabled={!selectedTarget}
                    >
                      検査項目を追加
                    </Button>
                  </span>
                </Tooltip>
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
                <Box py={4}>
                  <Alert
                    severity="info"
                    sx={{ width: "fit-content", mx: "auto" }}
                    action={
                      <Button
                        color="inherit"
                        size="small"
                        onClick={handleCreateTarget}
                      >
                        検査対象マスタを作成
                      </Button>
                    }
                  >
                    右側の検査項目を追加するには、左の検査対象マスタを選択してください。
                  </Alert>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 検査対象マスタ詳細・統計 */}
        {selectedTarget && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  検査対象マスタ詳細
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="型式グループ"
                      value={(function(){
                        const gid = (selectedTarget as any).group_id as string | undefined;
                        const g = gid ? groups.find((x) => x.id === gid) : undefined;
                        if (g) return `${(g as any).group_code || g.id} (${g.name})`;
                        return gid || '-';
                      })()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="工程"
                      value={(function(){
                        const code = (selectedTarget as any).process_code as string | undefined;
                        const p = code ? (processes as any[]).find((x) => x.process_code === code) : undefined;
                        if (p) return `${p.process_name} (${p.process_code})`;
                        return code || '-';
                      })()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="検査対象マスタ名"
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

      {/* 検査対象マスタ編集ダイアログ */}
      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingTarget?.id ? "検査対象マスタ編集" : "検査対象マスタ新規作成"}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel id="group-select-label">
                  型式グループ group_id
                </InputLabel>
                <Select
                  labelId="group-select-label"
                  label="型式グループ group_id"
                  value={(editingTarget as any)?.group_id || ""}
                  renderValue={(sel) => {
                    const v = String(sel || "");
                    if (!v) return ""; // 未選択時は何も表示しない
                    const found = groups.find((g) => g.id === v);
                    return found?.name || v;
                  }}
                  onChange={(e) =>
                    setEditingTarget((prev) =>
                      prev
                        ? { ...prev, group_id: String(e.target.value) }
                        : null
                    )
                  }
                  displayEmpty
                >
                  <MenuItem value="">
                    <em>未選択</em>
                  </MenuItem>
                  {groups.map((g) => (
                    <MenuItem key={g.id} value={g.id}>
                      {g.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel id="process-select-label">
                  工程 process_code
                </InputLabel>
                <Select
                  labelId="process-select-label"
                  label="工程 process_code"
                  value={(editingTarget as any)?.process_code || ""}
                  renderValue={(sel) => {
                    const v = String(sel || "");
                    if (!v) return "";
                    const found = processes.find(
                      (p: any) => p.process_code === v
                    );
                    return found?.process_name || v;
                  }}
                  onChange={(e) =>
                    setEditingTarget((prev) =>
                      prev
                        ? { ...prev, process_code: String(e.target.value) }
                        : null
                    )
                  }
                  displayEmpty
                >
                  <MenuItem value="">
                    <em>未選択</em>
                  </MenuItem>
                  {processes.map((p: any) => (
                    <MenuItem key={p.process_code} value={p.process_code}>
                      {p.process_name} ({p.process_code})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
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
                label="検査対象マスタ名"
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
            <Grid item xs={12}>
              <Alert severity="info">
                型式グループ（group_id）と工程（process_code）の両方が必須です。
              </Alert>
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
              !(editingTarget as any)?.group_id ||
              !(editingTarget as any)?.process_code
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
        <Button variant="outlined" onClick={() => { setEditingGroup({ name: "", group_code: "", description: "" } as any); setOpenGroupDialog(true) }}>グループ作成</Button>
        <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
          <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>グループコード</TableCell>
                  <TableCell>グループ名</TableCell>
                  <TableCell>メンバー（型式コード/名）</TableCell>
                  <TableCell>説明</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
              {groups.map((g) => (
                <TableRow key={g.id}>
                  <TableCell>{(g as any).group_code || '-'}</TableCell>
                  <TableCell>{g.name}</TableCell>
                  <TableCell>
                    {(groupMembersMap[g.id] || []).slice(0, 6).map((code) => (
                      <Chip
                        key={code}
                        size="small"
                        label={aliasMap[code] ? `${aliasMap[code]} (${code})` : code}
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    ))}
                    {(groupMembersMap[g.id] || []).length > 6 && (
                      <Chip
                        size="small"
                        label={`+${(groupMembersMap[g.id] || []).length - 6}`}
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    )}
                    {!(groupMembersMap[g.id] || []).length && (
                      <Typography color="textSecondary">未登録</Typography>
                    )}
                  </TableCell>
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
                          const codes = m.map((x: any) => x.product_code);
                          setGroupMembers(codes);
                          setGroupMembersMap((prev) => ({ ...prev, [g.id]: codes }));
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
        <DialogTitle>{editingGroup?.id ? '型式グループ編集' : '型式グループ作成'}</DialogTitle>
        <DialogContent>
          <TextField label="型式グループコード" value={(editingGroup as any)?.group_code || ''} onChange={(e)=> setEditingGroup(prev => prev ? { ...prev, group_code: e.target.value } : prev)} fullWidth sx={{ mt: 1 }} disabled={!!editingGroup?.id} />
          <TextField label="型式グループ名" value={editingGroup?.name || ''} onChange={(e)=> setEditingGroup(prev => prev ? { ...prev, name: e.target.value } : prev)} fullWidth sx={{ mt: 1 }} />
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
              <Typography variant="subtitle1">メンバー（型式コード/名）</Typography>
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
                    const codes = m.map((x: any) => x.product_code);
                    setGroupMembers(codes);
                    setGroupMembersMap((prev) => ({ ...prev, [editingGroup.id!]: codes }));
                  }}
                >
                  追加
                </Button>
              </Box>
              <Box mt={2}>
                {groupMembers.length ? (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>型式コード</TableCell>
                          <TableCell>型式名（表示名）</TableCell>
                          <TableCell>操作</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {groupMembers.map((code) => (
                          <TableRow key={code}>
                            <TableCell width="30%">{code}</TableCell>
                            <TableCell>
                              <TextField
                                size="small"
                                placeholder="例: 製品A-黒"
                                value={aliasMap[code] || ''}
                                onChange={(e) => {
                                  const next = { ...aliasMap, [code]: e.target.value };
                                  setAliasMap(next);
                                  try { localStorage.setItem('productCodeAliases', JSON.stringify(next)); } catch {}
                                }}
                                fullWidth
                              />
                            </TableCell>
                            <TableCell width="120">
                              <Button
                                size="small"
                                color="error"
                                onClick={async () => {
                                  await inspectionApi.deleteProductTypeGroupMember(
                                    editingGroup.id!,
                                    code
                                  );
                                  const m = await inspectionApi.listProductTypeGroupMembers(
                                    editingGroup.id!
                                  );
                                  const codes = m.map((x: any) => x.product_code);
                                  setGroupMembers(codes);
                                  setGroupMembersMap((prev) => ({ ...prev, [editingGroup.id!]: codes }));
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
                    group_code: (editingGroup as any).group_code,
                    description: editingGroup.description,
                  } as any);
                } else {
                  await inspectionApi.createProductTypeGroup({
                    name: editingGroup?.name,
                    group_code: (editingGroup as any)?.group_code,
                    description: editingGroup?.description,
                  });
                }
                setOpenGroupDialog(false);
                await loadGroups();
              } catch (e) {
                console.error(e);
              }
            }}
            disabled={!editingGroup?.name || !(editingGroup as any)?.group_code}
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

      {/* 工程マスタ 管理 */}
      <Box mt={4}>
        <Typography variant="h5" gutterBottom>工程マスタ管理</Typography>
        <Button variant="outlined" onClick={() => { setEditingProcess({ process_code: '', process_name: '' }); setOpenProcessDialog(true) }}>工程を追加</Button>
        <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>工程コード</TableCell>
                <TableCell>工程名</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {processes.map((p: any) => (
                <TableRow key={p.process_code}>
                  <TableCell>{p.process_code}</TableCell>
                  <TableCell>{p.process_name}</TableCell>
                  <TableCell>
                    <Button size="small" onClick={() => { setEditingProcess(p); setOpenProcessDialog(true) }}>編集</Button>
                    <Button size="small" color="error" onClick={async () => { if (confirm('削除しますか？')) { await inspectionApi.deleteProcess(p.process_code); await loadProcesses() } }}>削除</Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* 工程 編集ダイアログ */}
      <Dialog open={openProcessDialog} onClose={() => setOpenProcessDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingProcess?.id ? '工程編集' : '工程追加'}</DialogTitle>
        <DialogContent>
          <TextField label="工程コード" value={editingProcess?.process_code || ''} onChange={(e)=> setEditingProcess((p:any)=> ({ ...(p||{}), process_code: e.target.value }))} fullWidth sx={{ mt: 1 }} disabled={!!editingProcess?.id} />
          <TextField label="工程名" value={editingProcess?.process_name || ''} onChange={(e)=> setEditingProcess((p:any)=> ({ ...(p||{}), process_name: e.target.value }))} fullWidth sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={()=> setOpenProcessDialog(false)}>キャンセル</Button>
          <Button variant="contained" disabled={!editingProcess?.process_code || !editingProcess?.process_name} onClick={async ()=>{
            try {
              setLoading(true)
              if (editingProcess?.id) {
                await inspectionApi.updateProcess(editingProcess.process_code, { process_name: editingProcess.process_name })
              } else {
                await inspectionApi.createProcess({ process_code: editingProcess.process_code, process_name: editingProcess.process_name })
              }
              setOpenProcessDialog(false)
              await loadProcesses()
            } catch (e) {
              setError('工程の保存に失敗しました')
            } finally { setLoading(false) }
          }}>保存</Button>
        </DialogActions>
      </Dialog>

      {/* 検査基準 編集ダイアログ（タイプ別の構造化入力） */}
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

          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel id="judge-type-label">判定タイプ</InputLabel>
            <Select
              labelId="judge-type-label"
              label="判定タイプ"
              value={(editingCriteria?.judgment_type || 'BINARY') as string}
              onChange={(e) => {
                const jt = String(e.target.value).toUpperCase();
                // タイプ変更時に、そのタイプのデフォルトspecへ初期化
                const defaultSpec: any = jt === 'BINARY'
                  ? { binary: { expected_value: true } }
                  : jt === 'THRESHOLD'
                  ? { threshold: { threshold: 1, operator: 'LESS_THAN_OR_EQUAL' } }
                  : jt === 'CATEGORICAL'
                  ? { categorical: { allowed_categories: [] } }
                  : { numerical: { min_value: 0, max_value: 1 } };
                setEditingCriteria((p: any) => ({ ...(p || {}), judgment_type: jt, spec: defaultSpec }));
              }}
            >
              <MenuItem value="BINARY">BINARY（検出有無）</MenuItem>
              <MenuItem value="THRESHOLD">THRESHOLD（検出数と閾値）</MenuItem>
              <MenuItem value="CATEGORICAL">CATEGORICAL（許可カテゴリ）</MenuItem>
              <MenuItem value="NUMERICAL">NUMERICAL（数値範囲）</MenuItem>
            </Select>
          </FormControl>

          {/* タイプ別フォーム */}
          {(() => {
            const jt = (editingCriteria?.judgment_type || 'BINARY').toUpperCase();
            const spec = editingCriteria?.spec || {};
            if (jt === 'BINARY') {
              const expected = !!(spec.binary?.expected_value ?? true);
              return (
                <FormControl fullWidth sx={{ mt: 2 }}>
                  <InputLabel id="binary-expected-label">OK条件</InputLabel>
                  <Select
                    labelId="binary-expected-label"
                    label="OK条件"
                    value={expected ? 'ZERO_OK' : 'PRESENT_OK'}
                    onChange={(e) => {
                      const v = String(e.target.value) === 'ZERO_OK';
                      setEditingCriteria((p: any) => ({ ...(p || {}), spec: { binary: { expected_value: v } } }));
                    }}
                  >
                    <MenuItem value="ZERO_OK">検出ゼロでOK</MenuItem>
                    <MenuItem value="PRESENT_OK">検出ありでOK</MenuItem>
                  </Select>
                </FormControl>
              );
            }
            if (jt === 'THRESHOLD') {
              const th = Number(spec.threshold?.threshold ?? 1);
              const op = String(spec.threshold?.operator || 'LESS_THAN_OR_EQUAL');
              return (
                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={6}>
                    <TextField
                      type="number"
                      label="閾値 (threshold)"
                      value={th}
                      onChange={(e) => {
                        const v = Number(e.target.value || 0);
                        setEditingCriteria((p: any) => ({ ...(p || {}), spec: { threshold: { threshold: v, operator: op } } }));
                      }}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <FormControl fullWidth>
                      <InputLabel id="op-label">比較演算</InputLabel>
                      <Select
                        labelId="op-label"
                        label="比較演算"
                        value={op}
                        onChange={(e) => {
                          const nv = String(e.target.value);
                          setEditingCriteria((p: any) => ({ ...(p || {}), spec: { threshold: { threshold: th, operator: nv } } }));
                        }}
                      >
                        <MenuItem value="LESS_THAN">LESS_THAN (&lt;)</MenuItem>
                        <MenuItem value="LESS_THAN_OR_EQUAL">LESS_THAN_OR_EQUAL (≤)</MenuItem>
                        <MenuItem value="GREATER_THAN">GREATER_THAN (&gt;)</MenuItem>
                        <MenuItem value="GREATER_THAN_OR_EQUAL">GREATER_THAN_OR_EQUAL (≥)</MenuItem>
                        <MenuItem value="EQUAL">EQUAL (=)</MenuItem>
                        <MenuItem value="NOT_EQUAL">NOT_EQUAL (≠)</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              );
            }
            if (jt === 'CATEGORICAL') {
              const allowed = (spec.categorical?.allowed_categories || []).join(',');
              return (
                <TextField
                  label="許可カテゴリ（カンマ区切り）"
                  value={allowed}
                  onChange={(e) => {
                    const arr = e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter((s) => s.length > 0);
                    setEditingCriteria((p: any) => ({ ...(p || {}), spec: { categorical: { allowed_categories: arr } } }));
                  }}
                  fullWidth
                  sx={{ mt: 2 }}
                />
              );
            }
            // NUMERICAL
            const min = (typeof spec.numerical?.min_value === 'number' ? spec.numerical.min_value : 0);
            const max = (typeof spec.numerical?.max_value === 'number' ? spec.numerical.max_value : 1);
            return (
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={6}>
                  <TextField
                    type="number"
                    label="最小値 (min)"
                    value={min}
                    onChange={(e) => {
                      const v = Number(e.target.value || 0);
                      setEditingCriteria((p: any) => ({ ...(p || {}), spec: { numerical: { min_value: v, max_value: max } } }));
                    }}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    type="number"
                    label="最大値 (max)"
                    value={max}
                    onChange={(e) => {
                      const v = Number(e.target.value || 0);
                      setEditingCriteria((p: any) => ({ ...(p || {}), spec: { numerical: { min_value: min, max_value: v } } }));
                    }}
                    fullWidth
                  />
                </Grid>
              </Grid>
            );
          })()}

          <TextField
            label="プレビュー（生成JSON）"
            value={JSON.stringify(editingCriteria?.spec || {}, null, 2)}
            fullWidth
            multiline
            rows={6}
            sx={{ mt: 2 }}
            InputProps={{ readOnly: true }}
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
            disabled={!isCriteriaValid || loading}
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
              <FormControl fullWidth>
                <InputLabel id="item-type-label">タイプ</InputLabel>
                <Select
                  labelId="item-type-label"
                  label="タイプ"
                  value={editingItem?.type || "VISUAL_INSPECTION"}
                  onChange={(e) =>
                    setEditingItem((prev) =>
                      prev ? { ...prev, type: String(e.target.value) } : prev
                    )
                  }
                >
                  {[
                    "VISUAL_INSPECTION",
                    "DIMENSIONAL_INSPECTION",
                    "FUNCTIONAL_INSPECTION",
                    "SURFACE_INSPECTION",
                    "COLOR_INSPECTION",
                  ].map((t) => (
                    <MenuItem key={t} value={t}>
                      {t}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
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
              <FormControlLabel
                control={
                  <Switch
                    checked={editingItem?.is_required ?? true}
                    onChange={(e) =>
                      setEditingItem((prev) =>
                        prev ? { ...prev, is_required: e.target.checked } : prev
                      )
                    }
                  />
                }
                label="必須"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel id="criteria-label">検査基準</InputLabel>
                <Select
                  labelId="criteria-label"
                  label="検査基準"
                  value={editingItem?.criteria_id || ""}
                  renderValue={(sel) => {
                    const v = String(sel || "");
                    if (!v) return ""; // 未設定時は何も表示しない
                    const found = criterias.find((c: any) => c.id === v);
                    return found?.name || v;
                  }}
                  onChange={(e) =>
                    setEditingItem((prev) =>
                      prev
                        ? {
                            ...prev,
                            criteria_id: String(e.target.value) || undefined,
                          }
                        : prev
                    )
                  }
                  displayEmpty
                >
                  <MenuItem value="">
                    <em>未設定</em>
                  </MenuItem>
                  {criterias.map((c: any) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
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
