use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use chrono::{Duration, Utc};
use anyhow::{Result, anyhow};
use bcrypt::{hash, verify, DEFAULT_COST};
use crate::database::{DatabaseManager, User};

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub user_id: i64,
    pub username: String,
    pub role: String,
    pub exp: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginCredentials {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RegisterRequest {
    pub username: String,
    pub email: Option<String>,
    pub password: String,
    pub full_name: Option<String>,
    pub role: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AuthResponse {
    pub token: String,
    pub user: User,
    pub expires_at: i64,
}

pub struct AuthManager {
    secret_key: String,
}

impl AuthManager {
    pub fn new(secret_key: String) -> Self {
        Self { secret_key }
    }

    pub fn hash_password(&self, password: &str) -> Result<String> {
        let hashed = hash(password, DEFAULT_COST)?;
        Ok(hashed)
    }

    pub fn verify_password(&self, password: &str, hash: &str) -> Result<bool> {
        let is_valid = verify(password, hash)?;
        Ok(is_valid)
    }

    pub fn generate_token(&self, user: &User) -> Result<String> {
        let expiration = Utc::now() + Duration::hours(24);
        
        let claims = Claims {
            user_id: user.id,
            username: user.username.clone(),
            role: user.role.clone(),
            exp: expiration.timestamp(),
        };

        let token = encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret(self.secret_key.as_ref()),
        )?;

        Ok(token)
    }

    pub fn verify_token(&self, token: &str) -> Result<Claims> {
        let token_data = decode::<Claims>(
            token,
            &DecodingKey::from_secret(self.secret_key.as_ref()),
            &Validation::default(),
        )?;

        Ok(token_data.claims)
    }

    pub async fn authenticate(&self, db: &DatabaseManager, credentials: &LoginCredentials) -> Result<AuthResponse> {
        let user = db.get_user_by_username(&credentials.username).await?
            .ok_or_else(|| anyhow!("User not found"))?;

        // In a real implementation, get password_hash from database
        // For now, we'll create a mock verification
        let is_valid = self.verify_password(&credentials.password, "dummy_hash")?;
        
        if !is_valid {
            return Err(anyhow!("Invalid credentials"));
        }

        let token = self.generate_token(&user)?;
        let expires_at = (Utc::now() + Duration::hours(24)).timestamp();

        Ok(AuthResponse {
            token,
            user,
            expires_at,
        })
    }

    pub async fn register(&self, db: &DatabaseManager, request: &RegisterRequest) -> Result<AuthResponse> {
        let password_hash = self.hash_password(&request.password)?;
        let role = request.role.as_deref().unwrap_or("inspector");

        let _user_id = db.create_user(
            &request.username,
            request.email.as_deref(),
            &password_hash,
            request.full_name.as_deref(),
            role,
        ).await?;

        let user = db.get_user_by_username(&request.username).await?
            .ok_or_else(|| anyhow!("Failed to create user"))?;

        let token = self.generate_token(&user)?;
        let expires_at = (Utc::now() + Duration::hours(24)).timestamp();

        Ok(AuthResponse {
            token,
            user,
            expires_at,
        })
    }
}