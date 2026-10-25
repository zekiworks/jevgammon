//! HTTP with retries for network and server errors: connection failures, 408, 429 and
//! 5xx are retried up to `RETRIES` times with backoff. The time spent on failed attempts
//! and waits is added to a `RetryTime`, which the runner keeps off the clock.

use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering};
use std::time::{Duration, Instant};

use reqwest::{RequestBuilder, StatusCode};

use crate::auth::snippet;
use crate::budget::{Hold, Ledger};
use std::sync::Arc;

/// Retries after the first attempt.
pub const RETRIES: u32 = 3;
/// Retry limit in force (`RETRIES` unless `limit_retries_per_call` set another).
static RETRY_LIMIT: AtomicU32 = AtomicU32::new(RETRIES);
/// When set, the limit counts every failed network or server attempt of one call (one
/// `RetryTime`), over all its sends (e.g. Antigravity's fallback endpoint), not per send.
static PER_CALL: AtomicBool = AtomicBool::new(false);

/// Close choices, stage B (Method §9.13): at most `retries` retries of network and server
/// errors per call, counted over every send of the call. Process-wide; the leagues never
/// call it.
pub fn limit_retries_per_call(retries: u32) {
    RETRY_LIMIT.store(retries, Ordering::Relaxed);
    PER_CALL.store(true, Ordering::Relaxed);
}

/// Retries allowed after failed network or server attempts.
#[derive(Clone, Copy, Debug)]
struct RetryPolicy {
    limit: u32,
    /// Count failures over the whole call (`RetryTime`), not per send.
    per_call: bool,
}

impl RetryPolicy {
    fn current() -> Self {
        RetryPolicy {
            limit: RETRY_LIMIT.load(Ordering::Relaxed),
            per_call: PER_CALL.load(Ordering::Relaxed),
        }
    }
}
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

/// A response with a status that is not retried (and not 401/403); `Display` gives the
/// status and the start of the body.
#[derive(Debug)]
pub struct StatusError {
    pub status: StatusCode,
    pub message: String,
}

impl std::fmt::Display for StatusError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.status, self.message)
    }
}

impl std::error::Error for StatusError {}

/// Time spent on failed attempts and backoff waits, shared between the requests of one
/// decision and the runner's clock.
#[derive(Debug, Default)]
pub struct RetryTime(AtomicU64, AtomicU32);

impl RetryTime {
    pub fn add(&self, spent: Duration) {
        self.0
            .fetch_add(spent.as_millis() as u64, Ordering::Relaxed);
    }

    pub fn get(&self) -> Duration {
        Duration::from_millis(self.0.load(Ordering::Relaxed))
    }

    /// Failed network or server attempts so far (counted when `limit_retries_per_call` is on).
    #[cfg(test)]
    pub fn failures(&self) -> u32 {
        self.1.load(Ordering::Relaxed)
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
    let (body, _) = send_with_backoff(
        make,
        retry,
        None,
        FIRST_BACKOFF,
        RATE_LIMIT_BACKOFF,
        RetryPolicy::current(),
    )
    .await?;
    Ok(body)
}

/// As `send`, under a budget: every attempt first reserves `worst_case` dollars in `ledger`
/// (refused, before the call, when that would pass the cap). An attempt answered with an
/// error status is booked at nothing; one without a response keeps its worst case. The
/// successful attempt's reservation is returned for the caller to settle at its cost.
pub async fn send_metered(
    make: impl Fn() -> RequestBuilder,
    retry: &RetryTime,
    ledger: &Arc<Ledger>,
    worst_case: f64,
) -> Result<(String, Hold), CallError> {
    let (body, hold) = send_with_backoff(
        make,
        retry,
        Some((ledger, worst_case)),
        FIRST_BACKOFF,
        RATE_LIMIT_BACKOFF,
        RetryPolicy::current(),
    )
    .await?;
    Ok((body, hold.expect("a metered attempt holds a reservation")))
}

async fn send_with_backoff(
    make: impl Fn() -> RequestBuilder,
    retry: &RetryTime,
    budget: Option<(&Arc<Ledger>, f64)>,
    first_backoff: Duration,
    rate_limit_backoff: Duration,
    policy: RetryPolicy,
) -> Result<(String, Option<Hold>), CallError> {
    let mut backoff = first_backoff;
    let mut attempt = 0;
    loop {
        let hold = match budget {
            Some((ledger, amount)) => Some(ledger.reserve(amount)?),
            None => None,
        };
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
                let body = match response.text().await {
                    Ok(body) => body,
                    // The body was cut off: what was generated is unknown, `hold` is lost.
                    Err(error) if status.is_success() => {
                        return Err(CallError::Fatal(anyhow::anyhow!(
                            "reading the response failed: {error}"
                        )));
                    }
                    Err(_) => String::new(),
                };
                if status.is_success() {
                    return Ok((body, hold));
                }
                if let Some(hold) = hold {
                    hold.refused(&format!("{status}"));
                }
                if matches!(status, StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN) {
                    return Err(CallError::Auth(format!("{status}: {}", snippet(&body))));
                }
                if !retryable(status) {
                    return Err(CallError::Fatal(
                        StatusError {
                            status,
                            message: snippet(&body),
                        }
                        .into(),
                    ));
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
            // No response: `hold` drops here and keeps its worst case.
            Err(error) => format!("{error}"),
        };
        // Failed attempts so far: of this send, or of the whole call under a per-call limit.
        let failed = if policy.per_call {
            retry.1.fetch_add(1, Ordering::Relaxed) + 1
        } else {
            attempt + 1
        };
        if failed > policy.limit {
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

    const LEAGUE: RetryPolicy = RetryPolicy {
        limit: RETRIES,
        per_call: false,
    };

    /// Stage B (Method §9.13): at most 2 retries per call, counted over every send of the call.
    #[tokio::test]
    async fn per_call_limit_counts_failures_over_every_send() {
        let http = reqwest::Client::new();
        let backoff = Duration::from_millis(5);
        let stage_b = RetryPolicy {
            limit: 2,
            per_call: true,
        };
        // Always 502: one attempt and two retries.
        let (url, count) = serve(vec![502]);
        let retry = RetryTime::default();
        let error = send_with_backoff(|| http.get(&url), &retry, None, backoff, backoff, stage_b)
            .await
            .unwrap_err();
        assert!(format!("{error:?}").contains("gave up after 3 attempts"));
        assert_eq!(count.load(Ordering::SeqCst), 3);
        // A second send of the same call (a fallback endpoint) gets no retry left: one attempt.
        let (url, count) = serve(vec![502]);
        assert!(
            send_with_backoff(|| http.get(&url), &retry, None, backoff, backoff, stage_b)
                .await
                .is_err()
        );
        assert_eq!(count.load(Ordering::SeqCst), 1);
        // 503 then 200: one retry, success.
        let (url, count) = serve(vec![503, 200]);
        let retry = RetryTime::default();
        assert!(
            send_with_backoff(|| http.get(&url), &retry, None, backoff, backoff, stage_b)
                .await
                .is_ok()
        );
        assert_eq!(count.load(Ordering::SeqCst), 2);
        assert_eq!(retry.failures(), 1);
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
        let (body, _) = send_with_backoff(
            || http.get(&url),
            &retry,
            None,
            backoff,
            backoff * 3,
            LEAGUE,
        )
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
        let error = send_with_backoff(
            || http.get(&url),
            &retry,
            None,
            backoff,
            backoff * 3,
            LEAGUE,
        )
        .await
        .unwrap_err();
        assert!(format!("{:?}", error).contains("gave up after 4 attempts"));
        assert_eq!(count.load(Ordering::SeqCst), 4);
        assert!(retry.get() >= Duration::from_millis(140));

        // A client error is final at once and costs no retry time.
        let (url, count) = serve(vec![400]);
        let retry = RetryTime::default();
        assert!(
            send_with_backoff(
                || http.get(&url),
                &retry,
                None,
                backoff,
                backoff * 3,
                LEAGUE
            )
            .await
            .is_err()
        );
        assert_eq!(count.load(Ordering::SeqCst), 1);
        assert_eq!(retry.get(), Duration::ZERO);
    }

    /// Under a budget: an error status is booked at nothing, the answered attempt's hold
    /// is returned, and an attempt over the cap is refused before anything is sent.
    #[tokio::test]
    async fn metered_attempts_reserve_before_sending() {
        let http = reqwest::Client::new();
        let backoff = Duration::from_millis(5);
        let dir = std::env::temp_dir().join(format!("budget-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();
        let config = crate::budget::BudgetConfig {
            ledger: dir.join("ledger.db").to_string_lossy().into_owned(),
            cap_usd: 1.0,
            input_per_mtok: 2.0,
            cached_input_per_mtok: 0.2,
            output_per_mtok: 10.0,
        };
        let ledger = Ledger::open(&config, "t").unwrap();
        let (url, count) = serve(vec![503, 200]);
        let retry = RetryTime::default();
        let (_, hold) = send_with_backoff(
            || http.get(&url),
            &retry,
            Some((&ledger, 0.7)),
            backoff,
            backoff,
            LEAGUE,
        )
        .await
        .unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 2);
        // The answered attempt's 0.7 is still reserved: 0.4 more is refused unsent.
        let (url, count) = serve(vec![200]);
        let error = send_with_backoff(
            || http.get(&url),
            &retry,
            Some((&ledger, 0.4)),
            backoff,
            backoff,
            LEAGUE,
        )
        .await
        .unwrap_err();
        assert!(format!("{error:?}").contains("BUDGET CAP"));
        assert_eq!(count.load(Ordering::SeqCst), 0);
        hold.unwrap().settle(
            crate::budget::Usage {
                input_tokens: 1000,
                output_tokens: 1000,
                ..Default::default()
            },
            None,
        );
        assert!(
            send_with_backoff(
                || http.get(&url),
                &retry,
                Some((&ledger, 0.4)),
                backoff,
                backoff,
                LEAGUE
            )
            .await
            .is_ok()
        );
    }
}
