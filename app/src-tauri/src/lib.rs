// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionTarget {
    pub id: String,
    pub product_id: String,
    pub batch_id: String,
    pub qr_code: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionResult {
    pub id: String,
    pub target_id: String,
    pub ai_result: String,
    pub human_result: String,
    pub confidence: f64,
    pub processing_time: f64,
    pub timestamp: DateTime<Utc>,
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
async fn scan_qr_code(qr_data: String) -> Result<InspectionTarget, String> {
    // Simulate QR code processing
    let parts: Vec<&str> = qr_data.split('_').collect();
    
    if parts.len() < 3 {
        return Err("Invalid QR code format".to_string());
    }
    
    let target = InspectionTarget {
        id: uuid::Uuid::new_v4().to_string(),
        product_id: parts[0].to_string(),
        batch_id: parts.get(2).unwrap_or(&"UNKNOWN").to_string(),
        qr_code: qr_data,
        timestamp: Utc::now(),
    };
    
    Ok(target)
}

#[tauri::command]
async fn save_inspection_images(images: Vec<String>) -> Result<Vec<String>, String> {
    // Simulate image saving (in real implementation, save to local storage)
    let mut image_paths = Vec::new();
    
    for (index, _image_data) in images.iter().enumerate() {
        let path = format!("inspection_image_{}.jpg", index);
        image_paths.push(path);
    }
    
    Ok(image_paths)
}

#[tauri::command]
async fn execute_ai_pipeline(target_id: String, images: Vec<String>) -> Result<HashMap<String, serde_json::Value>, String> {
    // Simulate AI pipeline execution
    tokio::time::sleep(tokio::time::Duration::from_millis(3000)).await;
    
    let mut result = HashMap::new();
    result.insert("execution_id".to_string(), serde_json::Value::String(uuid::Uuid::new_v4().to_string()));
    result.insert("target_id".to_string(), serde_json::Value::String(target_id));
    result.insert("overall_result".to_string(), serde_json::Value::String("PASS".to_string()));
    result.insert("confidence".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(0.87).unwrap()));
    result.insert("processing_time".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(5.5).unwrap()));
    result.insert("image_count".to_string(), serde_json::Value::Number(serde_json::Number::from(images.len())));
    
    Ok(result)
}

#[tauri::command]
async fn save_inspection_result(result: InspectionResult) -> Result<String, String> {
    // Simulate saving inspection result to database
    println!("Saving inspection result: {:?}", result);
    
    // In real implementation, save to SQLite database
    Ok(result.id)
}

#[tauri::command]
async fn get_inspection_history(limit: Option<i32>) -> Result<Vec<InspectionResult>, String> {
    // Simulate fetching inspection history
    let mut history = Vec::new();
    let count = limit.unwrap_or(10).min(100);
    
    for i in 0..count {
        let result = InspectionResult {
            id: format!("result_{}", i),
            target_id: format!("target_{}", i),
            ai_result: if i % 3 == 0 { "PASS".to_string() } else { "WARNING".to_string() },
            human_result: "OK".to_string(),
            confidence: 0.85 + (i as f64 * 0.01) % 0.15,
            processing_time: 3.0 + (i as f64 * 0.1) % 5.0,
            timestamp: Utc::now() - chrono::Duration::hours(i as i64),
        };
        history.push(result);
    }
    
    Ok(history)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_sql::Builder::default().build())
        .plugin(tauri_plugin_store::Builder::default().build())
        .invoke_handler(tauri::generate_handler![
            greet,
            scan_qr_code,
            save_inspection_images,
            execute_ai_pipeline,
            save_inspection_result,
            get_inspection_history
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
