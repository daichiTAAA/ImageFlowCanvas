import React, { useState, useEffect, useRef } from "react";
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
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import {
  PhotoCamera,
  Refresh,
  KeyboardArrowLeft,
  KeyboardArrowRight,
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
  flash_enabled: boolean;
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({
  onNext,
  onBack,
}) => {
  const [capturing, setCapturing] = useState(false);
  const [images, setImages] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [config] = useState<CameraConfig>({
    flash_enabled: false,
  });

  // カメラ関連の状態
  const [usbCameras, setUsbCameras] = useState<any[]>([]);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);
  const [usbCameraAvailable, setUsbCameraAvailable] = useState(false);
  const [currentCameraType, setCurrentCameraType] = useState<"usb" | "system">(
    "system"
  );
  const [cameraActive, setCameraActive] = useState(false);
  const [filteredDevices, setFilteredDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const webcamRef = useRef<Webcam>(null);

  // カメラデバイスをフィルタリングする関数
  const filterCameraDevices = (
    devices: MediaDeviceInfo[]
  ): MediaDeviceInfo[] => {
    const seenGroupIds = new Set<string>();
    const seenLabels = new Set<string>();

    return devices.filter((device) => {
      // バーチャルカメラを除外
      const label = device.label.toLowerCase();
      if (
        label.includes("virtual") ||
        label.includes("obs") ||
        label.includes("snap") ||
        label.includes("zoom") ||
        label.includes("teams") ||
        label.includes("camera assistant") ||
        label.includes("screencast")
      ) {
        return false;
      }

      // 同じgroupIdのデバイスは1つだけ選択（最初のもの）
      if (device.groupId && seenGroupIds.has(device.groupId)) {
        return false;
      }
      if (device.groupId) {
        seenGroupIds.add(device.groupId);
      }

      // 同じラベルのデバイスは1つだけ選択
      if (device.label && seenLabels.has(device.label)) {
        return false;
      }
      if (device.label) {
        seenLabels.add(device.label);
      }

      return true;
    });
  };

  // Tauriカメラの重複を除去する関数
  const filterTauriCameras = (cameras: any[]): any[] => {
    const seenNames = new Set<string>();
    return cameras.filter((camera) => {
      if (seenNames.has(camera.name)) {
        return false;
      }
      seenNames.add(camera.name);
      return true;
    });
  };

  // WebカメラとTauriカメラの重複を検出して、Webカメラを優先する関数
  const mergeCameraLists = (
    webCameras: MediaDeviceInfo[],
    tauriCameras: any[]
  ): {
    filteredWebCameras: MediaDeviceInfo[];
    prioritizedTauriCameras: any[];
  } => {
    const webCameraNames = new Set(
      webCameras.map((cam) => cam.label.toLowerCase())
    );

    // Tauriカメラのうち、Webカメラと名前が重複しないもののみを残す
    const filteredTauriCameras = tauriCameras.filter((camera) => {
      const cameraName = camera.name.toLowerCase();
      // Webカメラに同じ名前のものがある場合は除外
      return !webCameraNames.has(cameraName);
    });

    return {
      filteredWebCameras: webCameras,
      prioritizedTauriCameras: filteredTauriCameras,
    };
  };

  // 初期化時にUSBカメラをチェック
  useEffect(() => {
    const checkCameras = async () => {
      try {
        // Webカメラデバイスを取得
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(
          (device) => device.kind === "videoinput"
        );

        // デバッグ情報をログ出力
        console.log("検出されたすべてのデバイス:", devices);
        console.log("ビデオ入力デバイス:", videoDevices);

        // TauriバックエンドのUSBカメラもチェック
        const cameras = (await invoke("list_usb_cameras")) as any[];
        console.log("Tauriで検出されたカメラ（フィルタリング前）:", cameras);

        // Tauriカメラの重複を除去
        const uniqueTauriCameras = filterTauriCameras(cameras);
        console.log(
          "Tauriで検出されたカメラ（重複除去後）:",
          uniqueTauriCameras
        );

        // Webカメラのフィルタリングを適用
        const basicFilteredWebCameras = filterCameraDevices(videoDevices);
        console.log(
          "Webカメラ（基本フィルタリング後）:",
          basicFilteredWebCameras
        );

        // WebカメラとTauriカメラの重複を処理（Webカメラを優先）
        const { filteredWebCameras, prioritizedTauriCameras } =
          mergeCameraLists(basicFilteredWebCameras, uniqueTauriCameras);

        console.log("最終的なWebカメラ:", filteredWebCameras);
        console.log("最終的なTauriカメラ:", prioritizedTauriCameras);

        setFilteredDevices(filteredWebCameras);
        setUsbCameras(prioritizedTauriCameras);
        setUsbCameraAvailable(prioritizedTauriCameras.length > 0);

        // 優先順位: Webカメラ > Tauriカメラ
        if (filteredWebCameras.length > 0) {
          setCurrentCameraType("system");
          setSelectedDeviceId(filteredWebCameras[0].deviceId);
        } else if (prioritizedTauriCameras.length > 0) {
          setCurrentCameraType("usb");
          setSelectedCameraIndex(0);
        }

        // カメラが利用可能なら自動的にプレビューを開始
        if (
          filteredWebCameras.length > 0 ||
          prioritizedTauriCameras.length > 0
        ) {
          setTimeout(() => startCameraPreview(), 500);
        }
      } catch (err) {
        console.log("カメラのチェックに失敗:", err);
        setUsbCameraAvailable(false);
        setCurrentCameraType("system");
      }
    };

    checkCameras();
  }, []);

  // カメラプレビューを開始
  const startCameraPreview = async () => {
    try {
      setCameraActive(true);
      setError("");

      // react-webcamはUSBカメラも自動的に検出して使用可能
      // Webcamコンポーネントが自動的にカメラストリームを開始
    } catch (err) {
      setError(
        "カメラプレビューの開始に失敗しました: " + (err as Error).message
      );
      setCameraActive(false);
    }
  };

  // カメラから画像を撮影
  const captureImage = async () => {
    setCapturing(true);
    setError("");

    try {
      if (webcamRef.current && cameraActive) {
        // react-webcamから直接スクリーンショットを取得
        const imageSrc = webcamRef.current.getScreenshot();
        if (imageSrc) {
          setImages((prev) => [...prev, imageSrc]);
          setError(
            `✅ ${
              currentCameraType === "usb" ? "🔌 Tauriカメラ" : "🌐 Webカメラ"
            }で撮影が完了しました！`
          );
        } else {
          throw new Error("スクリーンショットの取得に失敗しました");
        }
      } else if (currentCameraType === "usb" && usbCameraAvailable) {
        // フォールバック: TauriバックエンドのUSBカメラ機能を使用
        const result = (await invoke("capture_from_usb_camera", {
          cameraIndex: selectedCameraIndex,
          config,
        })) as string;

        if (result.startsWith("data:image/")) {
          setImages((prev) => [...prev, result]);
          setError("✅ USBカメラで撮影が完了しました！");
        }
      } else {
        // フォールバック: バックエンドのシステムカメラ機能を使用
        const result = (await invoke("capture_image_from_camera", {
          config,
        })) as string;

        if (result.startsWith("data:image/")) {
          setImages((prev) => [...prev, result]);
          setError("✅ システムカメラで撮影が完了しました！");
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
        }
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
            "• システムカメラに切り替えてご利用ください"
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
    captureImage();
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
    <Box sx={{ p: 3, maxWidth: 1400, mx: "auto" }}>
      {/* ヘッダー部分 - カメラ選択とステータス */}
      <Paper elevation={2} sx={{ p: 2, mb: 3, backgroundColor: "#f8f9fa" }}>
        <Grid container spacing={2} alignItems="center">
          {(filteredDevices.length > 1 || usbCameras.length > 0) && (
            <Grid size={{ xs: 12, md: 6 }}>
              <FormControl fullWidth>
                <InputLabel>カメラ選択</InputLabel>
                <Select
                  value={
                    currentCameraType === "system"
                      ? `web_${selectedDeviceId}`
                      : `tauri_${selectedCameraIndex}`
                  }
                  label="カメラ選択"
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value.startsWith("web_")) {
                      const deviceId = value.replace("web_", "");
                      setSelectedDeviceId(deviceId);
                      setCurrentCameraType("system");
                    } else if (value.startsWith("tauri_")) {
                      const index = parseInt(value.replace("tauri_", ""));
                      setSelectedCameraIndex(index);
                      setCurrentCameraType("usb");
                    }

                    // カメラが変更されたらプレビューを再開
                    if (cameraActive) {
                      setTimeout(() => {
                        setCameraActive(false);
                        setTimeout(() => startCameraPreview(), 300);
                      }, 100);
                    }
                  }}
                >
                  {/* Webカメラの選択肢（優先表示） */}
                  {filteredDevices.map((device, index) => (
                    <MenuItem
                      key={device.deviceId}
                      value={`web_${device.deviceId}`}
                    >
                      🌐 {device.label || `Webカメラ ${index + 1}`}
                    </MenuItem>
                  ))}

                  {/* Tauriカメラの選択肢 */}
                  {usbCameras.map((camera, index) => (
                    <MenuItem key={`tauri_${index}`} value={`tauri_${index}`}>
                      🔌 {camera.name || `Tauriカメラ ${index + 1}`}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          )}

          <Grid size={{ xs: 12, md: 6 }}>
            <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
              <Chip
                label={cameraActive ? "カメラ有効" : "カメラ停止中"}
                color={cameraActive ? "success" : "default"}
                icon={<CameraAlt />}
              />
              {images.length > 0 && (
                <Chip
                  label={`${images.length}枚撮影済み`}
                  color="primary"
                  icon={<PhotoCamera />}
                />
              )}
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* メインコンテンツエリア */}
      <Grid container spacing={3}>
        {/* 左側: カメラプレビューエリア */}
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper elevation={3} sx={{ p: 3, height: "fit-content" }}>
            <Typography
              variant="h6"
              gutterBottom
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              <CameraAlt />
              カメラプレビュー
            </Typography>

            {/* カメラコントロール */}
            {!cameraActive && (
              <Box sx={{ mb: 3 }}>
                <Button
                  variant="contained"
                  startIcon={<CameraAlt />}
                  onClick={startCameraPreview}
                  disabled={capturing}
                  color="primary"
                  size="large"
                  fullWidth
                  sx={{ py: 1.5 }}
                >
                  📹 カメラを開始
                </Button>
              </Box>
            )}

            {/* カメラプレビュー表示 */}
            <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
              {capturing && (
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 2,
                    py: 8,
                    minHeight: 400,
                    justifyContent: "center",
                  }}
                >
                  <CircularProgress size={60} />
                  <Typography variant="h6">カメラを準備中...</Typography>
                </Box>
              )}

              {cameraActive && (
                <Box
                  sx={{ position: "relative", maxWidth: 700, width: "100%" }}
                >
                  {currentCameraType === "system" ? (
                    <Webcam
                      ref={webcamRef}
                      audio={false}
                      width="100%"
                      screenshotFormat="image/jpeg"
                      videoConstraints={{
                        deviceId: selectedDeviceId
                          ? { exact: selectedDeviceId }
                          : undefined,
                        facingMode: selectedDeviceId
                          ? undefined
                          : "environment",
                        width: { ideal: 1920 },
                        height: { ideal: 1080 },
                      }}
                      style={{
                        borderRadius: 12,
                        border: "3px solid #2196f3",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.1)",
                      }}
                      onUserMediaError={(error) => {
                        console.error("Webcam error:", error);
                        const errorMessage =
                          typeof error === "string"
                            ? error
                            : error.message || "カメラアクセスエラー";
                        setError(
                          "カメラのアクセスに失敗しました: " + errorMessage
                        );
                        setCameraActive(false);
                      }}
                    />
                  ) : (
                    <Webcam
                      ref={webcamRef}
                      audio={false}
                      width="100%"
                      screenshotFormat="image/jpeg"
                      videoConstraints={{
                        width: { ideal: 1920 },
                        height: { ideal: 1080 },
                      }}
                      style={{
                        borderRadius: 12,
                        border: "3px solid #4caf50",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.1)",
                      }}
                      onUserMediaError={(error) => {
                        console.error("Tauri camera Webcam error:", error);
                        const errorMessage =
                          typeof error === "string"
                            ? error
                            : error.message || "カメラアクセスエラー";
                        setError(
                          "Tauriカメラのアクセスに失敗しました: " + errorMessage
                        );
                        setCameraActive(false);
                      }}
                    />
                  )}
                  <Chip
                    label={
                      currentCameraType === "usb"
                        ? `🔌 ${
                            usbCameras[selectedCameraIndex]?.name ||
                            `Tauriカメラ ${selectedCameraIndex + 1}`
                          }`
                        : `🌐 ${
                            filteredDevices.find(
                              (d) => d.deviceId === selectedDeviceId
                            )?.label || "Webカメラ"
                          }`
                    }
                    color={currentCameraType === "usb" ? "primary" : "success"}
                    size="medium"
                    sx={{
                      position: "absolute",
                      top: 12,
                      left: 12,
                      backgroundColor: "rgba(0,0,0,0.8)",
                      color: "white",
                      fontWeight: "bold",
                    }}
                  />
                </Box>
              )}

              {!cameraActive && !capturing && (
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 3,
                    py: 8,
                    minHeight: 400,
                    justifyContent: "center",
                    backgroundColor: "#f5f5f5",
                    borderRadius: 2,
                    width: "100%",
                  }}
                >
                  <CameraAlt sx={{ fontSize: 80, color: "#bdbdbd" }} />
                  <Typography
                    variant="h6"
                    align="center"
                    color="text.secondary"
                  >
                    「📹 カメラを開始」ボタンをクリックして
                    <br />
                    撮影を始めてください
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* 右側: 撮影コントロールエリア */}
        <Grid size={{ xs: 12, lg: 4 }}>
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography
              variant="h6"
              gutterBottom
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              <PhotoCamera />
              撮影操作
            </Typography>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Button
                variant="contained"
                startIcon={<CameraAlt />}
                onClick={handleCapture}
                disabled={capturing || !cameraActive}
                size="large"
                sx={{
                  py: 2,
                  backgroundColor: "#2e7d32",
                  "&:hover": {
                    backgroundColor: "#1b5e20",
                  },
                  fontSize: "1.1rem",
                  fontWeight: "bold",
                }}
              >
                {capturing ? (
                  <>
                    <CircularProgress
                      size={24}
                      color="inherit"
                      sx={{ mr: 1 }}
                    />
                    撮影中...
                  </>
                ) : cameraActive ? (
                  `📸 撮影する`
                ) : (
                  "📹 先にカメラを開始してください"
                )}
              </Button>

              <Button
                variant="outlined"
                startIcon={<FolderOpen />}
                onClick={selectImageFile}
                disabled={capturing}
                size="large"
                sx={{
                  py: 2,
                  color: "#1976d2",
                  borderColor: "#1976d2",
                  fontSize: "1.1rem",
                  "&:hover": {
                    backgroundColor: "#e3f2fd",
                  },
                }}
              >
                📁 ファイルから選択
              </Button>
            </Box>

            {error && (
              <Alert
                severity={error.includes("✅") ? "success" : "warning"}
                sx={{ mt: 2 }}
              >
                <Typography
                  component="pre"
                  sx={{ whiteSpace: "pre-line", fontSize: "0.9rem" }}
                >
                  {error}
                </Typography>
              </Alert>
            )}
          </Paper>

          {/* 撮影済み画像の表示 */}
          {images.length > 0 && (
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography
                variant="h6"
                gutterBottom
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <PhotoCamera />
                撮影済み画像 ({images.length}枚)
              </Typography>

              <Grid container spacing={2}>
                {images.map((image, index) => (
                  <Grid size={{ xs: 12 }} key={index}>
                    <Card elevation={2}>
                      <CardMedia
                        component="img"
                        height="150"
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
        </Grid>
      </Grid>

      {/* 全体撮影済み画像ギャラリー（大画面表示） */}
      {images.length > 0 && (
        <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography
              variant="h6"
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              📷 撮影済み画像ギャラリー
            </Typography>
            <Chip
              label={`${images.length}枚`}
              color="success"
              icon={<PhotoCamera />}
            />
          </Box>

          <Grid container spacing={2}>
            {images.map((image, index) => (
              <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={index}>
                <Card elevation={2}>
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

      {/* フッター: ナビゲーション */}
      <Paper elevation={2} sx={{ p: 3, backgroundColor: "#fafafa" }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Button
            variant="outlined"
            startIcon={<KeyboardArrowLeft />}
            onClick={onBack}
            size="large"
            sx={{ minWidth: 120 }}
          >
            戻る
          </Button>

          <Box sx={{ textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              画像を撮影してから次のステップに進んでください
            </Typography>
            <Typography
              variant="h6"
              color={images.length > 0 ? "success.main" : "text.secondary"}
            >
              {images.length > 0
                ? `✅ ${images.length}枚準備完了`
                : "📸 画像を撮影してください"}
            </Typography>
          </Box>

          <Button
            variant="contained"
            endIcon={<KeyboardArrowRight />}
            onClick={handleNext}
            disabled={images.length === 0}
            size="large"
            sx={{
              minWidth: 180,
              backgroundColor: images.length > 0 ? "#2e7d32" : undefined,
              "&:hover": {
                backgroundColor: images.length > 0 ? "#1b5e20" : undefined,
              },
            }}
          >
            次へ進む {images.length > 0 && `(${images.length}枚)`}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};
