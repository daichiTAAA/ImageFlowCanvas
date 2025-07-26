import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  Box,
  Button,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  Card,
  CardMedia,
  CardActions,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import {
  PhotoCamera,
  Refresh,
  KeyboardArrowLeft,
  KeyboardArrowRight,
  Videocam,
  VideocamOff,
  Cameraswitch,
  FolderOpen,
  CameraAlt,
} from "@mui/icons-material";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { readFile } from "@tauri-apps/plugin-fs";
import Webcam from "react-webcam";

interface CameraCaptureProps {
  onNext: (data: any) => void;
  onBack: () => void;
}

interface CameraConfig {
  resolution: string;
  quality: number;
  flash_enabled: boolean;
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({
  onNext,
  onBack,
}) => {
  const [capturing, setCapturing] = useState(false);
  const [images, setImages] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [config, setConfig] = useState<CameraConfig>({
    resolution: "1920x1080",
    quality: 0.8,
    flash_enabled: false,
  });

  // Webカメラ関連の状態 - デフォルトでは無効
  const [useWebcam, setUseWebcam] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [facingMode, setFacingMode] = useState<"user" | "environment">(
    "environment"
  );
  const [cameraPermission, setCameraPermission] = useState<
    "granted" | "denied" | "prompt" | "checking"
  >("prompt");

  // USBカメラ関連の状態
  const [usbCameras, setUsbCameras] = useState<any[]>([]);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);
  const [usbCameraAvailable, setUsbCameraAvailable] = useState(false);

  const webcamRef = useRef<Webcam>(null);

  const videoConstraints = {
    width: 1920,
    height: 1080,
    facingMode: facingMode,
  };

  // 初期化時にUSBカメラをチェック
  useEffect(() => {
    const checkUsbCameras = async () => {
      try {
        const cameras = (await invoke("list_usb_cameras")) as any[];
        setUsbCameras(cameras);
        setUsbCameraAvailable(cameras.length > 0);

        if (cameras.length > 0) {
          console.log("利用可能なUSBカメラ:", cameras);
        }
      } catch (err) {
        console.log("USBカメラのチェックに失敗:", err);
        setUsbCameraAvailable(false);
      }
    };

    checkUsbCameras();
  }, []);

  // 初期化時にWebView環境を検出してユーザーにガイダンスを表示
  useEffect(() => {
    const isTauriWebView = (window as any).__TAURI__ !== undefined;
    if (isTauriWebView && useWebcam) {
      setError(
        "TauriアプリケーションではWebカメラAPIに制限があります。\n" +
          "より確実な動作のため、USBカメラ機能をお使いください。\n\n" +
          "【おすすめの使用方法】\n" +
          "1. USBカメラを接続\n" +
          "2. 「USBカメラで撮影」ボタンで直接撮影"
      );
    }
  }, [useWebcam]);

  // カメラAPIの存在確認とフォールバック
  const checkCameraSupport = () => {
    // Tauri環境でのWebカメラAPIサポート確認
    const hasGetUserMedia = !!(
      navigator.mediaDevices && navigator.mediaDevices.getUserMedia
    );

    const nav = navigator as any;
    const hasLegacyGetUserMedia = !!(
      nav.getUserMedia ||
      nav.webkitGetUserMedia ||
      nav.mozGetUserMedia ||
      nav.msGetUserMedia
    );

    return hasGetUserMedia || hasLegacyGetUserMedia;
  };

  // レガシーAPIを使用したカメラアクセス
  const getLegacyUserMedia = (
    constraints: MediaStreamConstraints
  ): Promise<MediaStream> => {
    return new Promise((resolve, reject) => {
      const nav = navigator as any;
      const getUserMedia =
        nav.getUserMedia ||
        nav.webkitGetUserMedia ||
        nav.mozGetUserMedia ||
        nav.msGetUserMedia;

      if (!getUserMedia) {
        reject(new Error("getUserMedia is not supported"));
        return;
      }

      getUserMedia.call(navigator, constraints, resolve, reject);
    });
  };

  // カメラ権限の確認と開始（改良版）
  const startCamera = async () => {
    setError("");
    setCameraPermission("checking");

    // まずカメラサポートを確認
    if (!checkCameraSupport()) {
      setError(
        "このブラウザまたは環境ではカメラ機能がサポートされていません。\n" +
          "代わりにネイティブカメラ機能をご利用ください。"
      );
      setCameraPermission("denied");
      setUseWebcam(false);
      return;
    }

    try {
      const constraints = {
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          facingMode: facingMode,
        },
      };

      let stream: MediaStream;

      // 最新のAPIを試行
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          stream = await navigator.mediaDevices.getUserMedia(constraints);
        } catch (modernError) {
          console.warn("Modern getUserMedia failed:", modernError);
          // レガシーAPIにフォールバック
          stream = await getLegacyUserMedia(constraints);
        }
      } else {
        // レガシーAPIを使用
        stream = await getLegacyUserMedia(constraints);
      }

      // 権限が取得できた場合は一旦ストリームを停止
      stream.getTracks().forEach((track) => track.stop());

      setCameraPermission("granted");
      setCameraEnabled(true);
      setError("");
    } catch (err: any) {
      setCameraPermission("denied");
      setCameraEnabled(false);

      let errorMessage = "カメラへのアクセスに失敗しました。\n";

      if (err.name === "NotAllowedError") {
        errorMessage +=
          "カメラのアクセス許可が拒否されています。\n" +
          "ブラウザの設定でカメラの使用を許可してください。\n\n" +
          "【設定方法】\n" +
          "Chrome: アドレスバーのカメラアイコン → 許可\n" +
          "Safari: 環境設定 → Webサイト → カメラ → 許可\n" +
          "Edge: アドレスバーの設定アイコン → カメラ → 許可";
      } else if (err.name === "NotFoundError") {
        errorMessage +=
          "カメラデバイスが見つかりません。\n" +
          "カメラが正しく接続されているか確認してください。";
      } else if (err.name === "NotReadableError") {
        errorMessage +=
          "カメラが他のアプリケーションで使用中です。\n" +
          "他のカメラアプリを終了してから再試行してください。";
      } else if (err.message.includes("not implemented")) {
        errorMessage +=
          "この環境ではWebカメラAPIがサポートされていません。\n" +
          "代わりにネイティブカメラ機能をご利用ください。";
        setUseWebcam(false);
      } else {
        errorMessage += `エラー詳細: ${err.message}\n\n`;
        errorMessage += "代替手段としてネイティブカメラ機能をご利用ください。";
      }

      setError(errorMessage);
    }
  };

  // カメラを停止
  const stopCamera = () => {
    setCameraEnabled(false);
    setCameraPermission("prompt");
  };

  // カメラの向きを切り替え
  const switchCamera = () => {
    setFacingMode((prev) => (prev === "user" ? "environment" : "user"));
  };

  // Webカメラから画像をキャプチャ
  const captureWebcam = useCallback(() => {
    if (!webcamRef.current) {
      setError("カメラが初期化されていません");
      return;
    }

    setCapturing(true);
    setError("");

    try {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        setImages((prev) => [...prev, imageSrc]);
      } else {
        setError("Webカメラからの画像取得に失敗しました");
      }
    } catch (err) {
      setError("画像の撮影に失敗しました: " + (err as Error).message);
    } finally {
      setCapturing(false);
    }
  }, [webcamRef]);

  // Tauriネイティブカメラを使用した撮影（USBカメラ対応）
  const captureTauriCamera = async () => {
    setCapturing(true);
    setError("");

    try {
      const result = (await invoke("capture_image_from_camera", {
        config,
      })) as string;

      // USBカメラから直接撮影された場合（Base64データが返される）
      if (result.startsWith("data:image/")) {
        setImages((prev) => [...prev, result]);
        setError("✅ USBカメラで撮影が完了しました！");
      } else if (result === "CAMERA_APP_OPENED") {
        setError(
          "🎥 システムカメラアプリを開きました！\n\n" +
            "📸 写真を撮影後、「画像ファイルを選択」ボタンで画像を取り込んでください。"
        );
      } else if (result === "PHOTOBOOTH_APP_OPENED") {
        setError(
          "✅ Photo Boothアプリを開きました！\n\n" +
            "📸 写真を撮影後、「画像ファイルを選択」ボタンで画像を取り込んでください。"
        );
      } else {
        setImages((prev) => [...prev, result]);
      }
    } catch (err) {
      const errorMessage = (err as Error).message;

      if (errorMessage.includes("USBカメラが見つかりません")) {
        setError(
          "⚠️ USBカメラが見つかりません。\n\n" +
            "【確認事項】\n" +
            "1. USBカメラが正しく接続されているか確認\n" +
            "2. カメラドライバーがインストールされているか確認\n" +
            "3. 他のアプリケーションでカメラが使用されていないか確認\n\n" +
            "【代替方法】\n" +
            "• システムカメラアプリを手動で起動\n" +
            "• 既存の画像ファイルを直接選択"
        );
      } else if (errorMessage.includes("undefined")) {
        setError(
          "⚠️ カメラアプリの起動で問題が発生しました。\n\n" +
            "【解決方法】\n" +
            "1. 手動でカメラアプリを起動してください:\n" +
            "   • Finder > アプリケーション > Camera\n" +
            "   • または Photo Booth アプリ\n" +
            "2. 写真撮影後、「画像ファイルを選択」ボタンで画像を選択\n\n" +
            "【代替方法】\n" +
            "• 既存の画像ファイルを直接選択することも可能です"
        );
      } else {
        setError("カメラ撮影エラー:\n" + errorMessage);
      }
    } finally {
      setCapturing(false);
    }
  };

  // ファイル選択ダイアログで画像を選択
  const selectImageFile = async () => {
    setCapturing(true);
    setError("");

    try {
      const selected = await open({
        multiple: false,
        filters: [
          {
            name: "画像ファイル",
            extensions: ["png", "jpg", "jpeg", "gif", "bmp", "webp"],
          },
        ],
      });

      if (selected && typeof selected === "string") {
        // ファイルを読み込んでBase64に変換
        const fileData = await readFile(selected);
        const base64Data = btoa(
          String.fromCharCode(...new Uint8Array(fileData))
        );

        // 拡張子から MIME タイプを推定
        const extension = selected.split(".").pop()?.toLowerCase();
        let mimeType = "image/jpeg";
        if (extension === "png") mimeType = "image/png";
        else if (extension === "gif") mimeType = "image/gif";
        else if (extension === "bmp") mimeType = "image/bmp";
        else if (extension === "webp") mimeType = "image/webp";

        const dataUrl = `data:${mimeType};base64,${base64Data}`;
        setImages((prev) => [...prev, dataUrl]);
        setError("");
      }
    } catch (err) {
      setError(
        "画像ファイルの読み込みに失敗しました: " + (err as Error).message
      );
    } finally {
      setCapturing(false);
    }
  };

  const handleCapture = () => {
    if (useWebcam && cameraEnabled) {
      captureWebcam();
    } else {
      captureTauriCamera();
    }
  };

  const handleRetake = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleNext = async () => {
    if (images.length === 0) {
      setError("最低1枚の画像を撮影してください");
      return;
    }

    try {
      // Save images and proceed to next step
      onNext({ images, config });
    } catch (err) {
      setError("データの保存に失敗しました: " + (err as Error).message);
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Typography variant="h4" component="h1" gutterBottom>
        画像撮影
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          撮影方法の選択
        </Typography>

        {/* カメラタイプ選択 */}
        <Box sx={{ mb: 3 }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>推奨:</strong>{" "}
              ネイティブカメラ機能（デフォルト）を使用してください。
              <br />
              Tauriアプリケーションでは、ネイティブ機能がより安定して動作します。
            </Typography>
          </Alert>

          <FormControlLabel
            control={
              <Switch
                checked={useWebcam}
                onChange={(e) => {
                  setUseWebcam(e.target.checked);
                  if (!e.target.checked) {
                    stopCamera();
                    setError(""); // エラーメッセージをクリア
                  }
                }}
              />
            }
            label="Webカメラを使用（試験的機能）"
          />
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mt: 1, ml: 4 }}
          >
            {useWebcam
              ? "⚠️ WebView環境では制限があります。問題が発生した場合はネイティブ機能をお使いください。"
              : "✅ ネイティブカメラ機能を使用します。システムのカメラアプリが起動されます。"}
          </Typography>
        </Box>

        <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
          カメラ状態
        </Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Alert
              severity={usbCameraAvailable ? "success" : "info"}
              sx={{ height: "100%" }}
            >
              <Typography variant="body2">
                <strong>📷 USBカメラ:</strong>
                <br />
                {usbCameraAvailable
                  ? `✅ ${usbCameras.length}台のカメラが利用可能`
                  : "❌ USBカメラが見つかりません"}
                {usbCameraAvailable && usbCameras.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    検出されたカメラ:
                    <br />
                    {usbCameras.map((camera, index) => (
                      <div key={index} style={{ marginLeft: 8 }}>
                        • {camera.name}
                      </div>
                    ))}
                  </div>
                )}
              </Typography>
            </Alert>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Alert severity="info" sx={{ height: "100%" }}>
              <Typography variant="body2">
                <strong>🎥 システムカメラ:</strong>
                <br />
                内蔵カメラやシステムカメラアプリを使用
              </Typography>
            </Alert>
          </Grid>
        </Grid>

        <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
          画質設定
        </Typography>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <FormControl fullWidth>
              <InputLabel>解像度</InputLabel>
              <Select
                value={config.resolution}
                label="解像度"
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    resolution: e.target.value,
                  }))
                }
              >
                <MenuItem value="1920x1080">1920x1080 (FHD)</MenuItem>
                <MenuItem value="1280x720">1280x720 (HD)</MenuItem>
                <MenuItem value="640x480">640x480 (VGA)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <FormControl fullWidth>
              <InputLabel>画質</InputLabel>
              <Select
                value={config.quality}
                label="画質"
                onChange={(e) =>
                  setConfig((prev) => ({
                    ...prev,
                    quality: Number(e.target.value),
                  }))
                }
              >
                <MenuItem value={1.0}>最高画質</MenuItem>
                <MenuItem value={0.8}>高画質</MenuItem>
                <MenuItem value={0.6}>標準画質</MenuItem>
                <MenuItem value={0.4}>低画質</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        {error && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography component="pre" sx={{ whiteSpace: "pre-line" }}>
              {error}
            </Typography>
          </Alert>
        )}
      </Paper>

      {/* Webカメラプレビュー */}
      {useWebcam && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography variant="h6">カメラプレビュー</Typography>
            <Box sx={{ display: "flex", gap: 1 }}>
              {!cameraEnabled ? (
                <Button
                  variant="contained"
                  startIcon={<Videocam />}
                  onClick={startCamera}
                  disabled={cameraPermission === "checking"}
                >
                  {cameraPermission === "checking" ? "確認中..." : "カメラ開始"}
                </Button>
              ) : (
                <>
                  <Button
                    variant="outlined"
                    startIcon={<Cameraswitch />}
                    onClick={switchCamera}
                    size="small"
                  >
                    カメラ切替
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<VideocamOff />}
                    onClick={stopCamera}
                    size="small"
                  >
                    停止
                  </Button>
                </>
              )}
            </Box>
          </Box>

          <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
            {cameraPermission === "checking" && (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 2,
                  py: 4,
                }}
              >
                <CircularProgress />
                <Typography>カメラアクセスを確認中...</Typography>
              </Box>
            )}

            {cameraPermission === "granted" && cameraEnabled && (
              <Box sx={{ position: "relative", maxWidth: 600, width: "100%" }}>
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  screenshotFormat="image/jpeg"
                  screenshotQuality={config.quality}
                  videoConstraints={videoConstraints}
                  style={{
                    width: "100%",
                    borderRadius: 8,
                    border: "2px solid #e0e0e0",
                  }}
                  onUserMediaError={(error) => {
                    console.error("Webcam error:", error);
                    const errorMessage =
                      error instanceof Error ? error.message : String(error);
                    setError(
                      "Webカメラの初期化に失敗しました: " + errorMessage
                    );
                    setCameraEnabled(false);
                  }}
                />
                <Chip
                  label="ライブ"
                  color="error"
                  size="small"
                  sx={{
                    position: "absolute",
                    top: 8,
                    left: 8,
                    backgroundColor: "#ff4444",
                    color: "white",
                  }}
                />
              </Box>
            )}

            {cameraPermission === "denied" && (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 2,
                  py: 4,
                }}
              >
                <Typography color="error" align="center">
                  カメラアクセスが拒否されています
                </Typography>
                <Button variant="outlined" onClick={startCamera}>
                  再試行
                </Button>
              </Box>
            )}

            {!cameraEnabled && cameraPermission === "prompt" && (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 2,
                  py: 4,
                }}
              >
                <Typography align="center">
                  「カメラ開始」ボタンをクリックしてWebカメラを有効にしてください
                </Typography>
              </Box>
            )}
          </Box>
        </Paper>
      )}

      {/* 撮影コントロール */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          画像取得
        </Typography>

        {!useWebcam && (
          <Alert
            severity={usbCameraAvailable ? "success" : "info"}
            sx={{ mb: 3 }}
          >
            <Typography variant="body2">
              {usbCameraAvailable ? (
                <>
                  <strong>🎯 USBカメラ撮影（推奨）:</strong>
                  <br />
                  ① 「USBカメラで撮影」ボタンをクリック
                  <br />② 自動的に写真が撮影されて表示されます
                </>
              ) : (
                <>
                  <strong>📱 システムカメラ撮影:</strong>
                  <br />
                  ① 「カメラアプリを起動」ボタンをクリック
                  <br />
                  ② システムのカメラアプリで写真を撮影
                  <br />③ 「画像ファイルを選択」ボタンで撮影した画像を取り込み
                </>
              )}
            </Typography>
          </Alert>
        )}

        <Box
          sx={{
            display: "flex",
            gap: 2,
            flexWrap: "wrap",
            justifyContent: "center",
            mb: 2,
          }}
        >
          <Button
            variant="contained"
            startIcon={<CameraAlt />}
            onClick={handleCapture}
            disabled={capturing || (useWebcam && !cameraEnabled)}
            size="large"
            sx={{
              minWidth: 220,
              backgroundColor: useWebcam
                ? undefined
                : usbCameraAvailable
                ? "#1976d2"
                : "#2e7d32",
              "&:hover": {
                backgroundColor: useWebcam
                  ? undefined
                  : usbCameraAvailable
                  ? "#1565c0"
                  : "#1b5e20",
              },
            }}
          >
            {capturing ? (
              <>
                <CircularProgress size={20} color="inherit" sx={{ mr: 1 }} />
                撮影中...
              </>
            ) : useWebcam ? (
              "Webカメラで撮影"
            ) : usbCameraAvailable ? (
              "USBカメラで撮影"
            ) : (
              "カメラアプリを起動"
            )}
          </Button>

          <Button
            variant="outlined"
            startIcon={<FolderOpen />}
            onClick={selectImageFile}
            disabled={capturing}
            size="large"
            sx={{
              minWidth: 220,
              color: "#1976d2",
              borderColor: "#1976d2",
            }}
          >
            画像ファイルを選択
          </Button>
        </Box>

        <Typography
          variant="body2"
          color="text.secondary"
          align="center"
          sx={{ mb: 2 }}
        >
          撮影または既存の画像ファイルを選択してください
        </Typography>

        {useWebcam && !cameraEnabled && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Webカメラを使用するには、まず上記の「カメラ開始」ボタンをクリックしてください。
            </Typography>
          </Alert>
        )}
      </Paper>

      {/* 撮影した画像の表示 */}
      {images.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography variant="h6">
              撮影済み画像 ({images.length}枚)
            </Typography>
            <Chip
              label={`${images.length}枚`}
              color={images.length > 0 ? "success" : "default"}
            />
          </Box>

          <Grid container spacing={2}>
            {images.map((image, index) => (
              <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={index}>
                <Card>
                  <CardMedia
                    component="img"
                    height="200"
                    image={image}
                    alt={`撮影画像 ${index + 1}`}
                    sx={{ objectFit: "cover" }}
                  />
                  <CardActions>
                    <Button
                      size="small"
                      color="error"
                      startIcon={<Refresh />}
                      onClick={() => handleRetake(index)}
                      fullWidth
                    >
                      撮り直し
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* ナビゲーション */}
      <Box sx={{ display: "flex", justifyContent: "space-between", mt: 3 }}>
        <Button
          variant="outlined"
          startIcon={<KeyboardArrowLeft />}
          onClick={onBack}
        >
          戻る
        </Button>
        <Button
          variant="contained"
          endIcon={<KeyboardArrowRight />}
          onClick={handleNext}
          disabled={images.length === 0}
        >
          次へ ({images.length}枚の画像)
        </Button>
      </Box>
    </Box>
  );
};
