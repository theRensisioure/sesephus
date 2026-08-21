use axum::{
    extract::State,
    routing::get,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;
use tower_http::cors::CorsLayer;
use futures::StreamExt;

// --- Data Models ---

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardState {
    pub agents: HashMap<String, AgentStatus>,
    pub task_queue: Vec<TaskEntry>,
    pub artifacts: Vec<ArtifactEntry>,
    pub last_updated: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStatus {
    pub name: String,
    pub node: String,
    pub status: AgentState,
    pub current_task: Option<String>,
    pub resource_load: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AgentState {
    Idle,
    Busy,
    Error,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskEntry {
    pub id: Uuid,
    pub domain: String,
    pub status: String,
    pub payload_summary: String,
    pub created_at: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactEntry {
    pub id: Uuid,
    pub type_name: String,
    pub source_node: String,
    pub file_path: String,
    pub size_bytes: u64,
    pub created_at: u64,
}

// --- App State ---

#[derive(Clone)]
pub struct AppState {
    pub state: Arc<RwLock<DashboardState>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            state: Arc::new(RwLock::new(DashboardState {
                agents: HashMap::new(),
                task_queue: Vec::new(),
                artifacts: Vec::new(),
                last_updated: 0,
            })),
        }
    }
}

// --- Handlers ---

async fn get_dashboard_state(State(app_state): State<AppState>) -> Json<DashboardState> {
    let state = app_state.state.read().await;
    Json(state.clone())
}

// --- Main ---

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let app_state = AppState::new();

    // 1. Initialize NATS Connection
    // Assuming NATS is running locally for NODE_01
    let nats_url = std::env::var("NATS_URL").unwrap_or_else(|_| "127.0.0.1:4222".into());
    let nc = async_nats::connect(nats_url).await?;
    println!("[AETHER] Connected to NATS at {}", nc.address());

    // 2. Spawn NATS Subscriber Task
    let state_for_nats = app_state.state.clone();
    let mut subscriber = nc.subscribe("aether.monitoring.>").await?;
    
    tokio::spawn(async move {
        while let Some(message) = subscriber.next().await {
            let subject = message.subject.clone();
            println!("[AETHER] Received message on subject: {}", subject);
            
            // Basic logic: Update agent status if subject matches
            if subject == "aether.monitoring.agent_status" {
                if let Ok(update) = serde_json::from_slice::<AgentStatus>(&message.payload) {
                    let mut state = state_for_nats.write().await;
                    state.agents.insert(update.name.clone(), update);
                    state.last_updated = chrono::Utc::now().timestamp() as u64;
                    println!("[AETHER] Updated agent status.");
                }
            }
        }
    });

    // 3. Build Axum Router
    let app = Router::new()
        .route("/api/dashboard", get(get_dashboard_state))
        .layer(CorsLayer::permissive())
        .with_state(app_state);

    // 4. Start Server
    let addr = "0.0.0.0:3000";
    let listener = tokio::net::TcpListener::bind(addr).await?;
    println!("[AETHER] Dashboard Server running on http://{}", addr);

    axum::serve(listener, app).await?;

    Ok(())
}
