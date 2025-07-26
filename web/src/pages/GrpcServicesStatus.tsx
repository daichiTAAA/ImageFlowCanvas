import React, { useState } from "react";
import { Navigate } from "react-router-dom";
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
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  LinearProgress,
  Tooltip,
} from "@mui/material";
import {
  Refresh,
  RestartAlt,
  CheckCircle,
  Error,
  Warning,
  Schedule,
  Memory,
  Speed,
  Cloud,
} from "@mui/icons-material";
import { useQuery, useMutation, useQueryClient } from "react-query";
import { useAuth } from "../services/AuthContext";
import { apiService } from "../services/api";

interface GrpcServiceHealth {
  service_name: string;
  display_name: string;
  endpoint: string;
  status: "healthy" | "unhealthy" | "timeout" | "error";
  response_time_ms?: number;
  error?: string;
  last_checked: string;
  pod_info?: {
    name: string;
    status: string;
    restart_count: number;
    created_time: string;
    node_name: string;
  };
  uptime?: string;
  request_count?: {
    total_requests: number;
    requests_per_minute: number;
    success_rate: number;
  };
  cpu_usage?: string;
  memory_usage?: string;
}

export const GrpcServicesStatus: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [restartDialogOpen, setRestartDialogOpen] = useState(false);
  const [serviceToRestart, setServiceToRestart] = useState<string | null>(null);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const {
    data: servicesHealth = [],
    isLoading: healthLoading,
    error: healthError,
  } = useQuery(
    "grpc-services-health",
    () => apiService.getGrpcServicesHealth(),
    {
      refetchInterval: 30000, // 30秒ごとに自動更新
      retry: 3,
    }
  );

  const { data: servicesInfo = [], isLoading: infoLoading } = useQuery(
    "grpc-services-info",
    () => apiService.getGrpcServicesInfo(),
    {
      refetchInterval: 60000, // 1分ごとに自動更新
      retry: 3,
    }
  );

  const restartServiceMutation = useMutation(
    (serviceName: string) => apiService.restartGrpcService(serviceName),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("grpc-services-health");
        queryClient.invalidateQueries("grpc-services-info");
        setRestartDialogOpen(false);
        setServiceToRestart(null);
      },
      onError: (error) => {
        console.error("Service restart failed:", error);
      },
    }
  );

  const handleRefresh = () => {
    queryClient.invalidateQueries("grpc-services-health");
    queryClient.invalidateQueries("grpc-services-info");
  };

  const handleRestartService = (serviceName: string) => {
    setServiceToRestart(serviceName);
    setRestartDialogOpen(true);
  };

  const handleRestartConfirm = () => {
    if (serviceToRestart) {
      restartServiceMutation.mutate(serviceToRestart);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "success";
      case "unhealthy":
        return "error";
      case "timeout":
        return "warning";
      case "error":
        return "error";
      default:
        return "default";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
        return <CheckCircle color="success" />;
      case "unhealthy":
        return <Error color="error" />;
      case "timeout":
        return <Schedule color="warning" />;
      case "error":
        return <Warning color="error" />;
      default:
        return <Warning color="action" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "healthy":
        return "稼働中";
      case "unhealthy":
        return "異常";
      case "timeout":
        return "タイムアウト";
      case "error":
        return "エラー";
      default:
        return "不明";
    }
  };

  // サービスの健康状態から統計情報を計算
  const healthyCount = servicesHealth.filter(
    (s) => s.status === "healthy"
  ).length;
  const totalCount = servicesHealth.length;
  const averageResponseTime =
    servicesHealth
      .filter((s) => s.response_time_ms)
      .reduce((sum, s) => sum + (s.response_time_ms || 0), 0) /
      servicesHealth.filter((s) => s.response_time_ms).length || 0;

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
        <Typography variant="h4" gutterBottom>
          常駐gRPCサービス監視
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={handleRefresh}
          disabled={healthLoading || infoLoading}
        >
          更新
        </Button>
      </Box>

      {healthError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          サービス情報の取得に失敗しました: {String(healthError)}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* 統計カード */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Cloud color="primary" />
                <Typography color="textSecondary" gutterBottom>
                  稼働中サービス
                </Typography>
              </Box>
              <Typography variant="h4">
                {healthyCount}/{totalCount}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={totalCount > 0 ? (healthyCount / totalCount) * 100 : 0}
                color={healthyCount === totalCount ? "success" : "warning"}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Speed color="primary" />
                <Typography color="textSecondary" gutterBottom>
                  平均応答時間
                </Typography>
              </Box>
              <Typography variant="h4">
                {averageResponseTime
                  ? `${averageResponseTime.toFixed(1)}ms`
                  : "N/A"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Memory color="primary" />
                <Typography color="textSecondary" gutterBottom>
                  総リクエスト数
                </Typography>
              </Box>
              <Typography variant="h4">
                {servicesInfo.reduce(
                  (sum, s) => sum + (s.request_count?.total_requests || 0),
                  0
                )}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <CheckCircle color="primary" />
                <Typography color="textSecondary" gutterBottom>
                  成功率
                </Typography>
              </Box>
              <Typography variant="h4">
                {servicesInfo.length > 0
                  ? (
                      servicesInfo.reduce(
                        (sum, s) => sum + (s.request_count?.success_rate || 0),
                        0
                      ) / servicesInfo.length
                    ).toFixed(1)
                  : "0"}
                %
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* サービス一覧テーブル */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                サービス一覧
              </Typography>
              {healthLoading || infoLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
                  <CircularProgress />
                </Box>
              ) : servicesHealth.length === 0 ? (
                <Typography color="textSecondary">
                  監視対象のサービスがありません
                </Typography>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>サービス名</TableCell>
                        <TableCell>ステータス</TableCell>
                        <TableCell>応答時間</TableCell>
                        <TableCell>エンドポイント</TableCell>
                        <TableCell>Pod情報</TableCell>
                        <TableCell>CPU/Memory</TableCell>
                        <TableCell>リクエスト数</TableCell>
                        <TableCell>最終確認</TableCell>
                        <TableCell>アクション</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {servicesHealth.map((service) => {
                        const serviceInfo = servicesInfo.find(
                          (s) => s.service_name === service.service_name
                        );

                        return (
                          <TableRow key={service.service_name}>
                            <TableCell>
                              <Box
                                sx={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 1,
                                }}
                              >
                                {getStatusIcon(service.status)}
                                <Box>
                                  <Typography variant="body2" fontWeight="bold">
                                    {service.display_name}
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color="textSecondary"
                                  >
                                    {service.service_name}
                                  </Typography>
                                </Box>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={getStatusText(service.status)}
                                color={getStatusColor(service.status) as any}
                                size="small"
                              />
                              {service.error && (
                                <Tooltip title={service.error}>
                                  <Typography
                                    variant="caption"
                                    color="error"
                                    sx={{ display: "block", mt: 0.5 }}
                                  >
                                    {service.error.substring(0, 30)}...
                                  </Typography>
                                </Tooltip>
                              )}
                            </TableCell>
                            <TableCell>
                              {service.response_time_ms ? (
                                <Typography
                                  variant="body2"
                                  color={
                                    service.response_time_ms > 1000
                                      ? "warning.main"
                                      : "text.primary"
                                  }
                                >
                                  {service.response_time_ms.toFixed(1)}ms
                                </Typography>
                              ) : (
                                "N/A"
                              )}
                            </TableCell>
                            <TableCell>
                              <Typography
                                variant="body2"
                                fontFamily="monospace"
                              >
                                {service.endpoint}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              {service.pod_info ? (
                                <Box>
                                  <Typography variant="caption" display="block">
                                    {service.pod_info.name}
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color="textSecondary"
                                    display="block"
                                  >
                                    再起動: {service.pod_info.restart_count}回
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color="textSecondary"
                                    display="block"
                                  >
                                    ノード: {service.pod_info.node_name}
                                  </Typography>
                                </Box>
                              ) : (
                                "N/A"
                              )}
                            </TableCell>
                            <TableCell>
                              {serviceInfo ? (
                                <Box>
                                  <Typography variant="caption" display="block">
                                    CPU: {serviceInfo.cpu_usage || "N/A"}
                                  </Typography>
                                  <Typography variant="caption" display="block">
                                    MEM: {serviceInfo.memory_usage || "N/A"}
                                  </Typography>
                                </Box>
                              ) : (
                                "N/A"
                              )}
                            </TableCell>
                            <TableCell>
                              {serviceInfo?.request_count ? (
                                <Box>
                                  <Typography variant="caption" display="block">
                                    総数:{" "}
                                    {serviceInfo.request_count.total_requests.toLocaleString()}
                                  </Typography>
                                  <Typography variant="caption" display="block">
                                    /分:{" "}
                                    {serviceInfo.request_count.requests_per_minute.toFixed(
                                      1
                                    )}
                                  </Typography>
                                  <Typography variant="caption" display="block">
                                    成功率:{" "}
                                    {serviceInfo.request_count.success_rate.toFixed(
                                      1
                                    )}
                                    %
                                  </Typography>
                                </Box>
                              ) : (
                                "N/A"
                              )}
                            </TableCell>
                            <TableCell>
                              <Typography variant="caption">
                                {new Date(
                                  service.last_checked
                                ).toLocaleString()}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <IconButton
                                size="small"
                                color="warning"
                                onClick={() =>
                                  handleRestartService(service.service_name)
                                }
                                disabled={restartServiceMutation.isLoading}
                              >
                                <RestartAlt />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* サービス再起動確認ダイアログ */}
      <Dialog
        open={restartDialogOpen}
        onClose={() => setRestartDialogOpen(false)}
      >
        <DialogTitle>サービス再起動の確認</DialogTitle>
        <DialogContent>
          <Typography>
            サービス「{serviceToRestart}」を再起動しますか？
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            再起動中は一時的にサービスが利用できなくなります。
          </Typography>
          {restartServiceMutation.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              再起動に失敗しました:{" "}
              {restartServiceMutation.error instanceof Error
                ? restartServiceMutation.error.message
                : "不明なエラー"}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setRestartDialogOpen(false)}
            disabled={restartServiceMutation.isLoading}
          >
            キャンセル
          </Button>
          <Button
            onClick={handleRestartConfirm}
            variant="contained"
            color="warning"
            disabled={restartServiceMutation.isLoading}
            startIcon={
              restartServiceMutation.isLoading ? (
                <CircularProgress size={20} />
              ) : (
                <RestartAlt />
              )
            }
          >
            再起動
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
