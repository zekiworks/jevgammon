//! HTTP with retries for transient failures (network, 429, 5xx, overload).

use std::time::Duration;

use reqwest::{RequestBuilder, StatusCode};

use crate::auth::snippet;

/// With backoff doubling from 1 s up to `MAX_BACKOFF`, about 4 minutes of retrying.
const MAX_ATTEMPTS: u32 = 10;
const MAX_BACKOFF: Duration = Duration::from_secs(60);

#[derive(Debug)]
pub enum CallError {
    /// 401/403: the credential was rejected; a refresh may help.
    Auth(String),
    Fatal(anyhow::Error),
}

impl From<anyhow::Error> for CallError {
    fn from(error: anyhow::Error) -> Self {
        CallError::Fatal(error)
    }
}

impl CallError {
    pub fn into_anyhow(self) -> anyhow::Error {
        match self {
            CallError::Auth(message) => anyhow::anyhow!("credential rejected: {message}"),
            CallError::Fatal(error) => error,
        }
    }
}

pub fn client() -> reqwest::Client {
    reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(20))
        .timeout(Duration::from_secs(600))
        .build()
        .expect("HTTP client")
}

fn retryable(status: StatusCode) -> bool {
    matches!(
        status.as_u16(),
        408 | 409 | 425 | 429 | 500 | 502 | 503 | 504 | 529
    )
}

/// Sends the request built by `make`, retrying transient failures with exponential
/// backoff; `Retry-After` can lengthen a wait but never shorten it (Liquid answers every
/// 429 with `Retry-After: 1`). Returns the body of a successful response.
pub async fn send(make: impl Fn() -> RequestBuilder) -> Result<String, CallError> {
    let mut backoff = Duration::from_secs(1);
    let mut attempt = 1;
    loop {
        let failure = match make().send().await {
            Ok(response) => {
                let status = response.status();
                let retry_after = response
                    .headers()
                    .get(reqwest::header::RETRY_AFTER)
                    .and_then(|v| v.to_str().ok())
                    .and_then(|v| v.trim().parse::<u64>().ok())
                    .map(Duration::from_secs);
                let body = response.text().await.unwrap_or_default();
                if status.is_success() {
                    return Ok(body);
                }
                if matches!(status, StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN) {
                    return Err(CallError::Auth(format!("{status}: {}", snippet(&body))));
                }
                if !retryable(status) {
                    return Err(CallError::Fatal(anyhow::anyhow!(
                        "{status}: {}",
                        snippet(&body)
                    )));
                }
                if let Some(wait) = retry_after {
                    backoff = backoff.max(wait).min(MAX_BACKOFF);
                }
                format!("{status}: {}", snippet(&body))
            }
            Err(error) => format!("{error}"),
        };
        if attempt >= MAX_ATTEMPTS {
            return Err(CallError::Fatal(anyhow::anyhow!(
                "gave up after {attempt} attempts: {failure}"
            )));
        }
        tokio::time::sleep(backoff).await;
        backoff = (backoff * 2).min(MAX_BACKOFF);
        attempt += 1;
    }
}
