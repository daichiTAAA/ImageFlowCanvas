import React, { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Alert,
  Pagination,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  LinearProgress,
  Avatar,
} from "@mui/material";
import {
  Visibility as ViewIcon,
  GetApp as DownloadIcon,
  Assessment as AssessmentIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Warning as WarningIcon,
  Schedule as ScheduleIcon,
} from "@mui/icons-material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { inspectionApi } from "../services/api";

// Robust local time formatter that handles ISO with/without timezone, millis epoch, and Safari quirks
function formatLocalDateTime(value?: string | number): string {
  if (!value) return "-";
  // Millis epoch (string or number)
  if (typeof value === "number") return new Date(value).toLocaleString();
  if (/^\d{10,}$/.test(value)) {
    const ms = parseInt(value, 10);
    if (!isNaN(ms)) return new Date(ms).toLocaleString();
  }
  let s = value;
  // Normalize: if no timezone info, assume UTC and append 'Z'
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(s);
  if (!hasTz) {
    // Replace space with 'T' for Safari compatibility
    if (s.indexOf("T") === -1) s = s.replace(" ", "T");
    s = s + "Z";
  }
  const d = new Date(s);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

interface InspectionExecution {
  id: string;
  instruction_id: string;
  operator_id?: string;
  status: string;
  qr_code?: string;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  metadata?: Record<string, any>;
  instruction?: {
    id: string;
    name: string;
    product_name?: string;
    group_name?: string;
  };
}

interface InspectionResult {
  id: string;
  execution_id: string;
  item_execution_id: string;
  judgment: string;
  comment?: string;
  confidence_score?: number;
  processing_time_ms?: number;
  created_at: string;
  evidence_file_ids?: string[];
  metrics?: Record<string, any>;
}

interface InspectionItemExecution {
  id: string;
  execution_id: string;
  item_id: string;
  status: string;
  ai_result?: Record<string, any>;
  human_result?: Record<string, any>;
  final_result?: string;
  started_at: string;
  completed_at?: string;
  item?: {
    name: string;
    type: string;
    execution_order: number;
  };
}

const StatusChip = ({ status }: { status: string }) => {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return {
          color: "success" as const,
          icon: <CheckIcon />,
          label: "完了",
        };
      case "FAILED":
        return { color: "error" as const, icon: <CancelIcon />, label: "失敗" };
      case "IN_PROGRESS":
        return {
          color: "info" as const,
          icon: <ScheduleIcon />,
          label: "実行中",
        };
      case "PENDING":
        return {
          color: "default" as const,
          icon: <ScheduleIcon />,
          label: "待機中",
        };
      default:
        return {
          color: "default" as const,
          icon: <WarningIcon />,
          label: status,
        };
    }
  };

  const config = getStatusConfig(status);
  return (
    <Chip
      component="span"
      icon={config.icon}
      label={config.label}
      color={config.color}
      size="small"
    />
  );
};

const JudgmentChip = ({ judgment }: { judgment: string }) => {
  const getJudgmentConfig = (judgment: string) => {
    switch (judgment) {
      case "OK":
        return { color: "success" as const, label: "OK" };
      case "NG":
        return { color: "error" as const, label: "NG" };
      case "PENDING_REVIEW":
        return { color: "warning" as const, label: "確認待ち" };
      case "INCONCLUSIVE":
        return { color: "default" as const, label: "判定不能" };
      default:
        return { color: "default" as const, label: judgment };
    }
  };

  const config = getJudgmentConfig(judgment);
  return (
    <Chip
      component="span"
      label={config.label}
      color={config.color}
      size="small"
    />
  );
};

export function InspectionResults() {
  const [activeTab, setActiveTab] = useState(0);
  const [executions, setExecutions] = useState<InspectionExecution[]>([]);
  const [results, setResults] = useState<InspectionResult[]>([]);
  const [selectedExecution, setSelectedExecution] =
    useState<InspectionExecution | null>(null);
  const [itemExecutions, setItemExecutions] = useState<
    InspectionItemExecution[]
  >([]);
  // item_execution_id -> evidence_file_ids
  const [execResultsByItem, setExecResultsByItem] = useState<
    Record<string, string[]>
  >({});
  // item_execution_id -> ObjectURL (auth-safe thumbnail)
  const [thumbUrlsByItem, setThumbUrlsByItem] = useState<
    Record<string, string>
  >({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailDialog, setDetailDialog] = useState(false);
  // 型式コード -> 型式名（code-nameマスタ）マップ
  const [codeToProductName, setCodeToProductName] = useState<
    Record<string, string>
  >({});

  // フィルタ状態
  const [filters, setFilters] = useState({
    status: "",
    judgment: "",
    fromDate: null as Date | null,
    toDate: null as Date | null,
    instructionId: "",
  });

  // ページネーション
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    if (activeTab === 0) {
      loadExecutions();
    } else {
      loadResults();
    }
  }, [activeTab, page, filters]);

  useEffect(() => {
    // 型式コード・型式名マスタから、型式コード -> 型式名 を構築
    (async () => {
      try {
        const res = await inspectionApi.listProductTypeNames({
          page_size: 500,
        });
        const items = res.items || [];
        const map: Record<string, string> = {};
        items.forEach((e: any) => {
          if (e?.product_code) map[e.product_code] = e.product_name || "";
        });
        setCodeToProductName(map);
      } catch (e) {
        console.warn(
          "Failed to load product code-name master for code->name map",
          e
        );
      }
    })();
  }, []);

  const loadExecutions = async () => {
    try {
      setLoading(true);
      const response = await inspectionApi.listInspectionExecutions({
        page,
        page_size: pageSize,
        status: filters.status || undefined,
        instruction_id: filters.instructionId || undefined,
        from_date: filters.fromDate?.toISOString(),
        to_date: filters.toDate?.toISOString(),
      });
      setExecutions(response.items);
      setTotalPages(response.total_pages);
    } catch (error) {
      setError("検査実行履歴の読み込みに失敗しました");
      console.error("Failed to load executions:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadResults = async () => {
    try {
      setLoading(true);
      const response = await inspectionApi.listInspectionResults({
        page,
        page_size: pageSize,
        judgment: filters.judgment || undefined,
        instruction_id: filters.instructionId || undefined,
        from_date: filters.fromDate?.toISOString(),
        to_date: filters.toDate?.toISOString(),
      });
      setResults(response.items);
      setTotalPages(response.total_pages);
    } catch (error) {
      setError("検査結果の読み込みに失敗しました");
      console.error("Failed to load results:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadExecutionDetails = async (execution: InspectionExecution) => {
    try {
      setLoading(true);
      const response = await inspectionApi.getInspectionExecutionItems(
        execution.id
      );
      setItemExecutions(response);
      // 同一実行の結果一覧を取得し、項目実行IDごとの画像を紐付け
      try {
        // Backend enforces page_size <= 100. Fetch enough to cover
        // all item executions in a single execution.
        const res = await inspectionApi.listInspectionResults({
          execution_id: execution.id,
          page: 1,
          page_size: 100,
        });
        const byItem: Record<string, string[]> = {};
        (res.items || []).forEach((r: any) => {
          if (
            r.item_execution_id &&
            r.evidence_file_ids &&
            r.evidence_file_ids.length > 0
          ) {
            byItem[r.item_execution_id] = r.evidence_file_ids;
          }
        });
        setExecResultsByItem(byItem);
        const pairs: [string, string][] = [];
        for (const [itemExecId, ids] of Object.entries(byItem)) {
          const fileId = ids[0];
          try {
            const blob = await inspectionApi.downloadFile(fileId);
            const url = URL.createObjectURL(blob);
            pairs.push([itemExecId, url]);
          } catch (_e) {}
        }
        setThumbUrlsByItem(Object.fromEntries(pairs));
      } catch (e) {
        console.warn("Failed to load execution results for images", e);
        setExecResultsByItem({});
        setThumbUrlsByItem({});
      }
      setSelectedExecution(execution);
      setDetailDialog(true);
    } catch (error) {
      setError("検査詳細の読み込みに失敗しました");
      console.error("Failed to load execution details:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setPage(1);
  };

  const handleFilterChange = (field: string, value: any) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
    setPage(1);
  };

  const exportResults = async () => {
    try {
      // TODO: 実装
      console.log("Exporting results...");
    } catch (error) {
      setError("エクスポートに失敗しました");
    }
  };

  // 結果画像を安全に取得して新しいタブで表示
  const openEvidence = async (fileId: string) => {
    try {
      const blob = await inspectionApi.downloadFile(fileId);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      // しばらくして開放（即時revokeすると表示できないブラウザがある）
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      setError("結果の取得に失敗しました");
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        <Typography variant="h4" gutterBottom>
          検査結果管理
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* フィルタセクション */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              フィルタ
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={2}>
                <FormControl fullWidth>
                  <InputLabel>ステータス</InputLabel>
                  <Select
                    value={filters.status}
                    onChange={(e) =>
                      handleFilterChange("status", e.target.value)
                    }
                    label="ステータス"
                  >
                    <MenuItem value="">すべて</MenuItem>
                    <MenuItem value="PENDING">待機中</MenuItem>
                    <MenuItem value="IN_PROGRESS">実行中</MenuItem>
                    <MenuItem value="COMPLETED">完了</MenuItem>
                    <MenuItem value="FAILED">失敗</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={2}>
                <FormControl fullWidth>
                  <InputLabel>判定結果</InputLabel>
                  <Select
                    value={filters.judgment}
                    onChange={(e) =>
                      handleFilterChange("judgment", e.target.value)
                    }
                    label="判定結果"
                  >
                    <MenuItem value="">すべて</MenuItem>
                    <MenuItem value="OK">OK</MenuItem>
                    <MenuItem value="NG">NG</MenuItem>
                    <MenuItem value="PENDING_REVIEW">確認待ち</MenuItem>
                    <MenuItem value="INCONCLUSIVE">判定不能</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={2}>
                <DatePicker
                  label="開始日"
                  value={filters.fromDate}
                  onChange={(date) => handleFilterChange("fromDate", date)}
                  slotProps={{ textField: { fullWidth: true } }}
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <DatePicker
                  label="終了日"
                  value={filters.toDate}
                  onChange={(date) => handleFilterChange("toDate", date)}
                  slotProps={{ textField: { fullWidth: true } }}
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <TextField
                  label="製品コード"
                  value={filters.instructionId}
                  onChange={(e) =>
                    handleFilterChange("instructionId", e.target.value)
                  }
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={exportResults}
                  fullWidth
                >
                  エクスポート
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* メインコンテンツ */}
        <Card>
          <CardContent>
            <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 2 }}>
              <Tab label="検査実行履歴" />
              <Tab label="検査結果一覧" />
            </Tabs>

            {loading && <LinearProgress sx={{ mb: 2 }} />}

            {/* 検査実行履歴タブ */}
            {activeTab === 0 && (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>実行ID</TableCell>
                      <TableCell>検査指示</TableCell>
                      <TableCell>型式コード</TableCell>
                      <TableCell>型式名</TableCell>
                      <TableCell>機番</TableCell>
                      <TableCell>生産日</TableCell>
                      <TableCell>月連番</TableCell>
                      <TableCell>ステータス</TableCell>
                      <TableCell>検査開始時刻</TableCell>
                      <TableCell>検査完了時刻</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {executions.map((execution) => (
                      <TableRow key={execution.id} hover>
                        <TableCell>{execution.id.slice(0, 8)}...</TableCell>
                        <TableCell>
                          {execution.instruction?.name || "-"}
                        </TableCell>
                        <TableCell>
                          {execution.metadata?.product_code ||
                            execution.instruction?.product_code ||
                            "-"}
                        </TableCell>
                        <TableCell>
                          {(() => {
                            const code =
                              execution.metadata?.product_code ||
                              (execution as any)?.instruction?.product_code;
                            const nameFromCode = code
                              ? codeToProductName[code]
                              : undefined;
                            return (
                              nameFromCode ||
                              execution.instruction?.product_name ||
                              execution.metadata?.product_name ||
                              "-"
                            );
                          })()}
                        </TableCell>
                        <TableCell>
                          {execution.metadata?.machine_number || "-"}
                        </TableCell>
                        <TableCell>
                          {execution.metadata?.production_date || "-"}
                        </TableCell>
                        <TableCell>
                          {execution.metadata?.monthly_sequence || "-"}
                        </TableCell>
                        <TableCell>
                          <StatusChip status={execution.status} />
                        </TableCell>
                        <TableCell>
                          {formatLocalDateTime(
                            execution.metadata?.client_started_at_ms ||
                              execution.metadata?.client_started_at ||
                              execution.started_at
                          )}
                        </TableCell>
                        <TableCell>
                          {formatLocalDateTime(
                            execution.metadata?.client_completed_at_ms ||
                              execution.metadata?.client_completed_at ||
                              execution.completed_at
                          )}
                        </TableCell>
                        <TableCell>
                          <IconButton
                            size="small"
                            onClick={() => loadExecutionDetails(execution)}
                          >
                            <ViewIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {/* 検査結果一覧タブ */}
            {activeTab === 1 && (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>結果ID</TableCell>
                      <TableCell>実行ID</TableCell>
                      <TableCell>判定結果</TableCell>
                      <TableCell>信頼度</TableCell>
                      <TableCell>処理時間</TableCell>
                      <TableCell>結果画像</TableCell>
                      <TableCell>作成日時</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {results.map((result) => (
                      <TableRow key={result.id} hover>
                        <TableCell>{result.id.slice(0, 8)}...</TableCell>
                        <TableCell>
                          {result.execution_id.slice(0, 8)}...
                        </TableCell>
                        <TableCell>
                          <JudgmentChip judgment={result.judgment} />
                        </TableCell>
                        <TableCell>
                          {result.confidence_score
                            ? `${(result.confidence_score * 100).toFixed(1)}%`
                            : "-"}
                        </TableCell>
                        <TableCell>
                          {result.processing_time_ms
                            ? `${result.processing_time_ms}ms`
                            : "-"}
                        </TableCell>
                        <TableCell>
                          {result.evidence_file_ids &&
                          result.evidence_file_ids.length > 0 ? (
                            <Button
                              size="small"
                              onClick={() =>
                                openEvidence(result.evidence_file_ids![0])
                              }
                            >
                              表示
                            </Button>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                        <TableCell>
                          {formatLocalDateTime(result.created_at)}
                        </TableCell>
                        <TableCell>
                          <IconButton size="small">
                            <ViewIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {/* ページネーション */}
            <Box display="flex" justifyContent="center" mt={3}>
              <Pagination
                count={totalPages}
                page={page}
                onChange={(event, value) => setPage(value)}
                color="primary"
              />
            </Box>
          </CardContent>
        </Card>

        {/* 検査詳細ダイアログ */}
        <Dialog
          open={detailDialog}
          onClose={() => setDetailDialog(false)}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>
            検査詳細 - {selectedExecution?.instruction?.name}
          </DialogTitle>
          <DialogContent>
            {selectedExecution && (
              <Grid container spacing={3}>
                {/* 基本情報 */}
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        基本情報
                      </Typography>
                      <Typography>
                        <strong>実行ID:</strong> {selectedExecution.id}
                      </Typography>
                      <Typography>
                        <strong>検査指示:</strong>{" "}
                        {selectedExecution.instruction?.name}
                      </Typography>
                      <Typography>
                        <strong>型式コード:</strong>{" "}
                        {selectedExecution.metadata?.product_code ||
                          selectedExecution.instruction?.product_code ||
                          selectedExecution.instruction?.group_name ||
                          "-"}
                      </Typography>
                      <Typography>
                        <strong>型式名:</strong>{" "}
                        {(() => {
                          const code =
                            selectedExecution.metadata?.product_code ||
                            (selectedExecution as any)?.instruction
                              ?.product_code;
                          const nameFromCode = code
                            ? codeToProductName[code]
                            : undefined;
                          return (
                            nameFromCode ||
                            selectedExecution.instruction?.product_name ||
                            selectedExecution.metadata?.product_name ||
                            "-"
                          );
                        })()}
                      </Typography>
                      <Typography>
                        <strong>機番:</strong>{" "}
                        {selectedExecution.metadata?.machine_number || "-"}
                      </Typography>
                      <Typography>
                        <strong>生産日:</strong>{" "}
                        {selectedExecution.metadata?.production_date || "-"}
                      </Typography>
                      <Typography>
                        <strong>月連番:</strong>{" "}
                        {selectedExecution.metadata?.monthly_sequence || "-"}
                      </Typography>
                      <Typography>
                        <strong>ステータス:</strong>{" "}
                        <StatusChip status={selectedExecution.status} />
                      </Typography>
                      <Typography>
                        <strong>検査開始時刻:</strong>{" "}
                        {formatLocalDateTime(
                          selectedExecution.metadata?.client_started_at_ms ||
                            selectedExecution.metadata?.client_started_at ||
                            selectedExecution.started_at
                        )}
                      </Typography>
                      {selectedExecution.completed_at && (
                        <Typography>
                          <strong>検査完了時刻:</strong>{" "}
                          {formatLocalDateTime(
                            selectedExecution.metadata
                              ?.client_completed_at_ms ||
                              selectedExecution.metadata?.client_completed_at ||
                              selectedExecution.completed_at
                          )}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </Grid>

                {/* 統計情報 */}
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        統計情報
                      </Typography>
                      <Typography>
                        <strong>総項目数:</strong> {itemExecutions.length}
                      </Typography>
                      <Typography>
                        <strong>完了項目:</strong>{" "}
                        {
                          itemExecutions.filter(
                            (i) => i.status === "ITEM_COMPLETED"
                          ).length
                        }
                      </Typography>
                      <Typography>
                        <strong>OK判定:</strong>{" "}
                        {
                          itemExecutions.filter((i) => i.final_result === "OK")
                            .length
                        }
                      </Typography>
                      <Typography>
                        <strong>NG判定:</strong>{" "}
                        {
                          itemExecutions.filter((i) => i.final_result === "NG")
                            .length
                        }
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                {/* 検査項目詳細 */}
                <Grid item xs={12}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        検査項目詳細
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>順序</TableCell>
                              <TableCell>項目名</TableCell>
                              <TableCell>タイプ</TableCell>
                              <TableCell>ステータス</TableCell>
                              <TableCell>AI判定</TableCell>
                              <TableCell>最終判定</TableCell>
                              <TableCell>結果画像</TableCell>
                              <TableCell>処理時間</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {itemExecutions.map((itemExecution) => (
                              <TableRow key={itemExecution.id}>
                                <TableCell>
                                  {itemExecution.item?.execution_order}
                                </TableCell>
                                <TableCell>
                                  {itemExecution.item?.name}
                                </TableCell>
                                <TableCell>
                                  {itemExecution.item?.type}
                                </TableCell>
                                <TableCell>
                                  <StatusChip status={itemExecution.status} />
                                </TableCell>
                                <TableCell>
                                  {itemExecution.ai_result?.judgment ? (
                                    <JudgmentChip
                                      judgment={
                                        itemExecution.ai_result.judgment
                                      }
                                    />
                                  ) : (
                                    "-"
                                  )}
                                </TableCell>
                                <TableCell>
                                  {itemExecution.final_result ? (
                                    <JudgmentChip
                                      judgment={itemExecution.final_result}
                                    />
                                  ) : (
                                    "-"
                                  )}
                                </TableCell>
                                <TableCell>
                                  {execResultsByItem[itemExecution.id] &&
                                  execResultsByItem[itemExecution.id].length >
                                    0 ? (
                                    thumbUrlsByItem[itemExecution.id] ? (
                                      <img
                                        src={thumbUrlsByItem[itemExecution.id]}
                                        alt="結果画像"
                                        style={{
                                          maxWidth: 96,
                                          maxHeight: 64,
                                          objectFit: "cover",
                                          borderRadius: 4,
                                          cursor: "pointer",
                                        }}
                                        onClick={() =>
                                          openEvidence(
                                            execResultsByItem[
                                              itemExecution.id
                                            ][0]
                                          )
                                        }
                                      />
                                    ) : (
                                      <Button
                                        size="small"
                                        onClick={() =>
                                          openEvidence(
                                            execResultsByItem[
                                              itemExecution.id
                                            ][0]
                                          )
                                        }
                                      >
                                        表示
                                      </Button>
                                    )
                                  ) : (
                                    "-"
                                  )}
                                </TableCell>
                                <TableCell>
                                  {itemExecution.ai_result?.processing_time_ms
                                    ? `${itemExecution.ai_result.processing_time_ms}ms`
                                    : "-"}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDetailDialog(false)}>閉じる</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
}
