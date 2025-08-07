use sqlx::{SqlitePool, migrate::MigrateDatabase, Sqlite};
use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct User {
    pub id: i64,
    pub username: String,
    pub email: Option<String>,
    pub full_name: Option<String>,
    pub role: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
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
    pub user_id: i64,
    pub status: String,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct InspectionImage {
    pub id: String,
    pub session_id: String,
    pub file_path: String,
    pub image_type: String,
    pub file_size: Option<i64>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
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

#[derive(Debug, Serialize, Deserialize)]
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
            println!("Creating database {}", database_url);
            match Sqlite::create_database(database_url).await {
                Ok(_) => println!("Create db success"),
                Err(error) => panic!("error: {}", error),
            }
        } else {
            println!("Database already exists");
        }

        let pool = SqlitePool::connect(database_url).await?;
        
        let manager = DatabaseManager { pool };
        manager.run_migrations().await?;
        
        Ok(manager)
    }

    async fn run_migrations(&self) -> Result<()> {
        // Run migrations
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'operator',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS inspection_targets (
                id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                qr_code TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS inspection_sessions (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                FOREIGN KEY (target_id) REFERENCES inspection_targets (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS inspection_images (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                image_type TEXT NOT NULL,
                file_size INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES inspection_sessions (id)
            )
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS ai_inspection_results (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                pipeline_version TEXT,
                overall_result TEXT NOT NULL,
                confidence REAL NOT NULL,
                processing_time REAL NOT NULL,
                detailed_results TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES inspection_sessions (id)
            )
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS human_verification_results (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                final_result TEXT NOT NULL,
                notes TEXT,
                verification_time REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES inspection_sessions (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            "#,
        )
        .execute(&self.pool)
        .await?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            "#,
        )
        .execute(&self.pool)
        .await?;

        Ok(())
    }

    pub async fn create_user(&self, username: &str, email: Option<&str>, password_hash: &str, full_name: Option<&str>, role: &str) -> Result<i64> {
        let result = sqlx::query(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)"
        )
        .bind(username)
        .bind(email)
        .bind(password_hash)
        .bind(full_name)
        .bind(role)
        .execute(&self.pool)
        .await?;
        
        Ok(result.last_insert_rowid())
    }

    pub async fn get_user_by_username(&self, username: &str) -> Result<Option<User>> {
        let user = sqlx::query_as::<_, User>(
            "SELECT id, username, email, full_name, role, created_at FROM users WHERE username = ?"
        )
        .bind(username)
        .fetch_optional(&self.pool)
        .await?;
        
        Ok(user)
    }

    pub async fn save_inspection_target(&self, target: &InspectionTarget) -> Result<()> {
        sqlx::query(
            "INSERT INTO inspection_targets (id, product_id, batch_id, qr_code) VALUES (?, ?, ?, ?)"
        )
        .bind(&target.id)
        .bind(&target.product_id)
        .bind(&target.batch_id)
        .bind(&target.qr_code)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn save_inspection_session(&self, session: &InspectionSession) -> Result<()> {
        sqlx::query(
            "INSERT INTO inspection_sessions (id, target_id, user_id, status) VALUES (?, ?, ?, ?)"
        )
        .bind(&session.id)
        .bind(&session.target_id)
        .bind(session.user_id)
        .bind(&session.status)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn save_inspection_image(&self, image: &InspectionImage) -> Result<()> {
        sqlx::query(
            "INSERT INTO inspection_images (id, session_id, file_path, image_type, file_size) VALUES (?, ?, ?, ?, ?)"
        )
        .bind(&image.id)
        .bind(&image.session_id)
        .bind(&image.file_path)
        .bind(&image.image_type)
        .bind(image.file_size)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn save_ai_result(&self, result: &AIInspectionResult) -> Result<()> {
        sqlx::query(
            "INSERT INTO ai_inspection_results (id, session_id, pipeline_version, overall_result, confidence, processing_time, detailed_results) VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        .bind(&result.id)
        .bind(&result.session_id)
        .bind(&result.pipeline_version)
        .bind(&result.overall_result)
        .bind(result.confidence)
        .bind(result.processing_time)
        .bind(&result.detailed_results)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn save_human_verification(&self, result: &HumanVerificationResult) -> Result<()> {
        sqlx::query(
            "INSERT INTO human_verification_results (id, session_id, user_id, final_result, notes, verification_time) VALUES (?, ?, ?, ?, ?, ?)"
        )
        .bind(&result.id)
        .bind(&result.session_id)
        .bind(result.user_id)
        .bind(&result.final_result)
        .bind(&result.notes)
        .bind(result.verification_time)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }

    pub async fn get_inspection_history(&self, limit: Option<i32>) -> Result<Vec<InspectionSession>> {
        let limit = limit.unwrap_or(50);
        let sessions = sqlx::query_as::<_, InspectionSession>(
            "SELECT id, target_id, user_id, status, started_at, completed_at FROM inspection_sessions ORDER BY started_at DESC LIMIT ?"
        )
        .bind(limit)
        .fetch_all(&self.pool)
        .await?;
        
        Ok(sessions)
    }

    pub async fn get_config_value(&self, key: &str) -> Result<Option<String>> {
        let result = sqlx::query_scalar::<_, String>(
            "SELECT value FROM system_config WHERE key = ?"
        )
        .bind(key)
        .fetch_optional(&self.pool)
        .await?;
        
        Ok(result)
    }

    pub async fn set_config_value(&self, key: &str, value: &str) -> Result<()> {
        sqlx::query(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)"
        )
        .bind(key)
        .bind(value)
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }
}
