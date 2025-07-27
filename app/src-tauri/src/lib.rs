// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/

use tauri::Manager;
use tauri_plugin_sql::{Migration, MigrationKind};
use sqlx::SqlitePool;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::Mutex;
use uuid::Uuid;

mod database;
mod auth;
mod pipeline;
mod inspection_api;

use database::{DatabaseManager, InspectionTarget, InspectionSession, InspectionImage, AIInspectionResult, HumanVerificationResult};
use auth::{AuthManager, LoginCredentials, RegisterRequest, AuthResponse};
use pipeline::{PipelineClient, PipelineRequest, parse_qr_code};
use inspection_api::{InspectionApiClient, CreateExecutionRequest, SaveResultRequest};

// Application state
pub struct AppState {
    pub db: Arc<DatabaseManager>,
    pub auth: Arc<AuthManager>,
    pub pipeline: Arc<PipelineClient>,
    pub inspection_api: Arc<Mutex<InspectionApiClient>>,
}

// Enhanced data structures
#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionData {
    pub id: String,
    pub target_id: String,
    pub ai_result: String,
    pub human_result: String,
    pub confidence: f64,
    pub processing_time: f64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CameraConfig {
    pub resolution: String,
    pub quality: f32,
    pub flash_enabled: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct QRScanResult {
    pub data: String,
    pub format: String,
    pub confidence: f32,
}

// Legacy support command
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

// Authentication commands
#[tauri::command]
async fn login(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    credentials: LoginCredentials,
) -> Result<AuthResponse, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    app_state.auth.authenticate(&app_state.db, &credentials)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn register(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    request: RegisterRequest,
) -> Result<AuthResponse, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    app_state.auth.register(&app_state.db, &request)
        .await
        .map_err(|e| e.to_string())
}

// Enhanced QR code scanning with real implementation
#[tauri::command]
async fn scan_qr_code_camera() -> Result<QRScanResult, String> {
    // Use tauri-plugin-barcode-scanner for real QR code scanning
    // This is a placeholder implementation
    Ok(QRScanResult {
        data: "PRODUCT_001_BATCH_20240126".to_string(),
        format: "QR_CODE".to_string(),
        confidence: 0.95,
    })
}

#[tauri::command]
async fn parse_qr_data(qr_data: String) -> Result<InspectionTarget, String> {
    let parsed = parse_qr_code(&qr_data).map_err(|e| e.to_string())?;
    
    let target = InspectionTarget {
        id: Uuid::new_v4().to_string(),
        product_id: parsed.product_id,
        batch_id: parsed.batch_id,
        qr_code: qr_data,
        created_at: Utc::now(),
    };
    
    Ok(target)
}

// Enhanced camera capture with USB camera support
#[tauri::command]
async fn capture_image_from_camera(_config: CameraConfig) -> Result<String, String> {
    // Try USB camera capture first, then fallback to system camera app
    match capture_from_usb_camera().await {
        Ok(image_data) => Ok(image_data),
        Err(usb_error) => {
            println!("USB camera failed: {}, falling back to system camera", usb_error);
            open_system_camera_app().await
        }
    }
}

// USB camera capture using nokhwa with enhanced debugging and panic protection
async fn capture_from_usb_camera() -> Result<String, String> {
    use nokhwa::pixel_format::RgbFormat;
    use nokhwa::utils::{RequestedFormat, RequestedFormatType, CameraIndex};
    use nokhwa::Camera;
    use base64::{Engine as _, engine::general_purpose};
    
    println!("=== USB カメラ撮影開始 ===");
    
    // Try to find and use the first available USB camera
    let cameras = nokhwa::query(nokhwa::utils::ApiBackend::Auto)
        .map_err(|e| {
            let error_msg = format!("カメラデバイスの検索に失敗しました: {}", e);
            println!("{}", error_msg);
            error_msg
        })?;
    
    if cameras.is_empty() {
        let error_msg = "USBカメラが見つかりません\n\n確認事項:\n1. USBカメラが物理的に接続されているか\n2. カメラドライバーがインストールされているか\n3. 他のアプリでカメラが使用されていないか\n4. macOSの場合: システム環境設定 > セキュリティとプライバシー > カメラでアクセス許可を確認".to_string();
        println!("{}", error_msg);
        return Err(error_msg);
    }
    
    println!("利用可能なカメラデバイス: {} 台", cameras.len());
    for (i, camera_info) in cameras.iter().enumerate() {
        println!("  {}: {} ({})", i, camera_info.human_name(), camera_info.description());
    }
    
    // Try different camera initialization strategies
    let mut last_error = String::new();
    
    // Strategy 1: Try the EMEET SmartCam S600 specifically (index 0)
    let mut camera = None;
    for camera_idx in 0..std::cmp::min(cameras.len(), 3) {
        println!("カメラインデックス {} で初期化を試行...", camera_idx);
        
        let camera_index = CameraIndex::Index(camera_idx as u32);
        
        // Try with lower resolution first to avoid hardware issues - use simpler format request
        let requested_format = RequestedFormat::new::<RgbFormat>(RequestedFormatType::AbsoluteHighestResolution);
        
        match Camera::new(camera_index, requested_format) {
            Ok(cam) => {
                println!("カメラ {} の初期化に成功", camera_idx);
                camera = Some(cam);
                break;
            }
            Err(e) => {
                last_error = format!("カメラ {} の初期化に失敗: {}", camera_idx, e);
                println!("{}", last_error);
                continue;
            }
        }
    }
    
    let mut camera = camera.ok_or_else(|| {
        format!("すべてのカメラの初期化に失敗しました。最後のエラー: {}\n\n対処法:\n1. カメラが他のアプリで使用されていないか確認\n2. アプリを再起動\n3. USBケーブルを抜き差し\n4. 低解像度での撮影を試行済み", last_error)
    })?;
    
    println!("カメラストリームを開始中...");
    // Open the camera - simplified without panic handling for mutable reference
    match camera.open_stream() {
        Ok(_) => println!("カメラストリームの開始に成功"),
        Err(e) => {
            let error_msg = format!("カメラストリームの開始に失敗しました: {}\n\n考えられる原因:\n1. カメラへのアクセス権限が不足\n2. カメラが別のプロセスで使用中\n3. USBポートの問題", e);
            println!("{}", error_msg);
            return Err(error_msg);
        }
    }
    
    // Wait a bit for camera to stabilize
    println!("カメラの安定化を待機中...");
    std::thread::sleep(std::time::Duration::from_millis(2000)); // Increased wait time
    
    println!("フレームをキャプチャ中...");
    // Capture a frame with retry mechanism - simplified without panic handling
    let frame = {
        let mut last_error = String::new();
        let mut frame_result = None;
        
        for attempt in 1..=3 {
            println!("フレームキャプチャ試行 {}/3", attempt);
            
            match camera.frame() {
                Ok(frame) => {
                    frame_result = Some(frame);
                    break;
                }
                Err(e) => {
                    last_error = format!("試行 {}: {}", attempt, e);
                    println!("{}", last_error);
                    std::thread::sleep(std::time::Duration::from_millis(500));
                }
            }
        }
        
        frame_result.ok_or_else(|| {
            format!("3回の試行でフレームキャプチャに失敗しました。最後のエラー: {}", last_error)
        })?
    };
    
    println!("フレームをRGBにデコード中...");
    // Convert frame to RGB - simplified without panic handling
    let image_buffer = match frame.decode_image::<RgbFormat>() {
        Ok(buffer) => buffer,
        Err(e) => {
            let error_msg = format!("画像のデコードに失敗しました: {}", e);
            println!("{}", error_msg);
            return Err(error_msg);
        }
    };
    
    // Convert to image crate format
    let width = image_buffer.width();
    let height = image_buffer.height();
    let raw_data = image_buffer.into_raw();
    
    println!("画像サイズ: {}x{}", width, height);
    
    let img = image::RgbImage::from_raw(width, height, raw_data)
        .ok_or("画像の変換に失敗しました")?;
    
    // Convert to DynamicImage for easier encoding
    let dynamic_img = image::DynamicImage::ImageRgb8(img);
    
    println!("JPEGエンコード中...");
    // Encode to JPEG in memory
    let mut jpeg_data = Vec::new();
    let mut cursor = std::io::Cursor::new(&mut jpeg_data);
    
    dynamic_img.write_to(&mut cursor, image::ImageFormat::Jpeg)
        .map_err(|e| {
            let error_msg = format!("JPEG変換に失敗しました: {}", e);
            println!("{}", error_msg);
            error_msg
        })?;
    
    println!("カメラストリームを停止中...");
    // Close camera safely - simplified without panic handling
    match camera.stop_stream() {
        Ok(_) => println!("カメラストリームの停止に成功"),
        Err(e) => {
            let error_msg = format!("カメラストリームの停止に失敗しました: {}", e);
            println!("{}", error_msg);
            // Don't return error here as we have the image data
        }
    }
    
    // Convert to base64 data URL
    let base64_data = general_purpose::STANDARD.encode(&jpeg_data);
    let data_url = format!("data:image/jpeg;base64,{}", base64_data);
    
    println!("=== USB カメラ撮影完了 ===");
    println!("画像サイズ: {} bytes", jpeg_data.len());
    
    Ok(data_url)
}

// Fallback to system camera app
async fn open_system_camera_app() -> Result<String, String> {
    use std::process::Command;
    
    #[cfg(target_os = "macos")]
    {
        // Try multiple methods to open camera on macOS
        
        // Method 1: Try to open the Camera app directly
        let camera_result = Command::new("open")
            .arg("-a")
            .arg("Camera")
            .output();
            
        match camera_result {
            Ok(output) => {
                if output.status.success() {
                    return Ok("CAMERA_APP_OPENED".to_string());
                } else {
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    println!("Camera app failed: {}", stderr);
                }
            }
            Err(e) => {
                println!("Failed to execute camera command: {}", e);
            }
        }
        
        // Method 2: Try to open Photo Booth as fallback
        let photobooth_result = Command::new("open")
            .arg("-a")
            .arg("Photo Booth")
            .output();
            
        match photobooth_result {
            Ok(output) => {
                if output.status.success() {
                    return Ok("PHOTOBOOTH_APP_OPENED".to_string());
                } else {
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    println!("Photo Booth failed: {}", stderr);
                }
            }
            Err(e) => {
                println!("Failed to execute Photo Booth command: {}", e);
            }
        }
        
        return Err("カメラアプリが見つかりませんでした。\n\n手動でカメラアプリを起動してください:\n1. Finder > アプリケーション\n2. Camera または Photo Booth を起動\n3. 写真撮影後、「画像ファイルを選択」ボタンで画像を選択\n\nまたは、既存の画像ファイルを直接選択することも可能です。".to_string());
    }
    
    #[cfg(target_os = "windows")]
    {
        // Open Windows Camera app
        let output = Command::new("start")
            .arg("microsoft.windows.camera:")
            .output()
            .map_err(|e| format!("カメラアプリを開けませんでした: {}", e))?;
        
        if !output.status.success() {
            return Err("カメラアプリの起動に失敗しました。システムのカメラアプリを手動で開いて写真を撮影してください。".to_string());
        }
        
        return Ok("CAMERA_APP_OPENED".to_string());
    }
    
    #[cfg(target_os = "linux")]
    {
        // Try common Linux camera applications
        let apps = ["cheese", "guvcview", "kamoso"];
        let mut app_opened = false;
        
        for app in &apps {
            if Command::new(app).spawn().is_ok() {
                app_opened = true;
                break;
            }
        }
        
        if !app_opened {
            return Err("カメラアプリが見つかりませんでした。システムにカメラアプリをインストールしてください。".to_string());
        }
        
        return Ok("CAMERA_APP_OPENED".to_string());
    }
    
    // This should not be reached on any supported platform
    Err("未サポートのプラットフォームです。".to_string())
}

// New command to list available USB cameras with detailed debugging
#[tauri::command]
async fn list_usb_cameras() -> Result<Vec<serde_json::Value>, String> {
    use nokhwa::query;
    use serde_json::json;
    
    println!("=== USBカメラ検索を開始 ===");
    
    // Try all available backends for debugging
    let backends = vec![
        nokhwa::utils::ApiBackend::Auto,
        #[cfg(target_os = "macos")]
        nokhwa::utils::ApiBackend::AVFoundation,
        #[cfg(target_os = "windows")]
        nokhwa::utils::ApiBackend::MediaFoundation,
        #[cfg(target_os = "linux")]
        nokhwa::utils::ApiBackend::V4L2,
    ];
    
    let mut all_cameras = Vec::new();
    
    for backend in backends {
        println!("Backend {:?} を試行中...", backend);
        
        match query(backend) {
            Ok(cameras) => {
                println!("Backend {:?}: {}台のカメラを発見", backend, cameras.len());
                for (i, camera_info) in cameras.iter().enumerate() {
                    println!("  カメラ {}: {} ({})", i, camera_info.human_name(), camera_info.description());
                    all_cameras.push(json!({
                        "backend": format!("{:?}", backend),
                        "index": i,
                        "name": camera_info.human_name(),
                        "description": camera_info.description(),
                        "misc": camera_info.misc(),
                        "index_value": format!("{:?}", camera_info.index())
                    }));
                }
            }
            Err(e) => {
                println!("Backend {:?} でエラー: {}", backend, e);
            }
        }
    }
    
    // Also try to check system camera access permissions on macOS
    #[cfg(target_os = "macos")]
    {
        println!("=== macOS カメラ権限チェック ===");
        use std::process::Command;
        
        let output = Command::new("system_profiler")
            .arg("SPCameraDataType")
            .output();
            
        match output {
            Ok(result) => {
                let camera_info = String::from_utf8_lossy(&result.stdout);
                println!("System Profiler カメラ情報:");
                println!("{}", camera_info);
            }
            Err(e) => {
                println!("System Profiler実行エラー: {}", e);
            }
        }
    }
    
    println!("=== 合計 {} 台のカメラデバイスを発見 ===", all_cameras.len());
    
    if all_cameras.is_empty() {
        return Err("USBカメラが見つかりません。\n\n確認事項:\n1. USBカメラが正しく接続されているか\n2. 他のアプリケーションでカメラが使用されていないか\n3. macOSの場合、カメラアクセス権限が許可されているか\n4. USBケーブルが正常に動作しているか".to_string());
    }
    
    Ok(all_cameras)
}

// Debug command to test USB camera detection
#[tauri::command]
async fn debug_camera_detection() -> Result<String, String> {
    use std::process::Command;
    
    let mut debug_info = String::new();
    
    // System level camera detection
    debug_info.push_str("=== システムレベルカメラ検出 ===\n");
    match Command::new("system_profiler").arg("SPCameraDataType").output() {
        Ok(output) => {
            let camera_info = String::from_utf8_lossy(&output.stdout);
            debug_info.push_str(&camera_info);
        }
        Err(e) => {
            debug_info.push_str(&format!("System Profiler エラー: {}\n", e));
        }
    }
    
    debug_info.push_str("\n=== nokhwa ライブラリでの検出 ===\n");
    
    // Try different backends
    let backends = vec![
        ("Auto", nokhwa::utils::ApiBackend::Auto),
        #[cfg(target_os = "macos")]
        ("AVFoundation", nokhwa::utils::ApiBackend::AVFoundation),
    ];
    
    for (name, backend) in backends {
        debug_info.push_str(&format!("Backend {}: ", name));
        
        match nokhwa::query(backend) {
            Ok(cameras) => {
                debug_info.push_str(&format!("{}台のカメラを発見\n", cameras.len()));
                for (i, camera_info) in cameras.iter().enumerate() {
                    debug_info.push_str(&format!("  カメラ {}: {} ({})\n", 
                        i, camera_info.human_name(), camera_info.description()));
                    debug_info.push_str(&format!("    インデックス: {:?}\n", camera_info.index()));
                    debug_info.push_str(&format!("    その他情報: {}\n", camera_info.misc()));
                }
            }
            Err(e) => {
                debug_info.push_str(&format!("エラー: {}\n", e));
            }
        }
        debug_info.push_str("\n");
    }
    
    Ok(debug_info)
}

// New command for file-based image selection
#[tauri::command]
async fn select_image_file() -> Result<String, String> {
    // This will be used with tauri-plugin-dialog for file selection
    // For now, return instruction to use file dialog
    Ok("FILE_DIALOG_REQUIRED".to_string())
}

#[tauri::command]
async fn save_inspection_images(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    session_id: String,
    images: Vec<String>
) -> Result<Vec<String>, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let mut image_paths = Vec::new();
    
    for (index, image_data) in images.iter().enumerate() {
        let image_id = Uuid::new_v4().to_string();
        let file_path = format!("images/{}_{}.jpg", session_id, index);
        
        // Save image to filesystem (implementation would use tauri-plugin-fs)
        let inspection_image = InspectionImage {
            id: image_id,
            session_id: session_id.clone(),
            file_path: file_path.clone(),
            image_type: "capture".to_string(),
            file_size: Some(image_data.len() as i64),
            created_at: Utc::now(),
        };
        
        app_state.db.save_inspection_image(&inspection_image)
            .await
            .map_err(|e| e.to_string())?;
        
        image_paths.push(file_path);
    }
    
    Ok(image_paths)
}

// Enhanced AI pipeline execution with real backend integration
#[tauri::command]
async fn execute_ai_pipeline(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    session_id: String,
    target_id: String,
    images: Vec<String>
) -> Result<HashMap<String, serde_json::Value>, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let image_count = images.len();
    
    // Get target information for pipeline request
    let pipeline_request = PipelineRequest {
        session_id: session_id.clone(),
        images,
        product_id: "PRODUCT_001".to_string(), // This should come from target
        batch_id: "BATCH_20240126".to_string(), // This should come from target
    };
    
    // Execute pipeline
    let pipeline_response = app_state.pipeline.execute_inspection(&pipeline_request)
        .await
        .map_err(|e| e.to_string())?;
    
    // Save AI result to database
    let ai_result = AIInspectionResult {
        id: Uuid::new_v4().to_string(),
        session_id: session_id.clone(),
        pipeline_version: Some(pipeline_response.pipeline_version.clone()),
        overall_result: pipeline_response.overall_result.clone(),
        confidence: pipeline_response.confidence,
        processing_time: pipeline_response.processing_time,
        detailed_results: pipeline_response.detailed_results.as_ref()
            .map(|d| serde_json::to_string(d).unwrap_or_default()),
        created_at: Utc::now(),
    };
    
    app_state.db.save_ai_result(&ai_result)
        .await
        .map_err(|e| e.to_string())?;
    
    // Return results
    let mut result = HashMap::new();
    result.insert("execution_id".to_string(), serde_json::Value::String(pipeline_response.execution_id));
    result.insert("target_id".to_string(), serde_json::Value::String(target_id));
    result.insert("overall_result".to_string(), serde_json::Value::String(pipeline_response.overall_result));
    result.insert("confidence".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(pipeline_response.confidence).unwrap()));
    result.insert("processing_time".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(pipeline_response.processing_time).unwrap()));
    result.insert("image_count".to_string(), serde_json::Value::Number(serde_json::Number::from(image_count)));
    
    Ok(result)
}

// Enhanced inspection result saving with database integration
#[tauri::command]
async fn save_inspection_result(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    result: InspectionData
) -> Result<String, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    // Save human verification result
    let human_result = HumanVerificationResult {
        id: Uuid::new_v4().to_string(),
        session_id: result.target_id.clone(), // This should be session_id
        user_id: 1, // This should come from authenticated user
        final_result: result.human_result.clone(),
        notes: None,
        verification_time: result.processing_time,
        created_at: Utc::now(),
    };
    
    app_state.db.save_human_verification(&human_result)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(result.id)
}

// Enhanced inspection history with database integration
#[tauri::command]
async fn get_inspection_history(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    limit: Option<i32>
) -> Result<Vec<InspectionSession>, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    app_state.db.get_inspection_history(limit)
        .await
        .map_err(|e| e.to_string())
}

// Configuration management
#[tauri::command]
async fn get_app_config(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    key: String
) -> Result<Option<String>, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    app_state.db.get_config_value(&key)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn set_app_config(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    key: String,
    value: String
) -> Result<(), String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    app_state.db.set_config_value(&key, &value)
        .await
        .map_err(|e| e.to_string())
}

// New inspection API integration commands

#[tauri::command]
async fn get_inspection_targets(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    page: Option<i32>,
    search: Option<String>,
) -> Result<serde_json::Value, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let inspection_api = app_state.inspection_api.lock().await;
    let targets = inspection_api.get_targets(page, search)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(serde_json::to_value(targets).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn get_target_items(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    target_id: String,
) -> Result<serde_json::Value, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let inspection_api = app_state.inspection_api.lock().await;
    let items = inspection_api.get_target_items(&target_id)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(serde_json::to_value(items).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn create_inspection_execution(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    target_id: String,
    operator_id: Option<String>,
    qr_code: Option<String>,
) -> Result<serde_json::Value, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let request = CreateExecutionRequest {
        target_id,
        operator_id,
        qr_code,
        metadata: None,
    };
    
    let inspection_api = app_state.inspection_api.lock().await;
    let execution = inspection_api.create_execution(request)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(serde_json::to_value(execution).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn get_execution_items(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    execution_id: String,
) -> Result<serde_json::Value, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let inspection_api = app_state.inspection_api.lock().await;
    let items = inspection_api.get_execution_items(&execution_id)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(serde_json::to_value(items).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn execute_inspection_item_with_image(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    execution_id: String,
    item_id: String,
    image_data: Vec<u8>,
    image_filename: String,
) -> Result<serde_json::Value, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let inspection_api = app_state.inspection_api.lock().await;
    let result = inspection_api.execute_inspection_item(
        &execution_id,
        &item_id,
        image_data,
        &image_filename,
    )
    .await
    .map_err(|e| e.to_string())?;
    
    Ok(serde_json::to_value(result).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn save_inspection_result_api(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    execution_id: String,
    item_execution_id: String,
    judgment: String,
    comment: Option<String>,
    evidence_file_ids: Option<Vec<String>>,
    metrics: Option<HashMap<String, serde_json::Value>>,
) -> Result<serde_json::Value, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let request = SaveResultRequest {
        execution_id,
        item_execution_id,
        judgment,
        comment,
        evidence_file_ids,
        metrics,
    };
    
    let inspection_api = app_state.inspection_api.lock().await;
    let result = inspection_api.save_inspection_result(request)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(serde_json::to_value(result).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn get_inspection_results_api(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    execution_id: String,
) -> Result<serde_json::Value, String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let inspection_api = app_state.inspection_api.lock().await;
    let results = inspection_api.get_inspection_results(&execution_id)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(serde_json::to_value(results).map_err(|e| e.to_string())?)
}

#[tauri::command]
async fn set_inspection_api_auth_token(
    state: tauri::State<'_, Arc<Mutex<Option<AppState>>>>,
    token: String,
) -> Result<(), String> {
    let app_state = state.lock().await;
    let app_state = app_state.as_ref().ok_or("Application not initialized")?;
    
    let mut inspection_api = app_state.inspection_api.lock().await;
    inspection_api.set_auth_token(token);
    
    Ok(())
}

// Application initialization
async fn initialize_app() -> Result<AppState> {
    // Get application data directory - use system temp dir to avoid file watcher issues
    let data_dir = std::env::temp_dir().join("imageflowcanvas_inspection");
    
    std::fs::create_dir_all(&data_dir).unwrap();
    
    let db_path = data_dir.join("inspection.db");
    let database_url = format!("sqlite:{}", db_path.display());
    
    // Initialize database
    let db = DatabaseManager::new(&database_url).await?;
    
    // Initialize auth manager with a secret key (should be configurable)
    let auth = AuthManager::new("your-secret-key-here".to_string());
    
    // Initialize pipeline client
    let api_endpoint = db.get_config_value("api_endpoint").await?
        .unwrap_or_else(|| "https://api.imageflowcanvas.com".to_string());
    let pipeline = PipelineClient::new(api_endpoint.clone(), None);
    
    // Initialize inspection API client
    let inspection_api = InspectionApiClient::new(api_endpoint);
    
    Ok(AppState {
        db: Arc::new(db),
        auth: Arc::new(auth),
        pipeline: Arc::new(pipeline),
        inspection_api: Arc::new(Mutex::new(inspection_api)),
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app_state: Arc<Mutex<Option<AppState>>> = Arc::new(Mutex::new(None));
    let app_state_clone = app_state.clone();
    
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_sql::Builder::default().build())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(app_state)
        .setup(move |_app| {
            let app_state = app_state_clone.clone();
            tauri::async_runtime::spawn(async move {
                match initialize_app().await {
                    Ok(state) => {
                        *app_state.lock().await = Some(state);
                        println!("Application initialized successfully");
                    }
                    Err(e) => {
                        eprintln!("Failed to initialize application: {}", e);
                    }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            login,
            register,
            scan_qr_code_camera,
            parse_qr_data,
            capture_image_from_camera,
            list_usb_cameras,
            debug_camera_detection,
            select_image_file,
            save_inspection_images,
            execute_ai_pipeline,
            save_inspection_result,
            get_inspection_history,
            get_app_config,
            set_app_config,
            get_inspection_targets,
            get_target_items,
            create_inspection_execution,
            get_execution_items,
            execute_inspection_item_with_image,
            save_inspection_result_api,
            get_inspection_results_api,
            set_inspection_api_auth_token
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
