import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Grid,
  Chip,
  Paper,
  Switch,
  FormControlLabel,
} from "@mui/material";
import { Camera, CameraAlt, PlayArrow, StopCircle } from "@mui/icons-material";
import { apiService } from "../services/api";
import {
  CameraStreamPipelinesResponse,
  CameraStreamPipeline,
  ProcessedFrame,
  Detection,
} from "../types";

interface CameraStreamState {
  isInitialized: boolean;
  isStreaming: boolean;
  isConnected: boolean;
  error: string | null;
  selectedPipeline: string;
  pipelines: CameraStreamPipeline[];
  lastProcessedFrame: ProcessedFrame | null;
  frameCount: number;
  avgProcessingTime: number;
}

export const CameraStream: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const [state, setState] = useState<CameraStreamState>({
    isInitialized: false,
    isStreaming: false,
    isConnected: false,
    error: null,
    selectedPipeline: "",
    pipelines: [],
    lastProcessedFrame: null,
    frameCount: 0,
    avgProcessingTime: 0,
  });

  const [showDetections, setShowDetections] = useState(true);
  const [streamingRate, setStreamingRate] = useState(5); // frames per second

  // Load available pipelines on component mount
  useEffect(() => {
    loadPipelines();
  }, []);

  const loadPipelines = async () => {
    try {
      const response: CameraStreamPipelinesResponse =
        await apiService.getCameraStreamPipelines();
      setState((prev) => ({
        ...prev,
        pipelines: response.pipelines,
        selectedPipeline:
          response.pipelines.length > 0 ? response.pipelines[0].id : "",
        error: null,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: `パイプラインの読み込みに失敗しました: ${error}`,
      }));
    }
  };

  const initializeCamera = async () => {
    try {
      setState((prev) => ({ ...prev, error: null }));

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 },
        },
        audio: false,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;

        videoRef.current.onloadedmetadata = () => {
          setState((prev) => ({
            ...prev,
            isInitialized: true,
            error: null,
          }));
        };
      }
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: `カメラの初期化に失敗しました: ${error}`,
      }));
    }
  };

  const startStreaming = async () => {
    if (!state.selectedPipeline) {
      setState((prev) => ({
        ...prev,
        error: "パイプラインを選択してください",
      }));
      return;
    }

    try {
      // Connect to WebSocket
      const wsUrl = `${
        window.location.protocol === "https:" ? "wss:" : "ws:"
      }//${window.location.host}/api/ws/camera-stream/pc_camera`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setState((prev) => ({
          ...prev,
          isConnected: true,
          isStreaming: true,
          error: null,
        }));

        // Start sending frames
        startFrameCapture();
      };

      ws.onmessage = (event) => {
        try {
          const data: ProcessedFrame = JSON.parse(event.data);
          handleProcessedFrame(data);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.onclose = () => {
        setState((prev) => ({
          ...prev,
          isConnected: false,
          isStreaming: false,
        }));
        stopFrameCapture();
      };

      ws.onerror = (error) => {
        setState((prev) => ({
          ...prev,
          error: `WebSocket接続エラー: ${error}`,
          isConnected: false,
          isStreaming: false,
        }));
        stopFrameCapture();
      };

      wsRef.current = ws;
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: `ストリーミング開始に失敗しました: ${error}`,
      }));
    }
  };

  const stopStreaming = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    stopFrameCapture();

    setState((prev) => ({
      ...prev,
      isStreaming: false,
      isConnected: false,
      lastProcessedFrame: null,
    }));
  };

  const startFrameCapture = () => {
    const captureFrame = () => {
      if (!videoRef.current || !canvasRef.current || !state.isConnected) {
        return;
      }

      const video = videoRef.current;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");

      if (!ctx) return;

      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // Draw current frame to canvas
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Convert to base64
      const frameData = canvas.toDataURL("image/jpeg", 0.8).split(",")[1];

      // Send frame via WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        const message = {
          type: "frame",
          frame_data: frameData,
          timestamp_ms: Date.now(),
          width: canvas.width,
          height: canvas.height,
          pipeline_id: state.selectedPipeline,
          processing_params: {},
        };

        wsRef.current.send(JSON.stringify(message));
      }
    };

    // Start capturing frames at specified rate
    intervalRef.current = setInterval(captureFrame, 1000 / streamingRate);
  };

  const stopFrameCapture = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const handleProcessedFrame = (frame: ProcessedFrame) => {
    setState((prev) => {
      const newFrameCount = prev.frameCount + 1;
      const newAvgTime =
        (prev.avgProcessingTime * prev.frameCount + frame.processing_time_ms) /
        newFrameCount;

      return {
        ...prev,
        lastProcessedFrame: frame,
        frameCount: newFrameCount,
        avgProcessingTime: newAvgTime,
      };
    });

    // Draw detections if enabled
    if (showDetections && frame.detections) {
      drawDetections(frame.detections);
    }
  };

  const drawDetections = (detections: Detection[]) => {
    if (!overlayCanvasRef.current || !videoRef.current) return;

    const canvas = overlayCanvasRef.current;
    const video = videoRef.current;
    const ctx = canvas.getContext("2d");

    if (!ctx) return;

    // Set canvas dimensions to match video display
    const rect = video.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    // Clear previous detections
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Scale factors for video display
    const scaleX = rect.width / video.videoWidth;
    const scaleY = rect.height / video.videoHeight;

    // Draw detection boxes
    ctx.strokeStyle = "#ff0000";
    ctx.lineWidth = 2;
    ctx.font = "14px Arial";
    ctx.fillStyle = "#ff0000";

    detections.forEach((detection) => {
      const x1 = detection.bbox.x1 * scaleX;
      const y1 = detection.bbox.y1 * scaleY;
      const x2 = detection.bbox.x2 * scaleX;
      const y2 = detection.bbox.y2 * scaleY;

      // Draw bounding box
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      // Draw label
      const label = `${detection.class_name} (${Math.round(
        detection.confidence * 100
      )}%)`;
      const textWidth = ctx.measureText(label).width;

      // Draw background for text
      ctx.fillStyle = "rgba(255, 0, 0, 0.8)";
      ctx.fillRect(x1, y1 - 20, textWidth + 4, 16);

      // Draw text
      ctx.fillStyle = "#ffffff";
      ctx.fillText(label, x1 + 2, y1 - 6);
    });
  };

  const handlePipelineChange = (pipelineId: string) => {
    setState((prev) => ({ ...prev, selectedPipeline: pipelineId }));

    // If currently streaming, restart with new pipeline
    if (state.isStreaming) {
      stopStreaming();
      setTimeout(() => startStreaming(), 500);
    }
  };

  const cleanupResources = useCallback(() => {
    stopStreaming();

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    setState((prev) => ({
      ...prev,
      isInitialized: false,
      isStreaming: false,
      isConnected: false,
    }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return cleanupResources;
  }, [cleanupResources]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        リアルタイムカメラ処理
      </Typography>

      {state.error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {state.error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Control Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                制御パネル
              </Typography>

              <Box sx={{ mb: 2 }}>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>処理パイプライン</InputLabel>
                  <Select
                    value={state.selectedPipeline}
                    onChange={(e) => handlePipelineChange(e.target.value)}
                    disabled={state.isStreaming}
                  >
                    {state.pipelines.map((pipeline) => (
                      <MenuItem key={pipeline.id} value={pipeline.id}>
                        {pipeline.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>フレームレート (fps)</InputLabel>
                  <Select
                    value={streamingRate}
                    onChange={(e) => setStreamingRate(Number(e.target.value))}
                    disabled={state.isStreaming}
                  >
                    <MenuItem value={1}>1 fps</MenuItem>
                    <MenuItem value={2}>2 fps</MenuItem>
                    <MenuItem value={5}>5 fps</MenuItem>
                    <MenuItem value={10}>10 fps</MenuItem>
                  </Select>
                </FormControl>

                <FormControlLabel
                  control={
                    <Switch
                      checked={showDetections}
                      onChange={(e) => setShowDetections(e.target.checked)}
                    />
                  }
                  label="検出結果を表示"
                />
              </Box>

              <Box sx={{ display: "flex", gap: 1, flexDirection: "column" }}>
                {!state.isInitialized ? (
                  <Button
                    variant="contained"
                    startIcon={<Camera />}
                    onClick={initializeCamera}
                    fullWidth
                  >
                    カメラを初期化
                  </Button>
                ) : !state.isStreaming ? (
                  <Button
                    variant="contained"
                    startIcon={<PlayArrow />}
                    onClick={startStreaming}
                    disabled={!state.selectedPipeline}
                    fullWidth
                  >
                    ストリーミング開始
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<StopCircle />}
                    onClick={stopStreaming}
                    fullWidth
                  >
                    ストリーミング停止
                  </Button>
                )}

                <Button
                  variant="outlined"
                  startIcon={<CameraAlt />}
                  onClick={cleanupResources}
                  disabled={state.isStreaming}
                  fullWidth
                >
                  カメラを停止
                </Button>
              </Box>

              {/* Status */}
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  ステータス
                </Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                  <Chip
                    label={
                      state.isInitialized
                        ? "カメラ初期化済み"
                        : "カメラ未初期化"
                    }
                    color={state.isInitialized ? "success" : "default"}
                    size="small"
                  />
                  <Chip
                    label={state.isConnected ? "接続中" : "未接続"}
                    color={state.isConnected ? "success" : "default"}
                    size="small"
                  />
                  <Chip
                    label={state.isStreaming ? "ストリーミング中" : "停止中"}
                    color={state.isStreaming ? "primary" : "default"}
                    size="small"
                  />
                </Box>
              </Box>

              {/* Statistics */}
              {state.frameCount > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    処理統計
                  </Typography>
                  <Typography variant="body2">
                    処理フレーム数: {state.frameCount}
                  </Typography>
                  <Typography variant="body2">
                    平均処理時間: {Math.round(state.avgProcessingTime)}ms
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Video Display */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                カメラ映像
              </Typography>

              <Box sx={{ position: "relative", display: "inline-block" }}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{
                    width: "100%",
                    maxWidth: "640px",
                    height: "auto",
                    backgroundColor: "#000",
                    borderRadius: "4px",
                  }}
                />

                {/* Overlay canvas for detections */}
                <canvas
                  ref={overlayCanvasRef}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    pointerEvents: "none",
                  }}
                />

                {!state.isInitialized && (
                  <Box
                    sx={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: "rgba(0, 0, 0, 0.7)",
                      color: "white",
                      borderRadius: "4px",
                    }}
                  >
                    <Typography>カメラを初期化してください</Typography>
                  </Box>
                )}
              </Box>

              {/* Hidden canvas for frame capture */}
              <canvas ref={canvasRef} style={{ display: "none" }} />

              {/* Processing Results */}
              {state.lastProcessedFrame && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    最新の処理結果
                  </Typography>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="body2">
                      ステータス: {state.lastProcessedFrame.status}
                    </Typography>
                    <Typography variant="body2">
                      処理時間: {state.lastProcessedFrame.processing_time_ms}ms
                    </Typography>
                    {state.lastProcessedFrame.detections &&
                      state.lastProcessedFrame.detections.length > 0 && (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" gutterBottom>
                            検出結果:
                          </Typography>
                          {state.lastProcessedFrame.detections.map(
                            (detection, index) => (
                              <Chip
                                key={index}
                                label={`${detection.class_name} (${Math.round(
                                  detection.confidence * 100
                                )}%)`}
                                size="small"
                                sx={{ mr: 1, mb: 1 }}
                              />
                            )
                          )}
                        </Box>
                      )}
                    {state.lastProcessedFrame.error && (
                      <Alert severity="error" sx={{ mt: 1 }}>
                        {state.lastProcessedFrame.error}
                      </Alert>
                    )}
                  </Paper>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};
