// camera_preview.rs - カメラプレビュー機能の実装例
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::State;
use nokhwa::pixel_format::RgbFormat;
use nokhwa::utils::{RequestedFormat, RequestedFormatType};
use nokhwa::Camera;

pub struct CameraState {
    pub camera: Arc<Mutex<Option<Camera>>>,
    pub preview_active: Arc<Mutex<bool>>,
}

impl Default for CameraState {
    fn default() -> Self {
        CameraState {
            camera: Arc::new(Mutex::new(None)),
            preview_active: Arc::new(Mutex::new(false)),
        }
    }
}

#[tauri::command]
pub async fn start_camera_preview(
    camera_index: usize,
    config: serde_json::Value,
    state: State<'_, CameraState>,
) -> Result<String, String> {
    use nokhwa::utils::CameraIndex;
    
    // カメラが既にアクティブかチェック
    {
        let preview_active = state.preview_active.lock().unwrap();
        if *preview_active {
            return Err("プレビューは既にアクティブです".to_string());
        }
    }

    // カメラを初期化
    let requested = RequestedFormat::new::<RgbFormat>(RequestedFormatType::AbsoluteHighestFrameRate);
    
    match Camera::new(CameraIndex::Index(camera_index as u32), requested) {
        Ok(mut camera) => {
            // カメラを開始
            if let Err(e) = camera.open_stream() {
                return Err(format!("カメラストリームの開始に失敗: {}", e));
            }

            // カメラ状態を保存
            {
                let mut cam = state.camera.lock().unwrap();
                *cam = Some(camera);
            }

            // プレビューフラグを有効化
            {
                let mut preview_active = state.preview_active.lock().unwrap();
                *preview_active = true;
            }

            // プレビューURLを返す（実際の実装では、フレームをBase64エンコードしたデータURLまたは
            // 静的ファイルパスを返す必要があります）
            Ok("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjVmNWY1Ii8+CiAgPHRleHQgeD0iNTAlIiB5PSI1MCUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNiIgZmlsbD0iIzY2NiI+CiAgICBVU0Ljgqvjg6Hjg6njg5fjg6zjg5Pjg6Xjg7wnZWxsdHVncNh3aWR0Ej0iNDAwIgn='".to_string())
        }
        Err(e) => Err(format!("カメラの初期化に失敗: {}", e))
    }
}

#[tauri::command]
pub async fn stop_camera_preview(state: State<'_, CameraState>) -> Result<(), String> {
    // プレビューフラグを無効化
    {
        let mut preview_active = state.preview_active.lock().unwrap();
        *preview_active = false;
    }

    // カメラを停止
    {
        let mut cam = state.camera.lock().unwrap();
        if let Some(ref mut camera) = *cam {
            let _ = camera.stop_stream();
        }
        *cam = None;
    }

    Ok(())
}

#[tauri::command]
pub async fn get_camera_frame(state: State<'_, CameraState>) -> Result<String, String> {
    let cam = state.camera.lock().unwrap();
    if let Some(ref camera) = *cam {
        // ここで実際のフレームをキャプチャし、Base64エンコードして返す
        // この実装は複雑になるため、簡単な例では静的な画像を返します
        Ok("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjVmNWY1Ii8+CiAgPHRleHQgeD0iNTAlIiB5PSI1MCUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNiIgZmlsbD0iIzY2NiI+CiAgICBVU0Ljgqvjg6Hjg6njg5fjg6zjg5Ljg6Xjg7woRnJhbWUpCiAgPC90ZXh0Pgo8L3N2Zz4K".to_string())
    } else {
        Err("カメラが初期化されていません".to_string())
    }
}
