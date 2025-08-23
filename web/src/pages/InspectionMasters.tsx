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
import Autocomplete from "@mui/material/Autocomplete";
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  QrCode as QrCodeIcon,
} from "@mui/icons-material";
import { inspectionApi } from "../services/api";

interface inspectionInstruction {
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
  instruction_id: string;
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
  const [instructions, setInstructions] = useState<inspectionInstruction[]>([]);
  const [selectedInstruction, setSelectedInstruction] =
    useState<inspectionInstruction | null>(null);
  const [instructionInspectionItems, setInstructionInspectionItems] = useState<
    InspectionItem[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingInstruction, setEditingInstruction] =
    useState<Partial<inspectionInstruction> | null>(null);
  const [openItemDialog, setOpenItemDialog] = useState(false);
  const [editingItem, setEditingItem] =
    useState<Partial<InspectionItem> | null>(null);
  // 型式グループ
  const [groups, setGroups] = useState<ProductTypeGroup[]>([]);
  const [openGroupDialog, setOpenGroupDialog] = useState(false);
  const [editingGroup, setEditingGroup] =
    useState<Partial<ProductTypeGroup> | null>(null);
  const [groupMembers, setGroupMembers] = useState<string[]>([]);
  const [groupMembersMap, setGroupMembersMap] = useState<
    Record<string, string[]>
  >({});
  // 型式コード -> 型式名（サーバーマスタ）
  const [codeNameMap, setCodeNameMap] = useState<Record<string, string>>({});
  const [memberInput, setMemberInput] = useState("");
  // 検査基準
  const [criterias, setCriterias] = useState<any[]>([]);
  const [openCriteriaDialog, setOpenCriteriaDialog] = useState(false);
  const [editingCriteria, setEditingCriteria] = useState<any | null>(null);
  const [instructionSearch, setInstructionSearch] = useState("");
  const [processes, setProcesses] = useState<any[]>([]);
  const [openProcessDialog, setOpenProcessDialog] = useState(false);
  const [editingProcess, setEditingProcess] = useState<any | null>(null);
  // 型式コード・型式名マスタ一覧
  const [codeNameRows, setCodeNameRows] = useState<
    Array<{ product_code: string; product_name: string }>
  >([]);
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  // Pipeline list for item dialog
  const [pipelines, setPipelines] = useState<any[]>([]);

  // 検査基準のバリデーション（保存ボタン制御用）
  const isCriteriaValid = React.useMemo(() => {
    if (!editingCriteria) return false;
    if (!editingCriteria.name || !editingCriteria.judgment_type) return false;
    const jt = String(editingCriteria.judgment_type || "BINARY").toUpperCase();
    const spec = editingCriteria.spec || {};
    try {
      if (jt === "BINARY") {
        return typeof spec.binary?.expected_value === "boolean";
      }
      if (jt === "THRESHOLD") {
        const th = spec.threshold?.threshold;
        const op = spec.threshold?.operator;
        return (
          typeof th === "number" &&
          isFinite(th) &&
          typeof op === "string" &&
          op.length > 0
        );
      }
      if (jt === "CATEGORICAL") {
        return Array.isArray(spec.categorical?.allowed_categories);
      }
      if (jt === "NUMERICAL") {
        const mn = spec.numerical?.min_value;
        const mx = spec.numerical?.max_value;
        return (
          typeof mn === "number" &&
          isFinite(mn) &&
          typeof mx === "number" &&
          isFinite(mx)
        );
      }
      return true;
    } catch {
      return false;
    }
  }, [editingCriteria]);

  useEffect(() => {
    loadInstructions();
    loadGroups();
    loadCriterias();
    loadProcesses();
    loadPipelines();
    loadCodeNames();
  }, []);

  const loadInstructions = async () => {
    try {
      setLoading(true);
      // Fetch more rows but within backend limit (<= 100)
      const response = await inspectionApi.listinspectionInstructions({
        page_size: 100,
      });
      setInstructions(response.items);
    } catch (error) {
      setError("検査指示マスタの読み込みに失敗しました");
      console.error("Failed to load instructions:", error);
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

  const loadPipelines = async () => {
    try {
      const list = await inspectionApi.getPipelines();
      setPipelines(list || []);
    } catch (e) {
      console.error("Failed to load pipelines", e);
    }
  };

  const loadCodeNames = async () => {
    try {
      const resp = await inspectionApi.listProductTypeNames({ page_size: 500 });
      const rows = resp.items || [];
      setCodeNameRows(
        rows.map((x: any) => ({
          product_code: x.product_code,
          product_name: x.product_name,
        }))
      );
      const map: Record<string, string> = {};
      rows.forEach((x: any) => {
        map[x.product_code] = x.product_name;
      });
      setCodeNameMap(map);
    } catch (e) {
      console.error("Failed to load code-name master", e);
    }
  };

  const loadInstructionInspectionItems = async (instructionId: string) => {
    try {
      const response = await inspectionApi.listItems(instructionId);
      setInstructionInspectionItems(response.items);
    } catch (error) {
      console.error("Failed to load instruction items:", error);
    }
  };

  const handleInstructionSelect = (instruction: inspectionInstruction) => {
    setSelectedInstruction(instruction);
    loadInstructionInspectionItems(instruction.id);
  };

  const handleCreateInstruction = () => {
    setEditingInstruction({
      name: "",
      description: "",
      // group_id はダイアログで選択
      version: "1.0",
      metadata: {},
    });
    setOpenDialog(true);
  };

  const handleCreateItem = () => {
    if (!selectedInstruction) return;
    setEditingItem({
      instruction_id: selectedInstruction.id,
      name: "",
      description: "",
      type: "VISUAL_INSPECTION",
      pipeline_id: "",
      pipeline_params: {},
      execution_order: (instructionInspectionItems?.length || 0) + 1,
      is_required: true,
      criteria_id: "",
    });
    setOpenItemDialog(true);
  };

  const handleSaveItem = async () => {
    if (!editingItem || !selectedInstruction) return;
    try {
      setLoading(true);
      const payload: any = {
        instruction_id: selectedInstruction.id,
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
      await loadInstructionInspectionItems(selectedInstruction.id);
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
    if (!selectedInstruction) return;
    if (!window.confirm("この項目を削除しますか？")) return;
    try {
      setLoading(true);
      await inspectionApi.deleteInspectionItem(item.id);
      await loadInstructionInspectionItems(selectedInstruction.id);
    } catch (e) {
      setError("検査項目の削除に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleEditInstruction = (instruction: inspectionInstruction) => {
    setEditingInstruction(instruction);
    setOpenDialog(true);
  };

  const handleSaveInstruction = async () => {
    if (!editingInstruction) return;

    try {
      setLoading(true);
      if (editingInstruction.id) {
        // 更新
        await inspectionApi.updateinspectionInstruction(
          editingInstruction.id,
          editingInstruction
        );
      } else {
        // 新規作成
        await inspectionApi.createinspectionInstruction(editingInstruction);
      }
      setOpenDialog(false);
      setEditingInstruction(null);
      await loadInstructions();
    } catch (error) {
      setError("検査指示マスタの保存に失敗しました");
      console.error("Failed to save instruction:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteInstruction = async (instructionId: string) => {
    if (!window.confirm("この検査指示マスタを削除しますか？")) return;

    try {
      setLoading(true);
      await inspectionApi.deleteinspectionInstruction(instructionId);
      await loadInstructions();
      if (selectedInstruction?.id === instructionId) {
        setSelectedInstruction(null);
        setInstructionInspectionItems([]);
      }
    } catch (error) {
      setError("検査指示マスタの削除に失敗しました");
      console.error("Failed to delete instruction:", error);
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
        {/* 検査指示マスタ一覧 */}
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
                <Typography variant="h6">検査指示マスタ</Typography>
                <Box display="flex" gap={1}>
                  <TextField
                    size="small"
                    placeholder="型式グループ/工程/検査指示マスタ名で検索"
                    value={instructionSearch}
                    onChange={(e) => setInstructionSearch(e.target.value)}
                  />
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleCreateInstruction}
                    disabled={loading}
                  >
                    検査指示マスタを新規作成
                  </Button>
                </Box>
              </Box>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>型式グループ</TableCell>
                      <TableCell>工程</TableCell>
                      <TableCell>検査指示マスタ名</TableCell>
                      <TableCell>バージョン</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {instructions
                      .filter((t) => {
                        const q = instructionSearch.trim().toLowerCase();
                        if (!q) return true;
                        // Lookup group and process labels for filtering
                        const group = groups.find(
                          (g) => g.id === (t as any).group_id
                        );
                        const groupText = group
                          ? `${(group as any).group_code || ""} ${
                              group.name || ""
                            }`.toLowerCase()
                          : "";
                        const process = processes.find(
                          (p: any) => p.process_code === (t as any).process_code
                        );
                        const processText = process
                          ? `${process.process_code || ""} ${
                              process.process_name || ""
                            }`.toLowerCase()
                          : "";
                        const nameText = (t.name || "").toLowerCase();
                        return (
                          groupText.includes(q) ||
                          processText.includes(q) ||
                          nameText.includes(q)
                        );
                      })
                      .map((instruction) => (
                        <TableRow
                          key={instruction.id}
                          selected={selectedInstruction?.id === instruction.id}
                          hover
                          onClick={() => handleInstructionSelect(instruction)}
                          sx={{ cursor: "pointer" }}
                        >
                          <TableCell>
                            {(() => {
                              const gid = (instruction as any).group_id as
                                | string
                                | undefined;
                              const g = gid
                                ? groups.find((x) => x.id === gid)
                                : undefined;
                              if (g)
                                return `${(g as any).group_code || g.id} (${
                                  g.name
                                })`;
                              return gid || "-";
                            })()}
                          </TableCell>
                          <TableCell>
                            {(() => {
                              const code = (instruction as any).process_code as
                                | string
                                | undefined;
                              const p = code
                                ? (processes as any[]).find(
                                    (x) => x.process_code === code
                                  )
                                : undefined;
                              if (p)
                                return `${p.process_name} (${p.process_code})`;
                              return code || "-";
                            })()}
                          </TableCell>
                          <TableCell>{instruction.name}</TableCell>
                          <TableCell>{instruction.version}</TableCell>
                          <TableCell>
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEditInstruction(instruction);
                              }}
                            >
                              <EditIcon />
                            </IconButton>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteInstruction(instruction.id);
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
                  検査項目{" "}
                  {selectedInstruction && `- ${selectedInstruction.name}`}
                </Typography>
                <Tooltip
                  title={
                    selectedInstruction
                      ? ""
                      : "左の検査指示マスタを選択してください"
                  }
                >
                  <span>
                    <Button
                      variant="contained"
                      startIcon={<AddIcon />}
                      onClick={handleCreateItem}
                      disabled={!selectedInstruction}
                    >
                      検査項目を追加
                    </Button>
                  </span>
                </Tooltip>
              </Box>

              {selectedInstruction ? (
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
                      {instructionInspectionItems.map((item) => (
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
                        onClick={handleCreateInstruction}
                      >
                        検査指示マスタを作成
                      </Button>
                    }
                  >
                    右側の検査項目を追加するには、左の検査指示マスタを選択してください。
                  </Alert>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* 検査指示マスタ詳細・統計 */}
        {selectedInstruction && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  検査指示マスタ詳細
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="型式グループ"
                      value={(function () {
                        const gid = (selectedInstruction as any).group_id as
                          | string
                          | undefined;
                        const g = gid
                          ? groups.find((x) => x.id === gid)
                          : undefined;
                        if (g)
                          return `${(g as any).group_code || g.id} (${g.name})`;
                        return gid || "-";
                      })()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="工程"
                      value={(function () {
                        const code = (selectedInstruction as any)
                          .process_code as string | undefined;
                        const p = code
                          ? (processes as any[]).find(
                              (x) => x.process_code === code
                            )
                          : undefined;
                        if (p) return `${p.process_name} (${p.process_code})`;
                        return code || "-";
                      })()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="検査指示マスタ名"
                      value={selectedInstruction.name}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="説明"
                      value={selectedInstruction.description || ""}
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
                      value={selectedInstruction.version}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="作成日時"
                      value={new Date(
                        selectedInstruction.created_at
                      ).toLocaleString()}
                      fullWidth
                      InputProps={{ readOnly: true }}
                      margin="normal"
                    />
                    <TextField
                      label="更新日時"
                      value={new Date(
                        selectedInstruction.updated_at
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

      {/* 検査指示マスタ編集ダイアログ */}
      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingInstruction?.id
            ? "検査指示マスタ編集"
            : "検査指示マスタ新規作成"}
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
                  value={(editingInstruction as any)?.group_id || ""}
                  renderValue={(sel) => {
                    const v = String(sel || "");
                    if (!v) return ""; // 未選択時は何も表示しない
                    const found = groups.find((g) => g.id === v);
                    return found?.name || v;
                  }}
                  onChange={(e) =>
                    setEditingInstruction((prev) =>
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
                  value={(editingInstruction as any)?.process_code || ""}
                  renderValue={(sel) => {
                    const v = String(sel || "");
                    if (!v) return "";
                    const found = processes.find(
                      (p: any) => p.process_code === v
                    );
                    return found?.process_name || v;
                  }}
                  onChange={(e) =>
                    setEditingInstruction((prev) =>
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
                value={editingInstruction?.version || ""}
                onChange={(e) =>
                  setEditingInstruction((prev) =>
                    prev ? { ...prev, version: e.target.value } : null
                  )
                }
                fullWidth
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="検査指示マスタ名"
                value={editingInstruction?.name || ""}
                onChange={(e) =>
                  setEditingInstruction((prev) =>
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
                value={editingInstruction?.description || ""}
                onChange={(e) =>
                  setEditingInstruction((prev) =>
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
            onClick={handleSaveInstruction}
            variant="contained"
            disabled={
              loading ||
              !editingInstruction?.name ||
              !(editingInstruction as any)?.group_id ||
              !(editingInstruction as any)?.process_code
            }
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 型式コード・型式名マスタ 管理 */}
      <Box mt={4}>
        <Typography variant="h5" gutterBottom>
          型式コード・型式名マスタ
        </Typography>
        <Box mt={2} mb={1} display="flex" gap={1}>
          <TextField
            size="small"
            label="型式コード"
            value={newCode}
            onChange={(e) => setNewCode(e.target.value)}
          />
          <TextField
            size="small"
            label="型式名"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <Button
            variant="contained"
            onClick={async () => {
              if (!newCode || !newName) return;
              try {
                await inspectionApi.createProductTypeName({
                  product_code: newCode,
                  product_name: newName,
                });
              } catch {
                await inspectionApi.updateProductTypeName(newCode, {
                  product_name: newName,
                });
              }
              setNewCode("");
              setNewName("");
              await loadCodeNames();
            }}
          >
            追加/更新
          </Button>
        </Box>
        <TableContainer component={Paper} variant="outlined" sx={{ mt: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>型式コード</TableCell>
                <TableCell>型式名</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {codeNameRows.map((r) => (
                <TableRow key={r.product_code}>
                  <TableCell width="30%">{r.product_code}</TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      value={codeNameMap[r.product_code] ?? r.product_name}
                      onChange={(e) =>
                        setCodeNameMap((prev) => ({
                          ...prev,
                          [r.product_code]: e.target.value,
                        }))
                      }
                      fullWidth
                    />
                  </TableCell>
                  <TableCell width="150">
                    <Button
                      size="small"
                      onClick={async () => {
                        const name =
                          codeNameMap[r.product_code] ?? r.product_name;
                        try {
                          await inspectionApi.updateProductTypeName(
                            r.product_code,
                            { product_name: name }
                          );
                        } catch {}
                      }}
                    >
                      保存
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {codeNameRows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3}>
                    <Typography color="textSecondary">未登録</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
      <Box mt={4}>
        {/* 型式グループコード・型式グループ名マスタ 管理 */}
        <Typography variant="h5" gutterBottom>
          型式グループコード・型式グループ名マスタ
        </Typography>
        <Button
          variant="outlined"
          onClick={() => {
            setEditingGroup({
              name: "",
              group_code: "",
              description: "",
            } as any);
            setOpenGroupDialog(true);
          }}
        >
          グループ作成
        </Button>
        <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>型式グループコード</TableCell>
                <TableCell>型式グループ名</TableCell>
                <TableCell>メンバー（型式コード/名）</TableCell>
                <TableCell>説明</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {groups.map((g) => (
                <TableRow key={g.id}>
                  <TableCell>{(g as any).group_code || "-"}</TableCell>
                  <TableCell>{g.name}</TableCell>
                  <TableCell>
                    {(groupMembersMap[g.id] || []).slice(0, 6).map((code) => (
                      <Chip
                        key={code}
                        size="small"
                        label={
                          codeNameMap[code]
                            ? `${codeNameMap[code]} (${code})`
                            : code
                        }
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
                          setGroupMembersMap((prev) => ({
                            ...prev,
                            [g.id]: codes,
                          }));
                          // 併せて型式名をバッチ取得しマップへ格納
                          try {
                            const list =
                              await inspectionApi.getProductTypeNamesBatch(
                                codes
                              );
                            const cn: Record<string, string> = {
                              ...codeNameMap,
                            };
                            (list || []).forEach((e: any) => {
                              cn[e.product_code] = e.product_name;
                            });
                            setCodeNameMap(cn);
                          } catch {}
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
            label="型式グループコード"
            value={(editingGroup as any)?.group_code || ""}
            onChange={(e) =>
              setEditingGroup((prev) =>
                prev ? { ...prev, group_code: e.target.value } : prev
              )
            }
            fullWidth
            sx={{ mt: 1 }}
            disabled={!!editingGroup?.id}
          />
          <TextField
            label="型式グループ名"
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
              <Typography variant="subtitle1">
                メンバー（型式コード/名）
              </Typography>
              <Box display="flex" gap={1} mt={1}>
                <Autocomplete
                  options={codeNameRows as any}
                  getOptionLabel={(opt: any) =>
                    `${opt.product_name} (${opt.product_code})`
                  }
                  value={
                    (codeNameRows as any).find(
                      (o: any) => o.product_code === memberInput
                    ) || null
                  }
                  onChange={(_, val: any | null) =>
                    setMemberInput(val?.product_code || "")
                  }
                  renderInput={(params) => (
                    <TextField {...params} label="型式コードを選択" fullWidth />
                  )}
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
                    setGroupMembersMap((prev) => ({
                      ...prev,
                      [editingGroup.id!]: codes,
                    }));
                    try {
                      const ns = await inspectionApi.getProductTypeNamesBatch(
                        codes
                      );
                      const cn: Record<string, string> = { ...codeNameMap };
                      (ns || []).forEach((e: any) => {
                        cn[e.product_code] = e.product_name;
                      });
                      setCodeNameMap(cn);
                    } catch {}
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
                                value={codeNameMap[code] || ""}
                                onChange={(e) => {
                                  const next = {
                                    ...codeNameMap,
                                    [code]: e.target.value,
                                  };
                                  setCodeNameMap(next);
                                }}
                                fullWidth
                              />
                            </TableCell>
                            <TableCell width="200">
                              <Button
                                size="small"
                                onClick={async () => {
                                  const name = codeNameMap[code] || "";
                                  if (!name) return;
                                  try {
                                    await inspectionApi.createProductTypeName({
                                      product_code: code,
                                      product_name: name,
                                    });
                                  } catch {
                                    await inspectionApi.updateProductTypeName(
                                      code,
                                      { product_name: name }
                                    );
                                  }
                                }}
                                sx={{ mr: 1 }}
                              >
                                保存
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                onClick={async () => {
                                  await inspectionApi.deleteProductTypeGroupMember(
                                    editingGroup.id!,
                                    code
                                  );
                                  const m =
                                    await inspectionApi.listProductTypeGroupMembers(
                                      editingGroup.id!
                                    );
                                  const codes = m.map(
                                    (x: any) => x.product_code
                                  );
                                  setGroupMembers(codes);
                                  setGroupMembersMap((prev) => ({
                                    ...prev,
                                    [editingGroup.id!]: codes,
                                  }));
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
          検査基準管理マスタ
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
        <Typography variant="h5" gutterBottom>
          工程マスタ管理
        </Typography>
        <Button
          variant="outlined"
          onClick={() => {
            setEditingProcess({ process_code: "", process_name: "" });
            setOpenProcessDialog(true);
          }}
        >
          工程を追加
        </Button>
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
                    <Button
                      size="small"
                      onClick={() => {
                        setEditingProcess(p);
                        setOpenProcessDialog(true);
                      }}
                    >
                      編集
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      onClick={async () => {
                        if (confirm("削除しますか？")) {
                          await inspectionApi.deleteProcess(p.process_code);
                          await loadProcesses();
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

      {/* 工程 編集ダイアログ */}
      <Dialog
        open={openProcessDialog}
        onClose={() => setOpenProcessDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {editingProcess?.id ? "工程編集" : "工程追加"}
        </DialogTitle>
        <DialogContent>
          <TextField
            label="工程コード"
            value={editingProcess?.process_code || ""}
            onChange={(e) =>
              setEditingProcess((p: any) => ({
                ...(p || {}),
                process_code: e.target.value,
              }))
            }
            fullWidth
            sx={{ mt: 1 }}
            disabled={!!editingProcess?.id}
          />
          <TextField
            label="工程名"
            value={editingProcess?.process_name || ""}
            onChange={(e) =>
              setEditingProcess((p: any) => ({
                ...(p || {}),
                process_name: e.target.value,
              }))
            }
            fullWidth
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenProcessDialog(false)}>
            キャンセル
          </Button>
          <Button
            variant="contained"
            disabled={
              !editingProcess?.process_code || !editingProcess?.process_name
            }
            onClick={async () => {
              try {
                setLoading(true);
                if (editingProcess?.id) {
                  await inspectionApi.updateProcess(
                    editingProcess.process_code,
                    { process_name: editingProcess.process_name }
                  );
                } else {
                  await inspectionApi.createProcess({
                    process_code: editingProcess.process_code,
                    process_name: editingProcess.process_name,
                  });
                }
                setOpenProcessDialog(false);
                await loadProcesses();
              } catch (e) {
                setError("工程の保存に失敗しました");
              } finally {
                setLoading(false);
              }
            }}
          >
            保存
          </Button>
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
              value={(editingCriteria?.judgment_type || "BINARY") as string}
              onChange={(e) => {
                const jt = String(e.target.value).toUpperCase();
                // タイプ変更時に、そのタイプのデフォルトspecへ初期化
                const defaultSpec: any =
                  jt === "BINARY"
                    ? { binary: { expected_value: true } }
                    : jt === "THRESHOLD"
                    ? {
                        threshold: {
                          threshold: 1,
                          operator: "LESS_THAN_OR_EQUAL",
                        },
                      }
                    : jt === "CATEGORICAL"
                    ? { categorical: { allowed_categories: [] } }
                    : { numerical: { min_value: 0, max_value: 1 } };
                setEditingCriteria((p: any) => ({
                  ...(p || {}),
                  judgment_type: jt,
                  spec: defaultSpec,
                }));
              }}
            >
              <MenuItem value="BINARY">BINARY（検出有無）</MenuItem>
              <MenuItem value="THRESHOLD">THRESHOLD（検出数と閾値）</MenuItem>
              <MenuItem value="CATEGORICAL">
                CATEGORICAL（許可カテゴリ）
              </MenuItem>
              <MenuItem value="NUMERICAL">NUMERICAL（数値範囲）</MenuItem>
            </Select>
          </FormControl>

          {/* タイプ別フォーム */}
          {(() => {
            const jt = (
              editingCriteria?.judgment_type || "BINARY"
            ).toUpperCase();
            const spec = editingCriteria?.spec || {};
            if (jt === "BINARY") {
              const expected = !!(spec.binary?.expected_value ?? true);
              return (
                <FormControl fullWidth sx={{ mt: 2 }}>
                  <InputLabel id="binary-expected-label">OK条件</InputLabel>
                  <Select
                    labelId="binary-expected-label"
                    label="OK条件"
                    value={expected ? "ZERO_OK" : "PRESENT_OK"}
                    onChange={(e) => {
                      const v = String(e.target.value) === "ZERO_OK";
                      setEditingCriteria((p: any) => ({
                        ...(p || {}),
                        spec: { binary: { expected_value: v } },
                      }));
                    }}
                  >
                    <MenuItem value="ZERO_OK">検出ゼロでOK</MenuItem>
                    <MenuItem value="PRESENT_OK">検出ありでOK</MenuItem>
                  </Select>
                </FormControl>
              );
            }
            if (jt === "THRESHOLD") {
              const th = Number(spec.threshold?.threshold ?? 1);
              const op = String(
                spec.threshold?.operator || "LESS_THAN_OR_EQUAL"
              );
              return (
                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={6}>
                    <TextField
                      type="number"
                      label="閾値 (threshold)"
                      value={th}
                      onChange={(e) => {
                        const v = Number(e.target.value || 0);
                        setEditingCriteria((p: any) => ({
                          ...(p || {}),
                          spec: { threshold: { threshold: v, operator: op } },
                        }));
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
                          setEditingCriteria((p: any) => ({
                            ...(p || {}),
                            spec: {
                              threshold: { threshold: th, operator: nv },
                            },
                          }));
                        }}
                      >
                        <MenuItem value="LESS_THAN">LESS_THAN (&lt;)</MenuItem>
                        <MenuItem value="LESS_THAN_OR_EQUAL">
                          LESS_THAN_OR_EQUAL (≤)
                        </MenuItem>
                        <MenuItem value="GREATER_THAN">
                          GREATER_THAN (&gt;)
                        </MenuItem>
                        <MenuItem value="GREATER_THAN_OR_EQUAL">
                          GREATER_THAN_OR_EQUAL (≥)
                        </MenuItem>
                        <MenuItem value="EQUAL">EQUAL (=)</MenuItem>
                        <MenuItem value="NOT_EQUAL">NOT_EQUAL (≠)</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              );
            }
            if (jt === "CATEGORICAL") {
              const allowed = (spec.categorical?.allowed_categories || []).join(
                ","
              );
              return (
                <TextField
                  label="許可カテゴリ（カンマ区切り）"
                  value={allowed}
                  onChange={(e) => {
                    const arr = e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter((s) => s.length > 0);
                    setEditingCriteria((p: any) => ({
                      ...(p || {}),
                      spec: { categorical: { allowed_categories: arr } },
                    }));
                  }}
                  fullWidth
                  sx={{ mt: 2 }}
                />
              );
            }
            // NUMERICAL
            const min =
              typeof spec.numerical?.min_value === "number"
                ? spec.numerical.min_value
                : 0;
            const max =
              typeof spec.numerical?.max_value === "number"
                ? spec.numerical.max_value
                : 1;
            return (
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={6}>
                  <TextField
                    type="number"
                    label="最小値 (min)"
                    value={min}
                    onChange={(e) => {
                      const v = Number(e.target.value || 0);
                      setEditingCriteria((p: any) => ({
                        ...(p || {}),
                        spec: { numerical: { min_value: v, max_value: max } },
                      }));
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
                      setEditingCriteria((p: any) => ({
                        ...(p || {}),
                        spec: { numerical: { min_value: min, max_value: v } },
                      }));
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
              <Autocomplete
                options={pipelines as any}
                getOptionLabel={(p: any) =>
                  p?.name ? `${p.name} (${p.id})` : p?.id || ""
                }
                value={
                  (pipelines as any).find(
                    (p: any) =>
                      String(p.id) === String(editingItem?.pipeline_id)
                  ) || null
                }
                onChange={(_, val: any | null) =>
                  setEditingItem((prev) =>
                    prev ? { ...prev, pipeline_id: val?.id || undefined } : prev
                  )
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="パイプライン"
                    placeholder="選択"
                    fullWidth
                  />
                )}
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
