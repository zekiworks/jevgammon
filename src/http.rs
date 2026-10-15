//! HTTP with retries for network and server errors: connection failures, 408, 429 and
//! 5xx are retried up to `RETRIES` times with backoff. The time spent on failed attempts
//! and waits is added to a `RetryTime`, which the runner keeps off the clock.

use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use reqwest::{RequestBuilder, StatusCode};

use crate::auth::snippet;

/// Retries after the first attempt.
pub const RETRIES: u32 = 3;
/// First wait; doubled after each failure (2 s, 4 s, 8 s). `Retry-After` can lengthen a
/// wait up to `MAX_BACKOFF`, never shorten it.
const FIRST_BACKOFF: Duration = Duration::from_secs(2);
const MAX_BACKOFF: Duration = Duration::from_secs(60);
/// First wait after a 429 (rate limit): 15, 30, 60 s.
const RATE_LIMIT_BACKOFF: Duration = Duration::from_secs(15);

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

/// Time spent on failed attempts and backoff waits, shared between the requests of one
/// decision and the runner's clock.
#[derive(Debug, Default)]
pub struct RetryTime(AtomicU64);

impl RetryTime {
    pub fn add(&self, spent: Duration) {
        self.0
            .fetch_add(spent.as_millis() as u64, Ordering::Relaxed);
    }

    pub fn get(&self) -> Duration {
        Duration::from_millis(self.0.load(Ordering::Relaxed))
    }
}

pub fn client() -> reqwest::Client {
    reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(20))
        .timeout(Duration::from_secs(1800))
        .build()
        .expect("HTTP client")
}

/// Network and server errors: request timeout, rate limit, and every 5xx.
pub fn retryable(status: StatusCode) -> bool {
    matches!(status.as_u16(), 408 | 429 | 500..=599)
}

/// Sends the request built by `make`, retrying network and server errors; the failed
/// attempts and the waits are added to `retry`. Returns the body of a successful response.
pub async fn send(
    make: impl Fn() -> RequestBuilder,
    retry: &RetryTime,
) -> Result<String, CallError> {
    send_with_backoff(make, retry, FIRST_BACKOFF, RATE_LIMIT_BACKOFF).await
}

async fn send_with_backoff(
    make: impl Fn() -> RequestBuilder,
    retry: &RetryTime,
    first_backoff: Duration,
    rate_limit_backoff: Duration,
) -> Result<String, CallError> {
    let mut backoff = first_backoff;
    let mut attempt = 0;
    loop {
        let started = Instant::now();
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
                if status == StatusCode::TOO_MANY_REQUESTS {
                    // Shared provider pools recover in tens of seconds, not two.
                    backoff = backoff.max(rate_limit_backoff);
                }
                if let Some(wait) = retry_after {
                    backoff = backoff.max(wait).min(MAX_BACKOFF);
                }
                format!("{status}: {}", snippet(&body))
            }
            Err(error) => format!("{error}"),
        };
        if attempt >= RETRIES {
            retry.add(started.elapsed());
            return Err(CallError::Fatal(anyhow::anyhow!(
                "gave up after {} attempts: {failure}",
                attempt + 1
            )));
        }
        tokio::time::sleep(backoff).await;
        retry.add(started.elapsed());
        backoff = (backoff * 2).min(MAX_BACKOFF);
        attempt += 1;
    }
}

#[cfg(test)]
mod tests {
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::Arc;
    use std::sync::atomic::AtomicUsize;

    use super::*;

    /// A server answering request k with `statuses[k]` (the last one repeats); returns its
    /// URL and the request count.
    fn serve(statuses: Vec<u16>) -> (String, Arc<AtomicUsize>) {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}/", listener.local_addr().unwrap());
        let count = Arc::new(AtomicUsize::new(0));
        let seen = count.clone();
        std::thread::spawn(move || {
            for stream in listener.incoming() {
                let mut stream = stream.unwrap();
                let mut buffer = [0u8; 4096];
                let _ = stream.read(&mut buffer);
                let k = seen.fetch_add(1, Ordering::SeqCst);
                let status = statuses[k.min(statuses.len() - 1)];
                let body = format!("status {status}");
                let _ = write!(
                    stream,
                    "HTTP/1.1 {status} X\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{body}",
                    body.len()
                );
            }
        });
        (url, count)
    }

    #[test]
    fn retries_only_network_and_server_errors() {
        for code in [408, 429, 500, 502, 503, 504, 529] {
            assert!(retryable(StatusCode::from_u16(code).unwrap()), "{code}");
        }
        for code in [400, 401, 403, 404, 409, 422, 425] {
            assert!(!retryable(StatusCode::from_u16(code).unwrap()), "{code}");
        }
    }

    #[tokio::test]
    async fn three_retries_then_success_or_failure_with_time_logged() {
        let http = reqwest::Client::new();
        let backoff = Duration::from_millis(20);
        // 503, 429, 500, then 200: the fourth attempt succeeds.
        let (url, count) = serve(vec![503, 429, 500, 200]);
        let retry = RetryTime::default();
        let body = send_with_backoff(|| http.get(&url), &retry, backoff, backoff * 3)
            .await
            .unwrap();
        assert_eq!(body, "status 200");
        assert_eq!(count.load(Ordering::SeqCst), 4);
        // Waits of 20, 60 (after the 429) and 120 ms plus the failed attempts.
        assert!(
            retry.get() >= Duration::from_millis(140),
            "{:?}",
            retry.get()
        );

        // Always 502: one attempt and three retries, then an error.
        let (url, count) = serve(vec![502]);
        let retry = RetryTime::default();
        let error = send_with_backoff(|| http.get(&url), &retry, backoff, backoff * 3)
            .await
            .unwrap_err();
        assert!(format!("{:?}", error).contains("gave up after 4 attempts"));
        assert_eq!(count.load(Ordering::SeqCst), 4);
        assert!(retry.get() >= Duration::from_millis(140));

        // A client error is final at once and costs no retry time.
        let (url, count) = serve(vec![400]);
        let retry = RetryTime::default();
        assert!(
            send_with_backoff(|| http.get(&url), &retry, backoff, backoff * 3)
                .await
                .is_err()
        );
        assert_eq!(count.load(Ordering::SeqCst), 1);
        assert_eq!(retry.get(), Duration::ZERO);
    }
}
