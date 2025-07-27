use serde::{Deserialize, Serialize};
use reqwest;
use anyhow::{Result, anyhow};
use std::collections::HashMap;
use uuid::Uuid;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone)]
pub struct InspectionApiClient {
    base_url: String,
    client: reqwest::Client,
    auth_token: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionTarget {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub product_code: String,
    pub version: String,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionItem {
    pub id: String,
    pub target_id: String,
    pub name: String,
    pub description: Option<String>,
    pub item_type: String,
    pub pipeline_id: Option<String>,
    pub pipeline_params: Option<HashMap<String, serde_json::Value>>,
    pub execution_order: i32,
    pub is_required: bool,
    pub criteria_id: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionExecution {
    pub id: String,
    pub target_id: String,
    pub operator_id: Option<String>,
    pub status: String,
    pub qr_code: Option<String>,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub error_message: Option<String>,
    pub target: Option<InspectionTarget>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionItemExecution {
    pub id: String,
    pub execution_id: String,
    pub item_id: String,
    pub status: String,
    pub image_file_id: Option<String>,
    pub pipeline_execution_id: Option<String>,
    pub ai_result: Option<serde_json::Value>,
    pub human_result: Option<serde_json::Value>,
    pub final_result: Option<String>,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub item: Option<InspectionItem>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionResult {
    pub id: String,
    pub execution_id: String,
    pub item_execution_id: String,
    pub judgment: String,
    pub comment: Option<String>,
    pub evidence_file_ids: Option<Vec<String>>,
    pub metrics: Option<HashMap<String, serde_json::Value>>,
    pub confidence_score: Option<f64>,
    pub processing_time_ms: Option<i32>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PaginatedResponse<T> {
    pub items: Vec<T>,
    pub total_count: i32,
    pub page: i32,
    pub page_size: i32,
    pub total_pages: i32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateExecutionRequest {
    pub target_id: String,
    pub operator_id: Option<String>,
    pub qr_code: Option<String>,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateExecutionResponse {
    pub execution_id: String,
    pub execution: InspectionExecution,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SaveResultRequest {
    pub execution_id: String,
    pub item_execution_id: String,
    pub judgment: String,
    pub comment: Option<String>,
    pub evidence_file_ids: Option<Vec<String>>,
    pub metrics: Option<HashMap<String, serde_json::Value>>,
}

impl InspectionApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            client: reqwest::Client::new(),
            auth_token: None,
        }
    }

    pub fn set_auth_token(&mut self, token: String) {
        self.auth_token = Some(token);
    }

    pub async fn get_targets(&self, page: Option<i32>, search: Option<String>) -> Result<PaginatedResponse<InspectionTarget>> {
        let mut url = format!("{}/api/v1/inspection/targets", self.base_url);
        let mut params = vec![];
        
        if let Some(page) = page {
            params.push(format!("page={}", page));
        }
        if let Some(search) = search {
            params.push(format!("search={}", search));
        }
        
        if !params.is_empty() {
            url.push_str("?");
            url.push_str(&params.join("&"));
        }

        let mut request = self.client.get(&url);
        
        if let Some(token) = &self.auth_token {
            request = request.header("Authorization", format!("Bearer {}", token));
        }

        let response = request.send().await?;
        
        if response.status().is_success() {
            let targets = response.json::<PaginatedResponse<InspectionTarget>>().await?;
            Ok(targets)
        } else {
            Err(anyhow!("Failed to get targets: {}", response.status()))
        }
    }

    pub async fn get_target_items(&self, target_id: &str) -> Result<PaginatedResponse<InspectionItem>> {
        let url = format!("{}/api/v1/inspection/targets/{}/items", self.base_url, target_id);

        let mut request = self.client.get(&url);
        
        if let Some(token) = &self.auth_token {
            request = request.header("Authorization", format!("Bearer {}", token));
        }

        let response = request.send().await?;
        
        if response.status().is_success() {
            let items = response.json::<PaginatedResponse<InspectionItem>>().await?;
            Ok(items)
        } else {
            Err(anyhow!("Failed to get target items: {}", response.status()))
        }
    }

    pub async fn create_execution(&self, request: CreateExecutionRequest) -> Result<CreateExecutionResponse> {
        let url = format!("{}/api/v1/inspection/executions", self.base_url);

        let mut req = self.client.post(&url)
            .json(&request);
        
        if let Some(token) = &self.auth_token {
            req = req.header("Authorization", format!("Bearer {}", token));
        }

        let response = req.send().await?;
        
        if response.status().is_success() {
            let execution = response.json::<CreateExecutionResponse>().await?;
            Ok(execution)
        } else {
            let error_text = response.text().await.unwrap_or_default();
            Err(anyhow!("Failed to create execution: {}", error_text))
        }
    }

    pub async fn get_execution(&self, execution_id: &str) -> Result<InspectionExecution> {
        let url = format!("{}/api/v1/inspection/executions/{}", self.base_url, execution_id);

        let mut request = self.client.get(&url);
        
        if let Some(token) = &self.auth_token {
            request = request.header("Authorization", format!("Bearer {}", token));
        }

        let response = request.send().await?;
        
        if response.status().is_success() {
            let execution = response.json::<InspectionExecution>().await?;
            Ok(execution)
        } else {
            Err(anyhow!("Failed to get execution: {}", response.status()))
        }
    }

    pub async fn get_execution_items(&self, execution_id: &str) -> Result<Vec<InspectionItemExecution>> {
        let url = format!("{}/api/v1/inspection/executions/{}/items", self.base_url, execution_id);

        let mut request = self.client.get(&url);
        
        if let Some(token) = &self.auth_token {
            request = request.header("Authorization", format!("Bearer {}", token));
        }

        let response = request.send().await?;
        
        if response.status().is_success() {
            let items = response.json::<Vec<InspectionItemExecution>>().await?;
            Ok(items)
        } else {
            Err(anyhow!("Failed to get execution items: {}", response.status()))
        }
    }

    pub async fn execute_inspection_item(
        &self,
        execution_id: &str,
        item_id: &str,
        image_data: Vec<u8>,
        image_filename: &str,
    ) -> Result<InspectionItemExecution> {
        let url = format!(
            "{}/api/v1/inspection/executions/{}/items/{}/execute",
            self.base_url, execution_id, item_id
        );

        let form = reqwest::multipart::Form::new()
            .part(
                "image",
                reqwest::multipart::Part::bytes(image_data)
                    .file_name(image_filename.to_string())
                    .mime_str("image/jpeg")?,
            );

        let mut req = self.client.post(&url)
            .multipart(form);
        
        if let Some(token) = &self.auth_token {
            req = req.header("Authorization", format!("Bearer {}", token));
        }

        let response = req.send().await?;
        
        if response.status().is_success() {
            let item_execution = response.json::<InspectionItemExecution>().await?;
            Ok(item_execution)
        } else {
            let error_text = response.text().await.unwrap_or_default();
            Err(anyhow!("Failed to execute inspection item: {}", error_text))
        }
    }

    pub async fn save_inspection_result(&self, request: SaveResultRequest) -> Result<InspectionResult> {
        let url = format!("{}/api/v1/inspection/results", self.base_url);

        let mut req = self.client.post(&url)
            .json(&request);
        
        if let Some(token) = &self.auth_token {
            req = req.header("Authorization", format!("Bearer {}", token));
        }

        let response = req.send().await?;
        
        if response.status().is_success() {
            let result = response.json::<InspectionResult>().await?;
            Ok(result)
        } else {
            let error_text = response.text().await.unwrap_or_default();
            Err(anyhow!("Failed to save inspection result: {}", error_text))
        }
    }

    pub async fn get_inspection_results(&self, execution_id: &str) -> Result<PaginatedResponse<InspectionResult>> {
        let url = format!("{}/api/v1/inspection/results?execution_id={}", self.base_url, execution_id);

        let mut request = self.client.get(&url);
        
        if let Some(token) = &self.auth_token {
            request = request.header("Authorization", format!("Bearer {}", token));
        }

        let response = request.send().await?;
        
        if response.status().is_success() {
            let results = response.json::<PaginatedResponse<InspectionResult>>().await?;
            Ok(results)
        } else {
            Err(anyhow!("Failed to get inspection results: {}", response.status()))
        }
    }
}