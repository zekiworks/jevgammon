//! `gnubg-weak`: GNU Backgammon's own move choice (`gnubg.findbestmove`) at a weak
//! predefined level. One long-lived `gnubg -t -q -p tools/gnubg_player.py` process per
//! player answers every decision in about 10 ms; see that script for the line protocol.

use std::io::{BufRead, BufReader, Write as _};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::Mutex;

use anyhow::{Context, Result, anyhow, bail};
use serde_json::json;

use super::{Decision, DecisionRequest, Engine};
use crate::board::{Board, Play};

/// The script and the tools/v3 modules it imports, written to one folder at start-up.
const FILES: [(&str, &str); 3] = [
    ("gnubg_player.py", include_str!("../../tools/gnubg_player.py")),
    ("engine.py", include_str!("../../tools/v3/engine.py")),
    ("rules.py", include_str!("../../tools/v3/rules.py")),
];
const PREFIX: &str = "gnubg-player ";

/// A gnubg evaluation context for move choice.
#[derive(Clone, Copy, Debug)]
pub struct Level {
    pub plies: u8,
    /// Standard deviation of the noise gnubg adds to every evaluation output.
    pub noise: f32,
    /// Same noise for the same position (gnubg's predefined levels), so play is reproducible.
    pub deterministic: bool,
}

/// gnubg's predefined "Beginner" level (eval.c `aecSettings`): 0-ply, deterministic noise
/// 0.060, used cubeless because these games have no doubling cube.
pub const WEAK: Level = Level {
    plies: 0,
    noise: 0.060,
    deterministic: true,
};

struct GnubgProcess {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

impl GnubgProcess {
    fn start(level: Level, lib: &Path) -> Result<Self> {
        for (name, source) in FILES {
            std::fs::write(lib.join(name), source)?;
        }
        let binary = std::env::var("GNUBG").unwrap_or_else(|_| "gnubg".into());
        let mut child = Command::new(&binary)
            .args(["-t", "-q", "-p"])
            .arg(lib.join(FILES[0].0))
            .env("GNUBG_PLAYER_LIB", lib)
            .env("GNUBG_PLAYER_PLIES", level.plies.to_string())
            .env("GNUBG_PLAYER_NOISE", level.noise.to_string())
            .env(
                "GNUBG_PLAYER_DETERMINISTIC",
                u8::from(level.deterministic).to_string(),
            )
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .with_context(|| format!("starting {binary}"))?;
        let stdin = child.stdin.take().context("gnubg stdin")?;
        let stdout = BufReader::new(child.stdout.take().context("gnubg stdout")?);
        let mut process = GnubgProcess {
            child,
            stdin,
            stdout,
        };
        let reply = process.reply()?;
        if !reply.starts_with("ready ") {
            bail!("gnubg: unexpected start-up reply `{reply}`");
        }
        Ok(process)
    }

    /// Reads lines until one carries the protocol prefix; gnubg's banner shares stdout.
    fn reply(&mut self) -> Result<String> {
        let mut line = String::new();
        loop {
            line.clear();
            if self.stdout.read_line(&mut line)? == 0 {
                bail!("gnubg exited");
            }
            if let Some(reply) = line.trim_end().strip_prefix(PREFIX) {
                return Ok(reply.to_owned());
            }
        }
    }

    fn choose(&mut self, request: &str) -> Result<usize> {
        writeln!(self.stdin, "{request}")?;
        self.stdin.flush()?;
        let reply = self.reply()?;
        if let Some(error) = reply.strip_prefix("error ") {
            bail!("gnubg: {error}");
        }
        reply
            .parse()
            .map_err(|_| anyhow!("gnubg: unexpected reply `{reply}`"))
    }
}

impl Drop for GnubgProcess {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

pub struct GnubgPlayer {
    process: Mutex<GnubgProcess>,
}

impl GnubgPlayer {
    /// Starts gnubg (`GNUBG`, or `gnubg` on the PATH) and waits until it is ready.
    pub fn start(level: Level) -> Result<Self> {
        let lib: PathBuf = std::env::temp_dir().join(format!(
            "jevgammon-gnubg-player-{}",
            uuid::Uuid::new_v4().simple()
        ));
        std::fs::create_dir(&lib)?;
        let process = GnubgProcess::start(level, &lib);
        // gnubg has imported everything once it reports ready (or failed).
        let _ = std::fs::remove_dir_all(&lib);
        Ok(GnubgPlayer {
            process: Mutex::new(process?),
        })
    }

    /// Index into `plays` (the legal plays of `board` with `dice`, in `legal_plays` order)
    /// of gnubg's play. Blocks for one pipe round trip; a player shared by several matches
    /// serves them one at a time.
    pub fn choose(&self, board: &Board, dice: (u8, u8), plays: &[Play]) -> Result<usize> {
        let position = |b: &Board| json!([b.pts, b.bar, b.off]);
        let request = json!({
            "board": position(board),
            "dice": [dice.0, dice.1],
            "plays": plays.iter().map(|play| position(&play.result)).collect::<Vec<_>>(),
        })
        .to_string();
        let index = self
            .process
            .lock()
            .map_err(|_| anyhow!("gnubg process poisoned"))?
            .choose(&request)?;
        if index >= plays.len() {
            bail!("gnubg chose play {index} of {}", plays.len());
        }
        Ok(index)
    }
}

impl Engine for GnubgPlayer {
    fn decide(&self, req: &DecisionRequest<'_>) -> Result<Decision> {
        Ok(Decision::new(self.choose(req.board, req.dice, req.plays)?))
    }
}
