import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  IconButton,
} from "@mui/material";
import {
  Add,
  PlayArrow,
  Timeline,
  Upload,
  Storage,
  Settings,
  Visibility,
  Edit,
} from "@mui/icons-material";
import { useQuery, useMutation, useQueryClient } from "react-query";
import { useAuth } from "../services/AuthContext";
import { apiService } from "../services/api";
import { Pipeline } from "../types";

export const Dashboard: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(
    null
  );
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pipelineToDelete, setPipelineToDelete] = useState<Pipeline | null>(
    null
  );
  const [pipelineDetailDialogOpen, setPipelineDetailDialogOpen] =
    useState(false);
  const [pipelineToView, setPipelineToView] = useState<Pipeline | null>(null);
  const [pipelineExecutions, setPipelineExecutions] = useState<any[]>([]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const { data: pipelines = [] } = useQuery("pipelines", () =>
    apiService.getPipelines()
  );
  const { data: executions = [] } = useQuery("executions", () =>
    apiService.getExecutions(10)
  );
  const { data: grpcServicesHealth = [] } = useQuery(
    "grpc-services-health",
    () => apiService.getGrpcServicesHealth(),
    {
      refetchInterval: 30000, // 30秒ごとに自動更新
      retry: 3,
    }
  );

  const executePipelineMutation = useMutation(
    ({ pipelineId, files }: { pipelineId: string; files: File[] }) =>
      apiService.executePipeline(pipelineId, files),
    {
      onSuccess: (result) => {
        queryClient.invalidateQueries("executions");
        setExecuteDialogOpen(false);
        const executedPipelineId = selectedPipeline?.id;
        setSelectedPipeline(null);
        setSelectedFiles([]);
        // 実行監視画面に遷移して結果を確認
        // 戻る先に実行したパイプラインでフィルターされた実行監視一覧を設定
        const returnToUrl = executedPipelineId
          ? `/executions?pipeline=${executedPipelineId}`
          : "/executions";
        navigate(
          `/execution/${result.execution_id}?returnTo=${encodeURIComponent(
            returnToUrl
          )}`
        );
      },
      onError: (error) => {
        console.error("Pipeline execution failed:", error);
      },
    }
  );

  const deletePipelineMutation = useMutation(
    (pipelineId: string) => apiService.deletePipeline(pipelineId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("pipelines");
        setDeleteDialogOpen(false);
        setPipelineToDelete(null);
      },
      onError: (error) => {
        console.error("Pipeline deletion failed:", error);
      },
    }
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "success";
      case "running":
        return "primary";
      case "failed":
        return "error";
      case "cancelled":
        return "default";
      default:
        return "warning";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "pending":
        return "待機中";
      case "running":
        return "実行中";
      case "completed":
        return "完了";
      case "failed":
        return "失敗";
      case "cancelled":
        return "キャンセル";
      default:
        return status;
    }
  };

  const handleExecutePipeline = (pipeline: Pipeline) => {
    setSelectedPipeline(pipeline);
    setExecuteDialogOpen(true);
  };

  const handleDeletePipeline = (pipeline: Pipeline) => {
    setPipelineToDelete(pipeline);
    setDeleteDialogOpen(true);
  };

  const handleViewPipelineDetail = async (pipeline: Pipeline) => {
    setPipelineToView(pipeline);
    setPipelineDetailDialogOpen(true);

    // Fetch execution history for this pipeline
    try {
      const executions = await apiService.getExecutions(10, 0, pipeline.id);
      setPipelineExecutions(executions);
    } catch (error) {
      console.error("Failed to fetch pipeline executions:", error);
      setPipelineExecutions([]);
    }
  };

  const handleDeleteConfirm = () => {
    if (pipelineToDelete) {
      deletePipelineMutation.mutate(pipelineToDelete.id);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      setSelectedFiles(Array.from(files));
    }
  };

  const handleExecuteSubmit = () => {
    if (selectedPipeline && selectedFiles.length > 0) {
      executePipelineMutation.mutate({
        pipelineId: selectedPipeline.id,
        files: selectedFiles,
      });
    }
  };

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
              <Typography variant="h4">{pipelines.length}</Typography>
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
                {executions.filter((e: any) => e.status === "running").length}
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
                {executions.filter((e: any) => e.status === "completed").length}
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
                {executions.filter((e: any) => e.status === "failed").length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                gRPCサービス
              </Typography>
              <Typography variant="h4">
                {
                  grpcServicesHealth.filter((s: any) => s.status === "healthy")
                    .length
                }
                /{grpcServicesHealth.length}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                稼働中
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* アクションボタン */}
        <Grid item xs={12}>
          <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => navigate("/pipeline-builder")}
            >
              新しいパイプライン
            </Button>
            <Button
              variant="outlined"
              startIcon={<Timeline />}
              onClick={() => navigate("/executions")}
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
                  <Box
                    key={pipeline.id}
                    sx={{
                      mb: 2,
                      p: 2,
                      border: "1px solid #e0e0e0",
                      borderRadius: 1,
                    }}
                  >
                    <Typography variant="subtitle1">{pipeline.name}</Typography>
                    <Typography
                      variant="body2"
                      color="textSecondary"
                      sx={{ mb: 1 }}
                    >
                      {pipeline.description}
                    </Typography>

                    {/* コンポーネント一覧を表示 */}
                    <Box sx={{ mb: 1 }}>
                      <Typography variant="caption" color="textSecondary">
                        コンポーネント ({pipeline.components.length}個):
                      </Typography>
                      <Box
                        sx={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: 0.5,
                          mt: 0.5,
                        }}
                      >
                        {pipeline.components.map((component, index) => (
                          <Chip
                            key={component.id}
                            label={`${index + 1}. ${component.name}`}
                            size="small"
                            variant="outlined"
                            color="primary"
                          />
                        ))}
                      </Box>
                    </Box>

                    <Box sx={{ mt: 1, display: "flex", gap: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PlayArrow />}
                        onClick={() => handleExecutePipeline(pipeline)}
                      >
                        実行
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<Visibility />}
                        onClick={() => handleViewPipelineDetail(pipeline)}
                      >
                        詳細
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() => handleDeletePipeline(pipeline)}
                      >
                        削除
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
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 2,
                }}
              >
                <Typography variant="h6">最近の実行履歴</Typography>
                <Button
                  size="small"
                  variant="text"
                  onClick={() => navigate("/executions")}
                >
                  すべて表示
                </Button>
              </Box>
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  💡
                  実行IDまたは「詳細」ボタンをクリックして処理結果の画像を確認できます
                </Typography>
              </Alert>
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
                        <TableCell>アクション</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {executions.slice(0, 5).map((execution) => (
                        <TableRow
                          key={execution.execution_id}
                          sx={{
                            "&:hover": { backgroundColor: "#f5f5f5" },
                            cursor: "pointer",
                          }}
                          onClick={() => {
                            const returnToUrl = execution.pipeline_id
                              ? `/executions?pipeline=${execution.pipeline_id}`
                              : "/executions";
                            navigate(
                              `/execution/${
                                execution.execution_id
                              }?returnTo=${encodeURIComponent(returnToUrl)}`
                            );
                          }}
                        >
                          <TableCell>
                            <Typography
                              variant="body2"
                              color="primary"
                              sx={{ textDecoration: "underline" }}
                            >
                              {execution.execution_id.substring(0, 8)}...
                            </Typography>
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
                            {(() => {
                              // UTC時間として明示的に扱って、ローカルタイムゾーンに変換
                              const utcDate = new Date(
                                execution.created_at +
                                  (execution.created_at.includes("Z")
                                    ? ""
                                    : "Z")
                              );
                              return utcDate.toLocaleString(undefined, {
                                year: "numeric",
                                month: "2-digit",
                                day: "2-digit",
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit",
                                timeZoneName: "short",
                              });
                            })()}
                          </TableCell>
                          <TableCell onClick={(e) => e.stopPropagation()}>
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<Timeline />}
                              onClick={() => {
                                const returnToUrl = execution.pipeline_id
                                  ? `/executions?pipeline=${execution.pipeline_id}`
                                  : "/executions";
                                navigate(
                                  `/execution/${
                                    execution.execution_id
                                  }?returnTo=${encodeURIComponent(returnToUrl)}`
                                );
                              }}
                            >
                              詳細
                            </Button>
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

      {/* パイプライン実行ダイアログ */}
      <Dialog
        open={executeDialogOpen}
        onClose={() => setExecuteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>パイプライン実行: {selectedPipeline?.name}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>
              処理対象のファイルを選択してください
            </Typography>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={handleFileSelect}
              style={{ display: "none" }}
              id="file-input"
            />
            <label htmlFor="file-input">
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

            {selectedFiles.length > 0 && (
              <Box>
                <Typography variant="body2" gutterBottom>
                  選択されたファイル ({selectedFiles.length}件):
                </Typography>
                {selectedFiles.map((file, index) => (
                  <Typography key={index} variant="body2" color="textSecondary">
                    • {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </Typography>
                ))}
              </Box>
            )}

            {executePipelineMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                実行に失敗しました:{" "}
                {executePipelineMutation.error instanceof Error
                  ? executePipelineMutation.error.message
                  : "不明なエラー"}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExecuteDialogOpen(false)}>
            キャンセル
          </Button>
          <Button
            onClick={handleExecuteSubmit}
            variant="contained"
            disabled={
              selectedFiles.length === 0 || executePipelineMutation.isLoading
            }
            startIcon={
              executePipelineMutation.isLoading ? (
                <CircularProgress size={20} />
              ) : (
                <PlayArrow />
              )
            }
          >
            実行開始
          </Button>
        </DialogActions>
      </Dialog>

      {/* パイプライン削除確認ダイアログ */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>パイプライン削除の確認</DialogTitle>
        <DialogContent>
          <Typography>
            パイプライン「{pipelineToDelete?.name}」を削除しますか？
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            この操作は取り消せません。
          </Typography>
          {deletePipelineMutation.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              削除に失敗しました:{" "}
              {deletePipelineMutation.error instanceof Error
                ? deletePipelineMutation.error.message
                : "不明なエラー"}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            disabled={deletePipelineMutation.isLoading}
          >
            キャンセル
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            variant="contained"
            color="error"
            disabled={deletePipelineMutation.isLoading}
            startIcon={
              deletePipelineMutation.isLoading ? (
                <CircularProgress size={20} />
              ) : undefined
            }
          >
            削除
          </Button>
        </DialogActions>
      </Dialog>

      {/* パイプライン詳細ダイアログ */}
      <Dialog
        open={pipelineDetailDialogOpen}
        onClose={() => {
          setPipelineDetailDialogOpen(false);
          setPipelineExecutions([]);
        }}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>パイプライン詳細: {pipelineToView?.name}</DialogTitle>
        <DialogContent>
          {pipelineToView && (
            <Box>
              <Typography variant="body1" gutterBottom>
                <strong>説明:</strong>{" "}
                {pipelineToView.description || "説明なし"}
              </Typography>

              <Typography variant="body1" gutterBottom sx={{ mt: 2 }}>
                <strong>作成日時:</strong>{" "}
                {(() => {
                  // UTC時間として明示的に扱って、ローカルタイムゾーンに変換
                  const utcDate = new Date(
                    pipelineToView.created_at +
                      (pipelineToView.created_at.includes("Z") ? "" : "Z")
                  );
                  return utcDate.toLocaleString(undefined, {
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    timeZoneName: "short",
                  });
                })()}
              </Typography>

              <Typography variant="body1" gutterBottom>
                <strong>更新日時:</strong>{" "}
                {(() => {
                  // UTC時間として明示的に扱って、ローカルタイムゾーンに変換
                  const utcDate = new Date(
                    pipelineToView.updated_at +
                      (pipelineToView.updated_at.includes("Z") ? "" : "Z")
                  );
                  return utcDate.toLocaleString(undefined, {
                    year: "numeric",
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    timeZoneName: "short",
                  });
                })()}
              </Typography>

              <Typography variant="h6" sx={{ mt: 3, mb: 2 }}>
                処理コンポーネント ({pipelineToView.components.length}個)
              </Typography>

              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>順序</TableCell>
                      <TableCell>コンポーネント名</TableCell>
                      <TableCell>タイプ</TableCell>
                      <TableCell>パラメータ</TableCell>
                      <TableCell>依存関係</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pipelineToView.components.map((component, index) => (
                      <TableRow key={component.id}>
                        <TableCell>
                          <Chip
                            label={index + 1}
                            color="primary"
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{component.name}</TableCell>
                        <TableCell>
                          <Chip
                            label={component.component_type}
                            variant="outlined"
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {Object.keys(component.parameters).length > 0 ? (
                            <Box>
                              {Object.entries(component.parameters).map(
                                ([key, value]) => (
                                  <Typography
                                    key={key}
                                    variant="caption"
                                    display="block"
                                  >
                                    {key}: {String(value)}
                                  </Typography>
                                )
                              )}
                            </Box>
                          ) : (
                            <Typography variant="caption" color="textSecondary">
                              パラメータなし
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {component.dependencies.length > 0 ? (
                            <Box>
                              {component.dependencies.map((dep, depIndex) => (
                                <Chip
                                  key={depIndex}
                                  label={dep}
                                  size="small"
                                  variant="outlined"
                                  sx={{ mr: 0.5, mb: 0.5 }}
                                />
                              ))}
                            </Box>
                          ) : (
                            <Typography variant="caption" color="textSecondary">
                              なし
                            </Typography>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* パイプライン設定情報 */}
              <Typography variant="h6" sx={{ mt: 3, mb: 2 }}>
                パイプライン情報
              </Typography>

              <Box sx={{ bgcolor: "#f5f5f5", p: 2, borderRadius: 1 }}>
                <Typography variant="body2" gutterBottom>
                  <strong>パイプラインID:</strong> {pipelineToView.id}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  <strong>総コンポーネント数:</strong>{" "}
                  {pipelineToView.components.length}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  <strong>依存関係の数:</strong>{" "}
                  {pipelineToView.components.reduce(
                    (total, comp) => total + comp.dependencies.length,
                    0
                  )}
                </Typography>
              </Box>

              {/* 実行履歴セクション */}
              <Typography variant="h6" sx={{ mt: 3, mb: 2 }}>
                実行履歴 (最新10件)
              </Typography>

              {pipelineExecutions.length === 0 ? (
                <Typography color="textSecondary">
                  このパイプラインの実行履歴はありません
                </Typography>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>実行ID</TableCell>
                        <TableCell>ステータス</TableCell>
                        <TableCell>進捗</TableCell>
                        <TableCell>実行日時</TableCell>
                        <TableCell>アクション</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {pipelineExecutions.map((execution) => (
                        <TableRow key={execution.execution_id}>
                          <TableCell>
                            <Typography
                              variant="body2"
                              color="primary"
                              sx={{
                                textDecoration: "underline",
                                cursor: "pointer",
                              }}
                              onClick={() => {
                                const returnToUrl = execution.pipeline_id
                                  ? `/executions?pipeline=${execution.pipeline_id}`
                                  : "/executions";
                                navigate(
                                  `/execution/${
                                    execution.execution_id
                                  }?returnTo=${encodeURIComponent(returnToUrl)}`
                                );
                              }}
                            >
                              {execution.execution_id.substring(0, 8)}...
                            </Typography>
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
                            {(() => {
                              // UTC時間として明示的に扱って、ローカルタイムゾーンに変換
                              const utcDate = new Date(
                                execution.created_at +
                                  (execution.created_at.includes("Z")
                                    ? ""
                                    : "Z")
                              );
                              return utcDate.toLocaleString(undefined, {
                                year: "numeric",
                                month: "2-digit",
                                day: "2-digit",
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit",
                                timeZoneName: "short",
                              });
                            })()}
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<Timeline />}
                              onClick={() => {
                                const returnToUrl = execution.pipeline_id
                                  ? `/executions?pipeline=${execution.pipeline_id}`
                                  : "/executions";
                                navigate(
                                  `/execution/${
                                    execution.execution_id
                                  }?returnTo=${encodeURIComponent(returnToUrl)}`
                                );
                              }}
                            >
                              詳細
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setPipelineDetailDialogOpen(false);
              setPipelineExecutions([]);
            }}
          >
            閉じる
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
