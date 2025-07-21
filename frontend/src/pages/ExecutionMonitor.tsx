import React, { useEffect, useState } from "react";
import { Navigate, useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Alert,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
} from "@mui/material";
import {
  Cancel,
  Download,
  Refresh,
  ArrowBack,
  Visibility,
} from "@mui/icons-material";
import { useQuery } from "react-query";
import { useAuth } from "../services/AuthContext";
import { apiService } from "../services/api";
import { Execution } from "../types";

export const ExecutionMonitor: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [, setWsConnection] = useState<WebSocket | null>(null);
  const [previewDialog, setPreviewDialog] = useState<{
    open: boolean;
    fileId: string;
    filename: string;
    imageUrl: string;
  }>({ open: false, fileId: "", filename: "", imageUrl: "" });
  const [jsonPreviewDialog, setJsonPreviewDialog] = useState<{
    open: boolean;
    fileId: string;
    filename: string;
    content: string;
  }>({ open: false, fileId: "", filename: "", content: "" });
  const [resultsTabValue, setResultsTabValue] = useState(0);
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({});
  const [loadingImages, setLoadingImages] = useState<Record<string, boolean>>(
    {}
  );

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!id) {
    return <Navigate to="/" replace />;
  }

  const { data: execution, refetch } = useQuery<Execution>(
    ["execution", id],
    () => apiService.getExecution(id),
    {
      refetchInterval: (data) =>
        data?.status === "running" || data?.status === "pending" ? 2000 : false,
    }
  );

  useEffect(() => {
    // WebSocket接続を設定
    const token = localStorage.getItem("access_token");
    if (token) {
      const ws = new WebSocket(`ws://localhost:8000/v1/ws`);

      ws.onopen = () => {
        console.log("WebSocket connected");
        // 認証メッセージを送信
        ws.send(
          JSON.stringify({
            type: "auth",
            token,
          })
        );

        // 実行監視を開始
        ws.send(
          JSON.stringify({
            type: "watch",
            execution_id: id,
          })
        );
      };

      ws.onmessage = (event) => {
        console.log("WebSocket raw message:", event.data);
        try {
          const message = JSON.parse(event.data);
          console.log("WebSocket parsed message:", message);
          if (message.type === "progress" && message.execution_id === id) {
            refetch();
          }
        } catch (error) {
          console.error("WebSocket JSON parse error:", error);
          console.error("Invalid message data:", event.data);
        }
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
      };

      setWsConnection(ws);

      return () => {
        ws.close();
      };
    }
  }, [id, refetch]);

  const handleCancel = async () => {
    try {
      await apiService.cancelExecution(id);
      refetch();
    } catch (error) {
      console.error("Failed to cancel execution:", error);
    }
  };

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const blob = await apiService.downloadFile(fileId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Failed to download file:", error);
    }
  };

  const handlePreview = async (fileId: string, filename: string) => {
    try {
      const blob = await apiService.downloadFile(fileId);
      const imageUrl = window.URL.createObjectURL(blob);
      setPreviewDialog({
        open: true,
        fileId,
        filename,
        imageUrl,
      });
    } catch (error) {
      console.error("Failed to preview file:", error);
    }
  };

  const handleClosePreview = () => {
    if (previewDialog.imageUrl) {
      window.URL.revokeObjectURL(previewDialog.imageUrl);
    }
    setPreviewDialog({ open: false, fileId: "", filename: "", imageUrl: "" });
  };

  const handleJsonPreview = async (fileId: string, filename: string) => {
    try {
      const response = await apiService.downloadFile(fileId);
      const content = await response.text();
      setJsonPreviewDialog({ open: true, fileId, filename, content });
    } catch (error) {
      console.error("Failed to load JSON file:", error);
    }
  };

  const handleJsonPreviewClose = () => {
    setJsonPreviewDialog({
      open: false,
      fileId: "",
      filename: "",
      content: "",
    });
  };

  const isImageFile = (filename: string | undefined | null) => {
    if (!filename || typeof filename !== "string") return false;
    const imageExtensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"];
    return imageExtensions.some((ext) => filename.toLowerCase().endsWith(ext));
  };

  // ファイル名から処理ステップを抽出
  const getProcessingStepFromFilename = (filename: string): string => {
    console.log(`🔍 処理ステップ抽出デバッグ - ファイル名: ${filename}`);

    // 元画像のパターン: {execution_id}.{extension} または {execution_id}-input-{index}.{extension}
    const nameWithoutExt = filename.split(".")[0];
    console.log(`📝 拡張子なしファイル名: ${nameWithoutExt}`);

    // execution_idのパターンをチェック（UUID形式）
    const uuidPattern =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

    // 単純なexecution_idのみの場合（元画像）
    if (uuidPattern.test(nameWithoutExt)) {
      console.log(`✅ 元画像パターンにマッチ`);
      return "元画像";
    }

    // input付きの場合（複数ファイルアップロード時の元画像）
    if (nameWithoutExt.includes("-input-")) {
      console.log(`✅ 入力ファイルパターンにマッチ`);
      return "元画像";
    }

    // 処理済みファイルのパターン: {execution_id}_{processing_step}.{extension}
    const parts = filename.split("_");
    console.log(`📂 アンダースコア分割結果:`, parts);

    if (parts.length >= 2) {
      const stepPart = parts.slice(1).join("_"); // execution_idの後の部分を取得
      const stepName = stepPart.split(".")[0]; // 拡張子を除去
      console.log(`🎯 処理ステップ名: "${stepName}"`);

      // ステップ名を日本語に変換
      const stepLabels: Record<string, string> = {
        resize: "リサイズ処理",
        resized: "リサイズ処理",
        "ai-detection": "物体検知",
        detected: "物体検知",
        detection: "物体検知",
        filter: "フィルタ処理",
        filtered: "フィルタ処理",
        enhancement: "画質向上",
        enhanced: "画質向上",
      };

      const result = stepLabels[stepName] || stepName;
      console.log(`🏷️ 最終結果: "${result}"`);
      return result;
    }

    console.log(`❌ どのパターンにもマッチしませんでした`);
    return "不明な処理";
  };

  // 処理順序を取得（パイプラインの実際のステップ順序に基づく）
  const getProcessingOrder = (filename: string): number => {
    console.log(`🔍 処理順序取得デバッグ - ファイル名: ${filename}`);

    // 元画像は常に最初
    const stepInfo = getProcessingStepFromFilename(filename);
    if (stepInfo === "元画像") {
      console.log(`✅ 元画像として認識 - 順序: 0`);
      return 0;
    }

    // パイプラインのステップ情報から順序を決定
    if (execution?.steps && execution.steps.length > 0) {
      console.log(`📝 実行ステップ情報を使用:`, execution.steps);

      // ファイル名からステップ名を抽出してステップリストで検索
      const parts = filename.split("_");

      if (parts.length >= 2) {
        const stepPart = parts.slice(1).join("_");
        const stepName = stepPart.split(".")[0];
        console.log(`🎯 抽出されたステップ名: "${stepName}"`);

        // component_nameまたはname、stepIdでマッチするステップを検索
        const stepIndex = execution.steps.findIndex((step: any) => {
          const matches =
            step.component_name
              ?.toLowerCase()
              .includes(stepName.toLowerCase()) ||
            step.name?.toLowerCase().includes(stepName.toLowerCase()) ||
            step.step_id?.toLowerCase().includes(stepName.toLowerCase()) ||
            // 既知のマッピングも考慮
            (stepName === "resized" &&
              (step.component_name === "resize" ||
                step.name?.includes("リサイズ"))) ||
            (stepName === "detected" &&
              (step.component_name === "ai_detection" ||
                step.name?.includes("検知"))) ||
            (stepName === "filtered" &&
              (step.component_name === "filter" ||
                step.name?.includes("フィルタ"))) ||
            (stepName === "enhanced" &&
              (step.component_name === "enhancement" ||
                step.name?.includes("向上")));

          console.log(
            `🔍 ステップマッチチェック - ${step.component_name}(${step.name}): ${matches}`
          );
          return matches;
        });

        if (stepIndex !== -1) {
          const order = stepIndex + 1; // 元画像が0なので、ステップは1から開始
          console.log(`✅ ステップ順序発見 - ${stepName}: ${order}`);
          return order;
        }
      }
    }

    // フォールバック: 固定マッピング
    console.log(`⚠️ フォールバック順序マッピングを使用`);
    const fallbackOrderMap: Record<string, number> = {
      元画像: 0,
      リサイズ処理: 1,
      物体検知: 2,
      フィルタ処理: 3,
      画質向上: 4,
    };

    const fallbackOrder = fallbackOrderMap[stepInfo] || 999;
    console.log(`🔄 フォールバック順序: ${stepInfo} -> ${fallbackOrder}`);
    return fallbackOrder;
  };

  const isJsonFile = (filename: string) => {
    return filename.toLowerCase().endsWith(".json");
  };

  const getFileType = (filename: string) => {
    if (isImageFile(filename)) return "image";
    if (isJsonFile(filename)) return "json";
    return "other";
  };

  const getFileTypeLabel = (filename: string) => {
    const type = getFileType(filename);
    switch (type) {
      case "image":
        return "画像";
      case "json":
        return "JSON";
      default:
        return "その他";
    }
  };

  const getFileTypeColor = (filename: string) => {
    const type = getFileType(filename);
    switch (type) {
      case "image":
        return "primary";
      case "json":
        return "secondary";
      default:
        return "default";
    }
  };

  const loadImageForDisplay = async (fileId: string) => {
    if (imageUrls[fileId] || loadingImages[fileId]) {
      console.log(`Skipping load for ${fileId}: already loaded or loading`);
      return; // 既に読み込み済みまたは読み込み中
    }

    console.log(`Loading image for file_id: ${fileId}`);
    setLoadingImages((prev) => ({ ...prev, [fileId]: true }));

    try {
      const blob = await apiService.downloadFile(fileId);
      const imageUrl = window.URL.createObjectURL(blob);
      console.log(
        `Successfully loaded image for ${fileId}, blob size: ${
          blob.size
        }, URL: ${imageUrl.substring(0, 50)}...`
      );
      setImageUrls((prev) => ({ ...prev, [fileId]: imageUrl }));
    } catch (error) {
      console.error(`Failed to load image for ${fileId}:`, error);
    } finally {
      setLoadingImages((prev) => ({ ...prev, [fileId]: false }));
    }
  };

  // 実行が完了した時に画像を自動読み込み
  React.useEffect(() => {
    if (execution?.status === "completed" && execution.output_files) {
      console.log(
        "Auto-loading images for completed execution, total files:",
        execution.output_files.length
      );
      const imageFiles = execution.output_files.filter((file) =>
        isImageFile(file.filename)
      );
      console.log(
        "Image files to load:",
        imageFiles.map((f) => ({ id: f.file_id, name: f.filename }))
      );

      imageFiles.forEach((file, index) => {
        // 順次ロードして競合を避ける
        setTimeout(() => {
          loadImageForDisplay(file.file_id);
        }, index * 100); // 100ms間隔でロード
      });
    }
  }, [execution?.status, execution?.output_files]);

  // 画像プレビュータブが表示される時に画像を再読み込み
  React.useEffect(() => {
    if (resultsTabValue === 0 && execution?.output_files) {
      const imageFiles = execution.output_files.filter((file) =>
        isImageFile(file.filename)
      );

      imageFiles.forEach((file, index) => {
        // 既に読み込み済みでないか、URLが無効でないかチェック
        if (!imageUrls[file.file_id]) {
          setTimeout(() => {
            loadImageForDisplay(file.file_id);
          }, index * 100);
        }
      });
    }
  }, [resultsTabValue, execution?.output_files, imageUrls]);

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

  if (!execution) {
    return <Typography>読み込み中...</Typography>;
  }

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
        <Button
          variant="outlined"
          startIcon={<ArrowBack />}
          onClick={() => navigate("/executions")}
        >
          実行監視一覧に戻る
        </Button>
        <Box>
          <Typography variant="h4">実行監視</Typography>
          <Typography variant="subtitle1" color="textSecondary">
            実行ID: {execution.execution_id}
          </Typography>
        </Box>
      </Box>

      {/* 実行状況サマリ */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography variant="h6">実行状況</Typography>
            <Box sx={{ display: "flex", gap: 1 }}>
              <Chip
                label={getStatusText(execution.status)}
                color={getStatusColor(execution.status) as any}
              />
              {execution.status === "running" && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Cancel />}
                  onClick={handleCancel}
                >
                  キャンセル
                </Button>
              )}
              <Button
                variant="outlined"
                size="small"
                startIcon={<Refresh />}
                onClick={() => refetch()}
              >
                更新
              </Button>
            </Box>
          </Box>

          <Typography variant="body2" gutterBottom>
            進捗: {execution.progress.current_step} (
            {execution.progress.completed_steps}/
            {execution.progress.total_steps})
          </Typography>

          <LinearProgress
            variant="determinate"
            value={execution.progress.percentage}
            sx={{ mb: 2 }}
          />

          <Typography variant="body2" color="textSecondary">
            {execution.progress.percentage.toFixed(1)}% 完了
          </Typography>

          {execution.error_message && (
            <Alert severity="error" sx={{ mt: 2 }}>
              <Typography variant="body2" gutterBottom>
                {execution.error_message}
              </Typography>
              {execution.error_details && (
                <Box sx={{ mt: 1 }}>
                  {execution.error_details.failed_nodes &&
                    execution.error_details.failed_nodes.length > 0 && (
                      <Box sx={{ mt: 1 }}>
                        <Typography
                          variant="caption"
                          display="block"
                          gutterBottom
                        >
                          <strong>失敗したステップ:</strong>
                        </Typography>
                        {execution.error_details.failed_nodes.map(
                          (node, index) => (
                            <Typography
                              key={index}
                              variant="caption"
                              display="block"
                            >
                              • {node.name}: {node.message}
                            </Typography>
                          )
                        )}
                      </Box>
                    )}
                  {execution.error_details.processing_errors && (
                    <Box sx={{ mt: 1 }}>
                      <Typography
                        variant="caption"
                        display="block"
                        gutterBottom
                      >
                        <strong>処理エラー詳細:</strong>
                      </Typography>
                      {execution.error_details.processing_errors.errors &&
                        execution.error_details.processing_errors.errors.map(
                          (error, index) => (
                            <Typography
                              key={index}
                              variant="caption"
                              display="block"
                              sx={{ ml: 1 }}
                            >
                              • {error.step}: {error.message}
                            </Typography>
                          )
                        )}
                      {execution.error_details.processing_errors
                        .missing_files &&
                        execution.error_details.processing_errors.missing_files
                          .length > 0 && (
                          <Box sx={{ mt: 1, ml: 1 }}>
                            <Typography
                              variant="caption"
                              display="block"
                              gutterBottom
                            >
                              <strong>見つからないファイル:</strong>
                            </Typography>
                            {execution.error_details.processing_errors.missing_files.map(
                              (filename, index) => (
                                <Typography
                                  key={index}
                                  variant="caption"
                                  display="block"
                                  sx={{ ml: 1 }}
                                >
                                  • {filename}
                                </Typography>
                              )
                            )}
                          </Box>
                        )}
                    </Box>
                  )}
                </Box>
              )}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* ステップ詳細 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            ステップ詳細
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>コンポーネント</TableCell>
                  <TableCell>ステータス</TableCell>
                  <TableCell>開始時刻</TableCell>
                  <TableCell>完了時刻</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {execution.steps.map((step, index) => (
                  <TableRow key={index}>
                    <TableCell>{step.component_name}</TableCell>
                    <TableCell>
                      <Chip
                        label={getStatusText(step.status)}
                        color={getStatusColor(step.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {step.started_at
                        ? new Date(step.started_at).toLocaleString()
                        : "-"}
                    </TableCell>
                    <TableCell>
                      {step.completed_at
                        ? new Date(step.completed_at).toLocaleString()
                        : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            処理結果
          </Typography>
          <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
            <Tabs
              value={resultsTabValue}
              onChange={(_, newValue) => setResultsTabValue(newValue)}
            >
              <Tab
                label={`画像プレビュー ${
                  execution.output_files.filter((f) => isImageFile(f.filename))
                    .length > 0
                    ? `(${
                        execution.output_files.filter((f) =>
                          isImageFile(f.filename)
                        ).length
                      })`
                    : ""
                }`}
              />
              <Tab
                label={`ファイル一覧 ${
                  execution.output_files.length > 0
                    ? `(${execution.output_files.length})`
                    : ""
                }`}
              />
              <Tab label="処理詳細" />
            </Tabs>
          </Box>

          {/* 画像プレビュータブ */}
          {resultsTabValue === 0 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                処理結果画像
              </Typography>
              {execution.output_files.length === 0 ? (
                <Alert severity="info">
                  処理結果ファイルがまだ生成されていません。実行が完了するまでお待ちください。
                </Alert>
              ) : execution.output_files.filter((file) =>
                  isImageFile(file.filename)
                ).length === 0 ? (
                <Alert severity="warning">
                  画像ファイルが見つかりませんでした。「ファイル一覧」タブで他の出力ファイルを確認してください。
                </Alert>
              ) : (
                <Grid container spacing={2}>
                  {execution.output_files
                    .filter((file) => isImageFile(file.filename))
                    .sort(
                      (a, b) =>
                        getProcessingOrder(a.filename) -
                        getProcessingOrder(b.filename)
                    )
                    .map((file, index) => (
                      <Grid item xs={12} sm={6} md={4} key={file.file_id}>
                        <Card>
                          <CardContent>
                            <Box
                              sx={{
                                mb: 1,
                                display: "flex",
                                alignItems: "center",
                                gap: 1,
                                flexWrap: "wrap",
                              }}
                            >
                              <Box
                                sx={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 0.5,
                                }}
                              >
                                <Chip
                                  label={`処理順 ${index + 1}`}
                                  color="secondary"
                                  size="small"
                                  sx={{
                                    fontWeight: "bold",
                                    fontSize: "0.75rem",
                                  }}
                                />
                                <Typography
                                  variant="caption"
                                  color="textSecondary"
                                >
                                  →
                                </Typography>
                              </Box>
                              <Chip
                                label={getProcessingStepFromFilename(
                                  file.filename
                                )}
                                color="primary"
                                size="small"
                                sx={{ mb: 0 }}
                              />
                            </Box>
                            <Typography variant="subtitle2" gutterBottom noWrap>
                              {file.filename}
                            </Typography>
                            <Box
                              sx={{
                                width: "100%",
                                height: 200,
                                backgroundColor: "#f5f5f5",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                cursor: "pointer",
                                border: "1px dashed #ccc",
                                borderRadius: 1,
                                overflow: "hidden",
                                position: "relative",
                              }}
                              onClick={() =>
                                handlePreview(file.file_id, file.filename)
                              }
                            >
                              {loadingImages[file.file_id] ? (
                                <Typography color="textSecondary">
                                  読み込み中...
                                </Typography>
                              ) : imageUrls[file.file_id] ? (
                                <img
                                  src={imageUrls[file.file_id]}
                                  alt={file.filename}
                                  style={{
                                    width: "100%",
                                    height: "100%",
                                    objectFit: "cover",
                                  }}
                                />
                              ) : (
                                <Typography color="textSecondary">
                                  クリックで画像を表示
                                </Typography>
                              )}
                            </Box>
                            <Box sx={{ mt: 2, display: "flex", gap: 1 }}>
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<Visibility />}
                                onClick={() =>
                                  handlePreview(file.file_id, file.filename)
                                }
                              >
                                プレビュー
                              </Button>
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<Download />}
                                onClick={() =>
                                  handleDownload(file.file_id, file.filename)
                                }
                              >
                                DL
                              </Button>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                </Grid>
              )}
            </Box>
          )}

          {/* ファイル一覧タブ */}
          {resultsTabValue === 1 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                出力ファイル一覧
              </Typography>
              {execution.output_files.length === 0 ? (
                <Alert severity="info">
                  処理結果ファイルがまだ生成されていません。実行が完了するまでお待ちください。
                </Alert>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell width="60px">順序</TableCell>
                        <TableCell>ファイル名</TableCell>
                        <TableCell>処理ステップ</TableCell>
                        <TableCell>タイプ</TableCell>
                        <TableCell>サイズ</TableCell>
                        <TableCell>アクション</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {execution.output_files
                        .sort(
                          (a: any, b: any) =>
                            getProcessingOrder(a.filename) -
                            getProcessingOrder(b.filename)
                        )
                        .map((file: any, index: number) => (
                          <TableRow key={file.file_id}>
                            <TableCell>
                              <Chip
                                label={`処理順 ${index + 1}`}
                                color="secondary"
                                size="small"
                                sx={{
                                  fontWeight: "bold",
                                  fontSize: "0.75rem",
                                }}
                              />
                            </TableCell>
                            <TableCell>{file.filename}</TableCell>
                            <TableCell>
                              <Chip
                                label={getProcessingStepFromFilename(
                                  file.filename
                                )}
                                color="primary"
                                size="small"
                              />
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={getFileTypeLabel(file.filename)}
                                color={getFileTypeColor(file.filename) as any}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>
                              {(file.file_size / 1024 / 1024).toFixed(2)} MB
                            </TableCell>
                            <TableCell>
                              <Box sx={{ display: "flex", gap: 1 }}>
                                {isImageFile(file.filename) && (
                                  <Button
                                    variant="outlined"
                                    size="small"
                                    startIcon={<Visibility />}
                                    onClick={() =>
                                      handlePreview(file.file_id, file.filename)
                                    }
                                  >
                                    プレビュー
                                  </Button>
                                )}
                                {isJsonFile(file.filename) && (
                                  <Button
                                    variant="outlined"
                                    size="small"
                                    startIcon={<Visibility />}
                                    onClick={() =>
                                      handleJsonPreview(
                                        file.file_id,
                                        file.filename
                                      )
                                    }
                                  >
                                    JSON表示
                                  </Button>
                                )}
                                <Button
                                  variant="outlined"
                                  size="small"
                                  startIcon={<Download />}
                                  onClick={() =>
                                    handleDownload(file.file_id, file.filename)
                                  }
                                >
                                  ダウンロード
                                </Button>
                              </Box>
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}

          {/* 処理詳細タブ */}
          {resultsTabValue === 2 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                処理詳細情報
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        実行統計
                      </Typography>
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="body2">
                          総実行時間:{" "}
                          {(() => {
                            console.log("=== 総実行時間計算デバッグ ===");
                            console.log(
                              "execution.completed_at:",
                              execution.completed_at
                            );
                            console.log(
                              "execution.started_at:",
                              execution.started_at
                            );
                            console.log("execution.steps:", execution.steps);

                            // 実行レベルのタイムスタンプがある場合はそれを使用
                            if (
                              execution.completed_at &&
                              execution.started_at
                            ) {
                              console.log("実行レベルのタイムスタンプを使用");
                              return `${Math.round(
                                (new Date(execution.completed_at).getTime() -
                                  new Date(execution.started_at).getTime()) /
                                  1000
                              )}秒`;
                            }

                            // 実行レベルのタイムスタンプがない場合、ステップから計算
                            const completedSteps = execution.steps.filter(
                              (s) => s.status === "completed"
                            );
                            console.log("completedSteps:", completedSteps);

                            if (completedSteps.length === 0) {
                              console.log("完了したステップが0個");
                              return "実行中または未開始";
                            }

                            const stepStartTimes = completedSteps
                              .map((s) => s.started_at)
                              .filter((t) => t)
                              .map((t) => new Date(t).getTime());
                            const stepEndTimes = completedSteps
                              .map((s) => s.completed_at)
                              .filter((t) => t)
                              .map((t) => new Date(t).getTime());

                            console.log("stepStartTimes:", stepStartTimes);
                            console.log("stepEndTimes:", stepEndTimes);

                            if (
                              stepStartTimes.length === 0 ||
                              stepEndTimes.length === 0
                            ) {
                              console.log("ステップのタイムスタンプが不足");
                              return "実行中または未開始";
                            }

                            const earliestStart = Math.min(...stepStartTimes);
                            const latestEnd = Math.max(...stepEndTimes);

                            console.log(
                              "earliestStart:",
                              new Date(earliestStart)
                            );
                            console.log("latestEnd:", new Date(latestEnd));
                            console.log(
                              "計算された時間:",
                              (latestEnd - earliestStart) / 1000
                            );

                            return `${Math.round(
                              (latestEnd - earliestStart) / 1000
                            )}秒`;
                          })()}
                        </Typography>
                        <Typography variant="body2">
                          処理ステップ数: {execution.steps.length}
                        </Typography>
                        <Typography variant="body2">
                          完了ステップ数:{" "}
                          {
                            execution.steps.filter(
                              (s) => s.status === "completed"
                            ).length
                          }
                        </Typography>
                        <Typography variant="body2">
                          出力ファイル数: {execution.output_files.length}
                        </Typography>
                        <Typography variant="body2">
                          総出力サイズ:{" "}
                          {(
                            execution.output_files.reduce(
                              (sum, f) => sum + f.file_size,
                              0
                            ) /
                            1024 /
                            1024
                          ).toFixed(2)}{" "}
                          MB
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* 画像プレビューダイアログ */}
      <Dialog
        open={previewDialog.open}
        onClose={handleClosePreview}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{previewDialog.filename}</DialogTitle>
        <DialogContent>
          {previewDialog.imageUrl && (
            <Box
              component="img"
              src={previewDialog.imageUrl}
              alt={previewDialog.filename}
              sx={{
                width: "100%",
                height: "auto",
                maxHeight: "70vh",
                objectFit: "contain",
              }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePreview}>閉じる</Button>
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={() => {
              handleDownload(previewDialog.fileId, previewDialog.filename);
              handleClosePreview();
            }}
          >
            ダウンロード
          </Button>
        </DialogActions>
      </Dialog>

      {/* JSONプレビューダイアログ */}
      <Dialog
        open={jsonPreviewDialog.open}
        onClose={handleJsonPreviewClose}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{jsonPreviewDialog.filename}</DialogTitle>
        <DialogContent>
          <Box
            component="pre"
            sx={{
              backgroundColor: "#f5f5f5",
              padding: 2,
              borderRadius: 1,
              overflow: "auto",
              maxHeight: "400px",
              fontSize: "0.875rem",
              fontFamily: "monospace",
            }}
          >
            {jsonPreviewDialog.content &&
              JSON.stringify(JSON.parse(jsonPreviewDialog.content), null, 2)}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleJsonPreviewClose}>閉じる</Button>
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={() => {
              const blob = new Blob([jsonPreviewDialog.content], {
                type: "application/json",
              });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = jsonPreviewDialog.filename;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
            }}
          >
            ダウンロード
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
