use sqlx::{SqlitePool, migrate::MigrateDatabase, Sqlite};
use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct User {
    pub id: i64,
    pub username: String,
    pub email: Option<String>,
    pub full_name: Option<String>,
    pub role: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct InspectionTarget {
    pub id: String,
    pub product_id: String,
    pub batch_id: String,
    pub qr_code: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct InspectionSession {
    pub id: String,
    pub target_id: String,
    pub user_id: Option<i64>,
    pub status: String,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct InspectionImage {
    pub id: String,
    pub session_id: String,
    pub file_path: String,
    pub image_type: String,
    pub file_size: Option<i64>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct AIInspectionResult {
    pub id: String,
    pub session_id: String,
    pub pipeline_version: Option<String>,
    pub overall_result: String,
    pub confidence: f64,
    pub processing_time: f64,
    pub detailed_results: Option<String>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct HumanVerificationResult {
    pub id: String,
    pub session_id: String,
    pub user_id: i64,
    pub final_result: String,
    pub notes: Option<String>,
    pub verification_time: f64,
    pub created_at: DateTime<Utc>,
}

pub struct DatabaseManager {
    pool: SqlitePool,
}

impl DatabaseManager {
    pub async fn new(database_url: &str) -> Result<Self> {
        // Create database if it doesn't exist
        if !Sqlite::database_exists(database_url).await.unwrap_or(false) {
            Sqlite::create_database(database_url).await?;
        }

        let pool = SqlitePool::connect(database_url).await?;
        
        // Run migrations
        sqlx::migrate!("./migrations").run(&pool).await?;
        
        Ok(Self { pool })
    }

    pub async fn create_user(&self, username: &str, email: Option<&str>, password_hash: &str, full_name: Option<&str>, role: &str) -> Result<i64> {
        let result = sqlx::query!(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
            username, email, password_hash, full_name, role
        )
        .execute(&self.pool)
        .await?;
        
        Ok(result.last_insert_rowid())
    }

    pub async fn get_user_by_username(&self, username: &str) -> Result<Option<User>> {
        let user = sqlx::query_as!(
            User,
            "SELECT id, username, email, full_name, role, created_at FROM users WHERE username = ?",
            username
        )
        .fetch_optional(&self.pool)
        .await?;
        
        Ok(user)
    }

    pub async fn create_inspection_target(&self, target: &InspectionTarget) -> Result<()> {
        sqlx::query!(
            "INSERT INTO inspection_targets (id, product_id, batch_id, qr_code) VALUES (?, ?, ?, ?)",
            target.id, target.product_id, target.batch_id, target.qr_code
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn create_inspection_session(&self, session: &InspectionSession) -> Result<()> {
        sqlx::query!(
            "INSERT INTO inspection_sessions (id, target_id, user_id, status) VALUES (?, ?, ?, ?)",
            session.id, session.target_id, session.user_id, session.status
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn save_inspection_image(&self, image: &InspectionImage) -> Result<()> {
        sqlx::query!(
            "INSERT INTO inspection_images (id, session_id, file_path, image_type, file_size) VALUES (?, ?, ?, ?, ?)",
            image.id, image.session_id, image.file_path, image.image_type, image.file_size
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn save_ai_result(&self, result: &AIInspectionResult) -> Result<()> {
        sqlx::query!(
            "INSERT INTO ai_inspection_results (id, session_id, pipeline_version, overall_result, confidence, processing_time, detailed_results) VALUES (?, ?, ?, ?, ?, ?, ?)",
            result.id, result.session_id, result.pipeline_version, result.overall_result, result.confidence, result.processing_time, result.detailed_results
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn save_human_verification(&self, result: &HumanVerificationResult) -> Result<()> {
        sqlx::query!(
            "INSERT INTO human_verification_results (id, session_id, user_id, final_result, notes, verification_time) VALUES (?, ?, ?, ?, ?, ?)",
            result.id, result.session_id, result.user_id, result.final_result, result.notes, result.verification_time
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn get_inspection_history(&self, limit: Option<i32>) -> Result<Vec<InspectionSession>> {
        let limit = limit.unwrap_or(50).min(100);
        
        let sessions = sqlx::query_as!(
            InspectionSession,
            "SELECT id, target_id, user_id, status, started_at, completed_at FROM inspection_sessions ORDER BY started_at DESC LIMIT ?",
            limit
        )
        .fetch_all(&self.pool)
        .await?;
        
        Ok(sessions)
    }

    pub async fn get_config_value(&self, key: &str) -> Result<Option<String>> {
        let result = sqlx::query!(
            "SELECT value FROM system_config WHERE key = ?",
            key
        )
        .fetch_optional(&self.pool)
        .await?;
        
        Ok(result.map(|r| r.value))
    }

    pub async fn set_config_value(&self, key: &str, value: &str) -> Result<()> {
        sqlx::query!(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
            key, value
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }
}