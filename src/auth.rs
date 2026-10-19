//! Subscription (OAuth) and API-key credentials.
//!
//! OpenAI and Anthropic subscriptions are read from the stores other local tools
//! already maintain: the qfork/Glyph credential envelopes, the Codex CLI
//! (`~/.codex/auth.json`), and Claude Code (`~/.claude/.credentials.json`). The
//! freshest token wins. Refreshing rotates the refresh token, so refreshed tokens
//! are written back to the store they came from; otherwise that tool would be
//! logged out.
//!
//! The Google Antigravity login is OMP's (`~/.omp/agent/agent.db`, opened read-only and
//! never written). Google does not rotate the refresh token, so an expired access token
//! is refreshed here with Antigravity's OAuth client (`ANTIGRAVITY_OAUTH_CLIENT_ID`,
//! `ANTIGRAVITY_OAUTH_CLIENT_SECRET`) and cached in jevgammon's own state
//! (`~/.local/state/jevgammon/google-antigravity.json`); the freshest of the two wins.

use std::fs::{self, File, OpenOptions};
use std::io::Write as _;
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, anyhow, bail};
use base64::Engine as _;
use fs2::FileExt;
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};

const REFRESH_SKEW_MS: i64 = 5 * 60 * 1000;

const OPENAI_CLIENT_ID: &str = "app_EMoamEEZ73f0CkXaXp7hrann";
const OPENAI_TOKEN_URL: &str = "https://auth.openai.com/oauth/token";
const ANTHROPIC_CLIENT_ID: &str = "9d1c250a-e61b-44d9-88ed-5944d1962f5e";
const ANTHROPIC_TOKEN_URL: &str = "https://platform.claude.com/v1/oauth/token";
const GOOGLE_TOKEN_URL: &str = "https://oauth2.googleapis.com/token";
/// Environment variables holding Antigravity's OAuth client (the one OMP uses for its
/// Antigravity login), needed only to refresh an expired access token. Not in the source:
/// GitHub push protection rejects Google OAuth client credentials.
const ANTIGRAVITY_CLIENT_ID_ENV: &str = "ANTIGRAVITY_OAUTH_CLIENT_ID";
const ANTIGRAVITY_CLIENT_SECRET_ENV: &str = "ANTIGRAVITY_OAUTH_CLIENT_SECRET";
/// OMP's provider id, in its credential table and in the cache file name.
const ANTIGRAVITY: &str = "google-antigravity";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Subscription {
    OpenAi,
    Anthropic,
    /// Google Antigravity (Gemini through Cloud Code Assist), OMP's login.
    Antigravity,
}

impl Subscription {
    fn qfork_name(self) -> &'static str {
        match self {
            Subscription::OpenAi => "openai",
            Subscription::Anthropic => "anthropic",
            Subscription::Antigravity => ANTIGRAVITY,
        }
    }

    fn label(self) -> &'static str {
        match self {
            Subscription::OpenAi => "OpenAI (ChatGPT)",
            Subscription::Anthropic => "Anthropic (Claude)",
            Subscription::Antigravity => "Google Antigravity",
        }
    }
}

#[derive(Clone, Debug)]
enum Source {
    Qfork(PathBuf),
    Codex(PathBuf),
    Claude(PathBuf),
    /// OMP's credential database: read-only.
    Omp(PathBuf),
    /// jevgammon's own cache of refreshed Antigravity tokens.
    Cache(PathBuf),
}

impl Source {
    fn describe(&self) -> String {
        match self {
            Source::Qfork(root) => format!("qfork store {}", root.display()),
            Source::Codex(path)
            | Source::Claude(path)
            | Source::Omp(path)
            | Source::Cache(path) => path.display().to_string(),
        }
    }
}

#[derive(Clone)]
pub struct Token {
    pub access: String,
    /// ChatGPT account id (OpenAI only).
    pub account_id: Option<String>,
    /// Cloud Code Assist project (Antigravity only).
    pub project: Option<String>,
    refresh: String,
    expires_at_ms: i64,
    source: Source,
}

impl Token {
    fn needs_refresh(&self) -> bool {
        self.expires_at_ms <= now_ms() + REFRESH_SKEW_MS
    }
}

pub struct Credentials {
    provider: Subscription,
    qfork_root: PathBuf,
    http: reqwest::Client,
    current: tokio::sync::Mutex<Option<Token>>,
}

impl Credentials {
    pub fn new(provider: Subscription, qfork_root: PathBuf, http: reqwest::Client) -> Self {
        Credentials {
            provider,
            qfork_root,
            http,
            current: tokio::sync::Mutex::new(None),
        }
    }

    /// A usable access token, refreshing it when it is about to expire.
    pub async fn token(&self) -> Result<Token> {
        let mut current = self.current.lock().await;
        let token = match current.take() {
            Some(token) => token,
            None => self.best_stored()?,
        };
        let token = if token.needs_refresh() {
            self.refresh(token).await?
        } else {
            token
        };
        *current = Some(token.clone());
        Ok(token)
    }

    /// Called after the provider rejected `rejected`: refresh unless another caller
    /// already replaced it.
    pub async fn refresh_after_rejection(&self, rejected: &str) -> Result<Token> {
        let mut current = self.current.lock().await;
        let token = match current.take() {
            Some(token) if token.access != rejected => token,
            Some(token) => self.refresh(token).await?,
            None => self.best_stored()?,
        };
        *current = Some(token.clone());
        Ok(token)
    }

    fn best_stored(&self) -> Result<Token> {
        let mut candidates = Vec::new();
        let mut looked = Vec::new();
        let hint = match self.provider {
            Subscription::OpenAi | Subscription::Anthropic => {
                let qfork = self.qfork_root.clone();
                looked.push(Source::Qfork(qfork.clone()).describe());
                candidates.extend(read_qfork(self.provider, &qfork)?);
                if self.provider == Subscription::OpenAi {
                    let path = codex_auth_path();
                    looked.push(path.display().to_string());
                    candidates.extend(read_codex(&path)?);
                } else {
                    let path = claude_credentials_path();
                    looked.push(path.display().to_string());
                    candidates.extend(read_claude(&path)?);
                }
                "log in with qfork, `codex login`, or `claude`"
            }
            Subscription::Antigravity => {
                looked.push(omp_db_path().display().to_string());
                looked.push(antigravity_cache_path().display().to_string());
                candidates.extend(stored_antigravity()?);
                "log in to Google Antigravity with omp (/login)"
            }
        };
        candidates
            .into_iter()
            .max_by_key(|t| t.expires_at_ms)
            .ok_or_else(|| {
                anyhow!(
                    "no {} subscription login found (looked in: {}); {hint}",
                    self.provider.label(),
                    looked.join(", ")
                )
            })
    }

    async fn refresh(&self, stale: Token) -> Result<Token> {
        let _guard = match &stale.source {
            Source::Qfork(root) => Some(
                lock(
                    root,
                    &format!("{}.oauth-refresh", self.provider.qfork_name()),
                )
                .await?,
            ),
            Source::Omp(_) | Source::Cache(_) => Some(
                lock(
                    &jevgammon_state_dir(),
                    &format!("{ANTIGRAVITY}.oauth-refresh"),
                )
                .await?,
            ),
            _ => None,
        };
        // Another process may have refreshed the store since we read it.
        let reread = match &stale.source {
            Source::Qfork(root) => read_qfork(self.provider, root)?,
            Source::Codex(path) => read_codex(path)?,
            Source::Claude(path) => read_claude(path)?,
            Source::Omp(_) | Source::Cache(_) => stored_antigravity()?
                .into_iter()
                .max_by_key(|t| t.expires_at_ms),
        };
        if let Some(fresh) = reread.filter(|t| t.access != stale.access && !t.needs_refresh()) {
            return Ok(fresh);
        }
        let response = self
            .request_refresh(&stale.refresh)
            .await
            .with_context(|| {
                format!(
                    "refreshing {} login from {}",
                    self.provider.label(),
                    stale.source.describe()
                )
            })?;
        let access = string_field(&response, "access_token")?;
        let refresh = response
            .get("refresh_token")
            .and_then(Value::as_str)
            .map(str::to_owned)
            .unwrap_or_else(|| stale.refresh.clone());
        let id_token = response.get("id_token").and_then(Value::as_str);
        let account_id = id_token
            .and_then(openai_account_id)
            .or_else(|| stale.account_id.clone());
        let expires_at_ms = jwt_exp_ms(&access)
            .or_else(|| {
                response
                    .get("expires_in")
                    .and_then(Value::as_i64)
                    .map(|s| now_ms() + s * 1000)
            })
            .unwrap_or_else(|| now_ms() + 3_600_000);
        let token = Token {
            access,
            account_id,
            project: stale.project.clone(),
            refresh,
            expires_at_ms,
            source: stale.source.clone(),
        };
        match &stale.source {
            Source::Qfork(root) => write_qfork(self.provider, root, &token, id_token).await?,
            Source::Codex(path) => write_codex(path, &token, id_token)?,
            Source::Claude(path) => write_claude(path, &token)?,
            // Never OMP's database: the refreshed token goes to jevgammon's cache.
            Source::Omp(_) | Source::Cache(_) => {
                let path = antigravity_cache_path();
                write_cache(&path, &token)?;
                return Ok(Token {
                    source: Source::Cache(path),
                    ..token
                });
            }
        }
        Ok(token)
    }

    async fn request_refresh(&self, refresh_token: &str) -> Result<Value> {
        let request = match self.provider {
            Subscription::OpenAi => self.http.post(OPENAI_TOKEN_URL).form(&[
                ("grant_type", "refresh_token"),
                ("client_id", OPENAI_CLIENT_ID),
                ("refresh_token", refresh_token),
            ]),
            Subscription::Anthropic => self.http.post(ANTHROPIC_TOKEN_URL).json(&json!({
                "grant_type": "refresh_token",
                "client_id": ANTHROPIC_CLIENT_ID,
                "refresh_token": refresh_token,
            })),
            Subscription::Antigravity => {
                let client_id = required_env(ANTIGRAVITY_CLIENT_ID_ENV)?;
                let client_secret = required_env(ANTIGRAVITY_CLIENT_SECRET_ENV)?;
                self.http.post(GOOGLE_TOKEN_URL).form(&[
                    ("grant_type", "refresh_token"),
                    ("client_id", client_id.as_str()),
                    ("client_secret", client_secret.as_str()),
                    ("refresh_token", refresh_token),
                ])
            }
        };
        let response = request.send().await?;
        let status = response.status();
        let body = response.text().await?;
        if !status.is_success() {
            bail!("token endpoint answered {status}: {}", snippet(&body));
        }
        Ok(serde_json::from_str(&body)?)
    }
}

/// Gemini API key: `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or the qfork Gemini key.
pub fn gemini_api_key(qfork_root: &Path) -> Result<String> {
    for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"] {
        if let Ok(key) = std::env::var(var)
            && !key.is_empty()
        {
            return Ok(key);
        }
    }
    let path = qfork_root.join("credentials/gemini.json");
    if let Some(revision) = qfork_active_revision(&path)?
        && revision.get("authentication").is_none()
        && let Some(secret) = revision.get("secret").and_then(Value::as_str)
    {
        return Ok(secret.to_owned());
    }
    bail!(
        "no Gemini API key: set GEMINI_API_KEY (also checked GOOGLE_API_KEY and {})",
        path.display()
    )
}

pub fn default_qfork_root() -> PathBuf {
    dirs::home_dir().unwrap_or_default().join(".qfork/glyph")
}

fn codex_auth_path() -> PathBuf {
    std::env::var_os("CODEX_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| dirs::home_dir().unwrap_or_default().join(".codex"))
        .join("auth.json")
}

fn claude_credentials_path() -> PathBuf {
    std::env::var_os("CLAUDE_CONFIG_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| dirs::home_dir().unwrap_or_default().join(".claude"))
        .join(".credentials.json")
}

/// OMP's credential database.
fn omp_db_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_default()
        .join(".omp/agent/agent.db")
}

fn jevgammon_state_dir() -> PathBuf {
    dirs::state_dir()
        .unwrap_or_else(|| dirs::home_dir().unwrap_or_default().join(".local/state"))
        .join("jevgammon")
}

fn antigravity_cache_path() -> PathBuf {
    jevgammon_state_dir().join(format!("{ANTIGRAVITY}.json"))
}

/// The Antigravity tokens in OMP's database and in jevgammon's cache.
fn stored_antigravity() -> Result<Vec<Token>> {
    let mut tokens = read_omp(&omp_db_path())?;
    tokens.extend(read_cache(&antigravity_cache_path())?);
    Ok(tokens)
}

/// OMP's enabled `google-antigravity` logins, read-only.
fn read_omp(path: &Path) -> Result<Vec<Token>> {
    use rusqlite::{Connection, OpenFlags};
    if !path.exists() {
        return Ok(Vec::new());
    }
    let connection = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
    .with_context(|| format!("opening {} read-only", path.display()))?;
    connection.busy_timeout(std::time::Duration::from_secs(5))?;
    let mut statement = connection.prepare(
        "SELECT data FROM auth_credentials WHERE provider = ?1 AND disabled_cause IS NULL",
    )?;
    let rows = statement
        .query_map([ANTIGRAVITY], |row| row.get::<_, String>(0))?
        .collect::<rusqlite::Result<Vec<String>>>()
        .with_context(|| format!("reading {}", path.display()))?;
    Ok(rows
        .iter()
        .filter_map(|data| serde_json::from_str::<Value>(data).ok())
        .filter_map(|data| antigravity_token(&data, Source::Omp(path.to_owned())))
        .collect())
}

fn read_cache(path: &Path) -> Result<Option<Token>> {
    Ok(read_json(path)?.and_then(|data| antigravity_token(&data, Source::Cache(path.to_owned()))))
}

/// A token from OMP's credential JSON: `access`, `refresh`, `expires` (ms), `projectId`.
fn antigravity_token(data: &Value, source: Source) -> Option<Token> {
    Some(Token {
        access: data.get("access")?.as_str()?.to_owned(),
        account_id: None,
        project: Some(data.get("projectId")?.as_str()?.to_owned()),
        refresh: data.get("refresh")?.as_str()?.to_owned(),
        expires_at_ms: data.get("expires").and_then(Value::as_i64).unwrap_or(0),
        source,
    })
}

/// Caches a refreshed Antigravity token in OMP's credential shape.
fn write_cache(path: &Path, token: &Token) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    write_atomic(
        path,
        &json!({
            "access": token.access,
            "refresh": token.refresh,
            "expires": token.expires_at_ms,
            "projectId": token.project,
        }),
    )
}

fn required_env(name: &str) -> Result<String> {
    std::env::var(name)
        .ok()
        .filter(|value| !value.is_empty())
        .ok_or_else(|| anyhow!("set {name} (Antigravity's OAuth client, as OMP uses)"))
}

fn read_json(path: &Path) -> Result<Option<Value>> {
    match fs::read(path) {
        Ok(bytes) => Ok(Some(
            serde_json::from_slice(&bytes)
                .with_context(|| format!("parsing {}", path.display()))?,
        )),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error).with_context(|| format!("reading {}", path.display())),
    }
}

fn qfork_active_revision(path: &Path) -> Result<Option<Value>> {
    let Some(envelope) = read_json(path)? else {
        return Ok(None);
    };
    let active = envelope
        .get("activeRevision")
        .and_then(Value::as_str)
        .unwrap_or_default();
    Ok(envelope
        .get("revisions")
        .and_then(|r| r.get(active))
        .cloned())
}

fn read_qfork(provider: Subscription, root: &Path) -> Result<Option<Token>> {
    let path = root.join(format!("credentials/{}.json", provider.qfork_name()));
    let Some(revision) = qfork_active_revision(&path)? else {
        return Ok(None);
    };
    if revision.get("authentication").and_then(Value::as_str) != Some("o_auth") {
        return Ok(None);
    }
    let (Some(access), Some(refresh)) = (
        revision.get("secret").and_then(Value::as_str),
        revision.get("refreshToken").and_then(Value::as_str),
    ) else {
        return Ok(None);
    };
    let expires_at_ms = revision
        .get("expiresAtUs")
        .and_then(Value::as_i64)
        .unwrap_or(0)
        / 1000;
    let account_id = revision
        .pointer("/metadata/account_id")
        .and_then(Value::as_str)
        .map(str::to_owned);
    Ok(Some(Token {
        access: access.to_owned(),
        account_id,
        project: None,
        refresh: refresh.to_owned(),
        expires_at_ms,
        source: Source::Qfork(root.to_owned()),
    }))
}

fn read_codex(path: &Path) -> Result<Option<Token>> {
    let Some(auth) = read_json(path)? else {
        return Ok(None);
    };
    let Some(tokens) = auth.get("tokens").filter(|t| t.is_object()) else {
        return Ok(None);
    };
    let (Some(access), Some(refresh)) = (
        tokens.get("access_token").and_then(Value::as_str),
        tokens.get("refresh_token").and_then(Value::as_str),
    ) else {
        return Ok(None);
    };
    let account_id = tokens
        .get("account_id")
        .and_then(Value::as_str)
        .map(str::to_owned)
        .or_else(|| {
            tokens
                .get("id_token")
                .and_then(Value::as_str)
                .and_then(openai_account_id)
        });
    Ok(Some(Token {
        access: access.to_owned(),
        account_id,
        project: None,
        refresh: refresh.to_owned(),
        expires_at_ms: jwt_exp_ms(access).unwrap_or(0),
        source: Source::Codex(path.to_owned()),
    }))
}

fn read_claude(path: &Path) -> Result<Option<Token>> {
    let Some(file) = read_json(path)? else {
        return Ok(None);
    };
    let Some(oauth) = file.get("claudeAiOauth") else {
        return Ok(None);
    };
    let (Some(access), Some(refresh)) = (
        oauth.get("accessToken").and_then(Value::as_str),
        oauth.get("refreshToken").and_then(Value::as_str),
    ) else {
        return Ok(None);
    };
    Ok(Some(Token {
        access: access.to_owned(),
        account_id: None,
        project: None,
        refresh: refresh.to_owned(),
        expires_at_ms: oauth.get("expiresAt").and_then(Value::as_i64).unwrap_or(0),
        source: Source::Claude(path.to_owned()),
    }))
}

/// Adds the refreshed token as the new active revision of a qfork envelope, under the
/// same per-provider lock qfork uses.
async fn write_qfork(
    provider: Subscription,
    root: &Path,
    token: &Token,
    id_token: Option<&str>,
) -> Result<()> {
    let _guard = lock(root, provider.qfork_name()).await?;
    let path = root.join(format!("credentials/{}.json", provider.qfork_name()));
    let mut envelope =
        read_json(&path)?.ok_or_else(|| anyhow!("{} disappeared", path.display()))?;
    let active = envelope
        .get("activeRevision")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned();
    let previous = envelope
        .get("revisions")
        .and_then(|r| r.get(&active))
        .cloned()
        .unwrap_or(Value::Null);
    let mut metadata = previous
        .get("metadata")
        .and_then(Value::as_object)
        .cloned()
        .unwrap_or_default();
    if let Some(id_token) = id_token {
        metadata.insert("id_token".into(), id_token.into());
    }
    if let Some(account_id) = &token.account_id {
        metadata.insert("account_id".into(), account_id.clone().into());
    }
    let mut revision = Map::new();
    revision.insert("createdAtUs".into(), (now_ms() * 1000).into());
    revision.insert(
        "profileId".into(),
        previous
            .get("profileId")
            .cloned()
            .unwrap_or_else(|| "default".into()),
    );
    revision.insert(
        "fingerprint".into(),
        hex::encode(Sha256::digest(token.access.as_bytes())).into(),
    );
    revision.insert("secret".into(), token.access.clone().into());
    revision.insert("authentication".into(), "o_auth".into());
    revision.insert("refreshToken".into(), token.refresh.clone().into());
    revision.insert("expiresAtUs".into(), (token.expires_at_ms * 1000).into());
    if !metadata.is_empty() {
        revision.insert("metadata".into(), Value::Object(metadata));
    }
    let id = uuid::Uuid::new_v4().to_string();
    envelope
        .get_mut("revisions")
        .and_then(Value::as_object_mut)
        .ok_or_else(|| anyhow!("{} has no revisions map", path.display()))?
        .insert(id.clone(), Value::Object(revision));
    envelope["activeRevision"] = id.into();
    write_atomic(&path, &envelope)
}

fn write_codex(path: &Path, token: &Token, id_token: Option<&str>) -> Result<()> {
    let mut auth = read_json(path)?.ok_or_else(|| anyhow!("{} disappeared", path.display()))?;
    let tokens = auth
        .get_mut("tokens")
        .and_then(Value::as_object_mut)
        .ok_or_else(|| anyhow!("{} has no tokens", path.display()))?;
    tokens.insert("access_token".into(), token.access.clone().into());
    tokens.insert("refresh_token".into(), token.refresh.clone().into());
    if let Some(id_token) = id_token {
        tokens.insert("id_token".into(), id_token.into());
    }
    if let Some(account_id) = &token.account_id {
        tokens.insert("account_id".into(), account_id.clone().into());
    }
    auth["last_refresh"] = chrono::Utc::now().to_rfc3339().into();
    write_atomic(path, &auth)
}

fn write_claude(path: &Path, token: &Token) -> Result<()> {
    let mut file = read_json(path)?.ok_or_else(|| anyhow!("{} disappeared", path.display()))?;
    let oauth = file
        .get_mut("claudeAiOauth")
        .and_then(Value::as_object_mut)
        .ok_or_else(|| anyhow!("{} has no claudeAiOauth", path.display()))?;
    oauth.insert("accessToken".into(), token.access.clone().into());
    oauth.insert("refreshToken".into(), token.refresh.clone().into());
    oauth.insert("expiresAt".into(), token.expires_at_ms.into());
    write_atomic(path, &file)
}

fn write_atomic(path: &Path, value: &Value) -> Result<()> {
    let temporary = path.with_extension(format!("tmp-{}", uuid::Uuid::new_v4().simple()));
    let result = (|| -> Result<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&temporary)?;
        file.write_all(&serde_json::to_vec(value)?)?;
        file.sync_all()?;
        fs::set_permissions(&temporary, fs::Permissions::from_mode(0o600))?;
        fs::rename(&temporary, path)?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.with_context(|| format!("writing {}", path.display()))
}

/// Exclusive `flock` on `<root>/locks/<name>.lock`, the convention qfork uses.
async fn lock(root: &Path, name: &str) -> Result<File> {
    let path = root.join("locks").join(format!("{name}.lock"));
    tokio::task::spawn_blocking(move || -> Result<File> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let file = OpenOptions::new()
            .create(true)
            .truncate(false)
            .write(true)
            .mode(0o600)
            .open(&path)?;
        file.lock_exclusive()?;
        Ok(file)
    })
    .await?
}

fn jwt_claims(jwt: &str) -> Option<Value> {
    let payload = jwt.split('.').nth(1)?;
    let bytes = base64::engine::general_purpose::URL_SAFE_NO_PAD
        .decode(payload.trim_end_matches('='))
        .ok()?;
    serde_json::from_slice(&bytes).ok()
}

fn jwt_exp_ms(jwt: &str) -> Option<i64> {
    jwt_claims(jwt)?.get("exp")?.as_i64().map(|s| s * 1000)
}

fn openai_account_id(id_token: &str) -> Option<String> {
    let claims = jwt_claims(id_token)?;
    claims
        .get("chatgpt_account_id")
        .or_else(|| claims.pointer("/https:~1~1api.openai.com~1auth/chatgpt_account_id"))
        .and_then(Value::as_str)
        .filter(|id| !id.is_empty())
        .map(str::to_owned)
}

fn string_field(value: &Value, field: &str) -> Result<String> {
    value
        .get(field)
        .and_then(Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| anyhow!("token response lacks {field}"))
}

fn now_ms() -> i64 {
    chrono::Utc::now().timestamp_millis()
}

pub fn snippet(body: &str) -> String {
    let trimmed = body.trim();
    match trimmed.char_indices().nth(400) {
        Some((cut, _)) => format!("{}…", &trimmed[..cut]),
        None => trimmed.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir() -> PathBuf {
        let dir =
            std::env::temp_dir().join(format!("jevgammon-auth-{}", uuid::Uuid::new_v4().simple()));
        fs::create_dir_all(dir.join("credentials")).unwrap();
        dir
    }

    fn token(source: Source) -> Token {
        Token {
            access: "new-access".into(),
            account_id: Some("acct-1".into()),
            project: None,
            refresh: "new-refresh".into(),
            expires_at_ms: 4_000_000_000_000,
            source,
        }
    }

    #[tokio::test]
    async fn qfork_refresh_becomes_active_revision_and_keeps_history() {
        let root = temp_dir();
        let path = root.join("credentials/openai.json");
        let original = json!({
            "version": 1,
            "provider": "openai",
            "activeRevision": "r1",
            "revisions": {"r1": {
                "createdAtUs": 1, "profileId": "work", "fingerprint": "f", "secret": "old",
                "authentication": "o_auth", "refreshToken": "old-refresh", "expiresAtUs": 2,
                "metadata": {"account_id": "acct-1", "id_token": "old-id"}
            }},
            "requests": {"req": {"digest": "d", "revision": "r1", "profileId": "work", "fingerprint": "f"}}
        });
        fs::write(&path, original.to_string()).unwrap();

        write_qfork(
            Subscription::OpenAi,
            &root,
            &token(Source::Qfork(root.clone())),
            None,
        )
        .await
        .unwrap();

        let envelope = read_json(&path).unwrap().unwrap();
        let active = envelope["activeRevision"].as_str().unwrap();
        assert_ne!(active, "r1");
        assert_eq!(envelope["revisions"]["r1"], original["revisions"]["r1"]);
        assert_eq!(envelope["requests"], original["requests"]);
        let revision = &envelope["revisions"][active];
        assert_eq!(revision["profileId"], "work");
        assert_eq!(revision["metadata"]["id_token"], "old-id");
        assert_eq!(
            revision["fingerprint"],
            hex::encode(Sha256::digest(b"new-access"))
        );
        let reread = read_qfork(Subscription::OpenAi, &root).unwrap().unwrap();
        assert_eq!(
            (reread.access.as_str(), reread.refresh.as_str()),
            ("new-access", "new-refresh")
        );
        assert_eq!(reread.expires_at_ms, 4_000_000_000_000);
        assert_eq!(
            fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            0o600
        );
        fs::remove_dir_all(root).unwrap();
    }

    /// OMP's database is read without being changed; a refreshed token lands in the cache
    /// in the same shape and reads back with its project.
    #[test]
    fn antigravity_reads_omp_and_round_trips_the_cache() {
        let root = temp_dir();
        let db = root.join("agent.db");
        let connection = rusqlite::Connection::open(&db).unwrap();
        connection
            .execute_batch(
                "CREATE TABLE auth_credentials (id INTEGER PRIMARY KEY, provider TEXT,
                 credential_type TEXT, data TEXT, disabled_cause TEXT);
                 INSERT INTO auth_credentials (provider, credential_type, data, disabled_cause) VALUES
                 ('google-antigravity', 'oauth', '{\"access\":\"a1\",\"refresh\":\"r1\",\"expires\":5,\"projectId\":\"p\"}', NULL),
                 ('google-antigravity', 'oauth', '{\"access\":\"a0\",\"refresh\":\"r0\",\"expires\":9,\"projectId\":\"p\"}', 'revoked'),
                 ('anthropic', 'oauth', '{\"access\":\"x\",\"refresh\":\"y\",\"expires\":9}', NULL);",
            )
            .unwrap();
        drop(connection);
        let before = fs::read(&db).unwrap();
        let tokens = read_omp(&db).unwrap();
        assert_eq!(tokens.len(), 1);
        assert_eq!(
            (tokens[0].access.as_str(), tokens[0].refresh.as_str()),
            ("a1", "r1")
        );
        assert_eq!(
            (tokens[0].expires_at_ms, tokens[0].project.as_deref()),
            (5, Some("p"))
        );
        assert_eq!(fs::read(&db).unwrap(), before);
        assert!(read_omp(&root.join("missing.db")).unwrap().is_empty());

        let cache = root.join("state/google-antigravity.json");
        let refreshed = Token {
            project: Some("p".into()),
            account_id: None,
            ..token(Source::Cache(cache.clone()))
        };
        write_cache(&cache, &refreshed).unwrap();
        let reread = read_cache(&cache).unwrap().unwrap();
        assert_eq!(
            (reread.access.as_str(), reread.refresh.as_str()),
            ("new-access", "new-refresh")
        );
        assert_eq!(reread.expires_at_ms, 4_000_000_000_000);
        assert_eq!(reread.project.as_deref(), Some("p"));
        assert_eq!(
            fs::metadata(&cache).unwrap().permissions().mode() & 0o777,
            0o600
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn codex_and_claude_refresh_preserve_unrelated_fields() {
        let root = temp_dir();
        let codex = root.join("auth.json");
        fs::write(&codex, json!({"auth_mode": "chatgpt", "OPENAI_API_KEY": null,
            "tokens": {"access_token": "old", "refresh_token": "old-r", "id_token": "i", "account_id": "acct-1"}})
            .to_string()).unwrap();
        write_codex(&codex, &token(Source::Codex(codex.clone())), Some("new-id")).unwrap();
        let written = read_json(&codex).unwrap().unwrap();
        assert_eq!(written["auth_mode"], "chatgpt");
        assert!(written["OPENAI_API_KEY"].is_null());
        assert_eq!(written["tokens"]["id_token"], "new-id");
        let reread = read_codex(&codex).unwrap().unwrap();
        assert_eq!(
            (reread.access.as_str(), reread.refresh.as_str()),
            ("new-access", "new-refresh")
        );

        let claude = root.join(".credentials.json");
        fs::write(
            &claude,
            json!({"claudeAiOauth": {"accessToken": "old", "refreshToken": "old-r",
            "expiresAt": 1, "scopes": ["user:inference"], "subscriptionType": "max"}, "other": 1})
            .to_string(),
        )
        .unwrap();
        write_claude(&claude, &token(Source::Claude(claude.clone()))).unwrap();
        let written = read_json(&claude).unwrap().unwrap();
        assert_eq!(written["other"], 1);
        assert_eq!(written["claudeAiOauth"]["subscriptionType"], "max");
        let reread = read_claude(&claude).unwrap().unwrap();
        assert_eq!(reread.expires_at_ms, 4_000_000_000_000);
        fs::remove_dir_all(root).unwrap();
    }
}
