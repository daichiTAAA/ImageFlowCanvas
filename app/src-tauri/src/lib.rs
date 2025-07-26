// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use anyhow::Result;
use std::sync::Arc;
use tokio::sync::Mutex;
use uuid::Uuid;
use std::path::PathBuf;

mod database;
mod auth;
mod pipeline;

use database::{DatabaseManager, InspectionTarget, InspectionSession, InspectionImage, AIInspectionResult, HumanVerificationResult};
use auth::{AuthManager, LoginCredentials, RegisterRequest, AuthResponse};
use pipeline::{PipelineClient, PipelineRequest, parse_qr_code};

// Application state
pub struct AppState {
    pub db: Arc<DatabaseManager>,
    pub auth: Arc<AuthManager>,
    pub pipeline: Arc<PipelineClient>,
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

// Enhanced camera capture with real implementation
#[tauri::command]
async fn capture_image_from_camera(config: CameraConfig) -> Result<String, String> {
    // Use tauri-plugin-camera for real camera integration
    // This is a placeholder implementation
    let image_data = format!("captured_image_{}_{}.jpg", 
        config.resolution, 
        Utc::now().timestamp()
    );
    Ok(image_data)
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
    result.insert("image_count".to_string(), serde_json::Value::Number(serde_json::Number::from(images.len())));
    
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

// Application initialization
async fn initialize_app() -> Result<AppState> {
    // Get application data directory
    let data_dir = tauri::api::path::app_data_dir(&tauri::Config::default())
        .unwrap_or_else(|| PathBuf::from("./data"));
    
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
    let pipeline = PipelineClient::new(api_endpoint, None);
    
    Ok(AppState {
        db: Arc::new(db),
        auth: Arc::new(auth),
        pipeline: Arc::new(pipeline),
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
            save_inspection_images,
            execute_ai_pipeline,
            save_inspection_result,
            get_inspection_history,
            get_app_config,
            set_app_config
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
