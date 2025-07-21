import React, { useState, useEffect } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
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
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from "@mui/material";
import { Refresh, Visibility } from "@mui/icons-material";
import { useQuery } from "react-query";
import { useAuth } from "../services/AuthContext";
import { apiService } from "../services/api";
import { Execution, Pipeline } from "../types";

export const ExecutionList: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedPipelineId, setSelectedPipelineId] = useState<string>("");

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // URLパラメータからフィルターを初期化
  useEffect(() => {
    const pipelineId = searchParams.get("pipeline");
    if (pipelineId) {
      setSelectedPipelineId(pipelineId);
    }
  }, [searchParams]);

  // パイプライン一覧を取得
  const {
    data: pipelines = [],
    isLoading: pipelinesLoading,
    error: pipelinesError,
  } = useQuery<Pipeline[]>("pipelines", () => apiService.getPipelines(), {
    staleTime: 5 * 60 * 1000, // 5分間キャッシュ
  });

  // デバッグ用ログ
  console.log("🔍 パイプライン一覧デバッグ:", {
    pipelines,
    pipelinesLoading,
    pipelinesError,
    count: pipelines?.length || 0,
  });

  // 実行履歴を取得（パイプラインIDでフィルター）
  const { data: executions = [], refetch } = useQuery<Execution[]>(
    ["executions", selectedPipelineId],
    () => apiService.getExecutions(50, 0, selectedPipelineId || undefined),
    {
      refetchInterval: 5000, // 5秒ごとに更新
    }
  );

  const handlePipelineFilterChange = (event: SelectChangeEvent) => {
    const newPipelineId = event.target.value;
    setSelectedPipelineId(newPipelineId);

    // URLパラメータを更新
    const newSearchParams = new URLSearchParams(searchParams);
    if (newPipelineId) {
      newSearchParams.set("pipeline", newPipelineId);
    } else {
      newSearchParams.delete("pipeline");
    }
    setSearchParams(newSearchParams);
  };

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

  // パイプラインIDから名前を取得するヘルパー関数
  const getPipelineName = (pipelineId: string) => {
    const pipeline = pipelines.find((p) => p.id === pipelineId);
    return pipeline ? pipeline.name : pipelineId;
  };

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4">実行監視</Typography>
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel id="pipeline-filter-label">
              パイプラインでフィルター
            </InputLabel>
            <Select
              labelId="pipeline-filter-label"
              value={selectedPipelineId}
              onChange={handlePipelineFilterChange}
              label="パイプラインでフィルター"
              disabled={pipelinesLoading}
            >
              <MenuItem value="">
                <em>すべてのパイプライン</em>
              </MenuItem>
              {pipelinesLoading ? (
                <MenuItem disabled>
                  <em>読み込み中...</em>
                </MenuItem>
              ) : pipelinesError ? (
                <MenuItem disabled>
                  <em>エラー: パイプライン一覧の取得に失敗</em>
                </MenuItem>
              ) : pipelines.length === 0 ? (
                <MenuItem disabled>
                  <em>パイプラインが見つかりません</em>
                </MenuItem>
              ) : (
                pipelines.map((pipeline) => (
                  <MenuItem key={pipeline.id} value={pipeline.id}>
                    {pipeline.name} ({pipeline.id})
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refetch()}
          >
            更新
          </Button>
        </Box>
      </Box>

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
            <Typography variant="h6">
              実行履歴
              {selectedPipelineId && (
                <Chip
                  label={`フィルター: ${
                    pipelines.find((p) => p.id === selectedPipelineId)?.name ||
                    selectedPipelineId
                  }`}
                  color="primary"
                  size="small"
                  sx={{ ml: 2 }}
                  onDelete={() => {
                    setSelectedPipelineId("");
                    const newSearchParams = new URLSearchParams(searchParams);
                    newSearchParams.delete("pipeline");
                    setSearchParams(newSearchParams);
                  }}
                />
              )}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {executions.length}件の実行
            </Typography>
          </Box>
          {executions.length === 0 ? (
            <Typography color="textSecondary">実行履歴がありません</Typography>
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
                    <TableCell>詳細</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {executions.map((execution) => (
                    <TableRow key={execution.execution_id}>
                      <TableCell>
                        {execution.execution_id.substring(0, 8)}...
                      </TableCell>
                      <TableCell>
                        {getPipelineName(execution.pipeline_id)}
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
                        {new Date(execution.created_at).toLocaleString(
                          "ja-JP",
                          {
                            timeZone: "Asia/Tokyo",
                            year: "numeric",
                            month: "2-digit",
                            day: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          }
                        )}
                      </TableCell>
                      <TableCell>
                        {execution.completed_at
                          ? new Date(execution.completed_at).toLocaleString(
                              "ja-JP",
                              {
                                timeZone: "Asia/Tokyo",
                                year: "numeric",
                                month: "2-digit",
                                day: "2-digit",
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit",
                              }
                            )
                          : "-"}
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => {
                            const executionDetailPath = `/execution/${execution.execution_id}`;
                            // 現在のフィルター状態をクエリパラメータとして保持
                            const returnParams = new URLSearchParams();
                            if (selectedPipelineId) {
                              returnParams.set("pipeline", selectedPipelineId);
                            }
                            const returnQuery = returnParams.toString();
                            const finalPath = returnQuery
                              ? `${executionDetailPath}?returnTo=${encodeURIComponent(
                                  `/executions?${returnQuery}`
                                )}`
                              : `${executionDetailPath}?returnTo=${encodeURIComponent(
                                  "/executions"
                                )}`;
                            navigate(finalPath);
                          }}
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
  );
};
