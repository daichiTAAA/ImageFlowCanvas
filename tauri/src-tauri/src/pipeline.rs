use anyhow::Result;
use serde::{Deserialize, Serialize};
use reqwest::Client;
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize)]
pub struct PipelineRequest {
    pub session_id: String,
    pub images: Vec<String>, // Base64 encoded images
    pub product_id: String,
    pub batch_id: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PipelineResponse {
    pub execution_id: String,
    pub session_id: String,
    pub overall_result: String,
    pub confidence: f64,
    pub processing_time: f64,
    pub detailed_results: Option<HashMap<String, serde_json::Value>>,
    pub pipeline_version: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct QRCodeData {
    pub product_id: String,
    pub batch_id: String,
    pub timestamp: Option<String>,
    pub metadata: Option<HashMap<String, String>>,
}

pub struct PipelineClient {
    client: Client,
    base_url: String,
    api_key: Option<String>,
}

impl PipelineClient {
    pub fn new(base_url: String, api_key: Option<String>) -> Self {
        Self {
            client: Client::new(),
            base_url,
            api_key,
        }
    }

    pub async fn execute_inspection(&self, request: &PipelineRequest) -> Result<PipelineResponse> {
        let url = format!("{}/api/v1/inspection/execute", self.base_url);
        
        let mut req_builder = self.client.post(&url).json(request);
        
        if let Some(api_key) = &self.api_key {
            req_builder = req_builder.bearer_auth(api_key);
        }
        
        let response = req_builder.send().await?;
        
        if !response.status().is_success() {
            return Err(anyhow::anyhow!("Pipeline execution failed: {}", response.status()));
        }
        
        let pipeline_response: PipelineResponse = response.json().await?;
        Ok(pipeline_response)
    }

    pub async fn get_pipeline_status(&self, execution_id: &str) -> Result<PipelineResponse> {
        let url = format!("{}/api/v1/inspection/status/{}", self.base_url, execution_id);
        
        let mut req_builder = self.client.get(&url);
        
        if let Some(api_key) = &self.api_key {
            req_builder = req_builder.bearer_auth(api_key);
        }
        
        let response = req_builder.send().await?;
        
        if !response.status().is_success() {
            return Err(anyhow::anyhow!("Failed to get pipeline status: {}", response.status()));
        }
        
        let pipeline_response: PipelineResponse = response.json().await?;
        Ok(pipeline_response)
    }

    pub async fn validate_target(&self, product_id: &str, batch_id: &str) -> Result<bool> {
        let url = format!("{}/api/v1/targets/validate", self.base_url);
        
        let payload = serde_json::json!({
            "product_id": product_id,
            "batch_id": batch_id
        });
        
        let mut req_builder = self.client.post(&url).json(&payload);
        
        if let Some(api_key) = &self.api_key {
            req_builder = req_builder.bearer_auth(api_key);
        }
        
        let response = req_builder.send().await?;
        
        if !response.status().is_success() {
            return Ok(false);
        }
        
        let result: serde_json::Value = response.json().await?;
        Ok(result.get("valid").and_then(|v| v.as_bool()).unwrap_or(false))
    }
}

pub fn parse_qr_code(qr_data: &str) -> Result<QRCodeData> {
    // Parse QR code data based on expected format
    // Format: PRODUCT_ID_BATCH_ID_TIMESTAMP or JSON
    
    if qr_data.starts_with('{') {
        // JSON format
        let data: QRCodeData = serde_json::from_str(qr_data)?;
        Ok(data)
    } else {
        // Underscore-separated format
        let parts: Vec<&str> = qr_data.split('_').collect();
        
        if parts.len() < 2 {
            return Err(anyhow::anyhow!("Invalid QR code format"));
        }
        
        Ok(QRCodeData {
            product_id: parts[0].to_string(),
            batch_id: parts.get(1).unwrap_or(&"UNKNOWN").to_string(),
            timestamp: parts.get(2).map(|s| s.to_string()),
            metadata: None,
        })
    }
}