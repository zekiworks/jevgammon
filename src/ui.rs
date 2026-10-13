//! Ratatui front end. Speeds 1-6 draw the board; max speed drops it and shows only
//! the score with rolls and moves flashing underneath.

use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::Result;
use ratatui::crossterm::event::{self, Event as TermEvent, KeyCode, KeyEventKind, KeyModifiers};
use ratatui::layout::{Alignment, Constraint, Layout, Rect};
use ratatui::style::{Color, Modifier, Style, Stylize};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph};
use ratatui::{DefaultTerminal, Frame};
use tokio::sync::mpsc;

use crate::board::{Board, Side};
use crate::runner::{Clocks, Control, Event, MAX_SPEED, SPEED_DELAYS_MS, format_clock};

/// Clocks below this are drawn in red.
const LOW_CLOCK: Duration = Duration::from_secs(30);

const LOG_CAPACITY: usize = 500;
const FLASH: Duration = Duration::from_millis(250);
const WHITE: Color = Color::Rgb(240, 240, 220);
const BLACK: Color = Color::Rgb(230, 80, 70);

struct LogLine {
    side: Option<Side>,
    text: String,
    at: Instant,
}

/// The roll on the table: the mover's dice while it decides, then until the next roll.
#[derive(Clone, Copy)]
struct Roll {
    player: u8,
    side: Side,
    dice: (u8, u8),
    /// Set while the model is choosing a play.
    thinking_since: Option<Instant>,
}

fn dice_text(dice: (u8, u8)) -> String {
    format!("[{}] [{}]", dice.0, dice.1)
}

pub struct App {
    names: [String; 2],
    match_id: i64,
    seed: u64,
    control: Arc<Control>,
    round: u32,
    rounds: u32,
    leg: u8,
    white_player: u8,
    board: Board,
    score: [u32; 2],
    log: VecDeque<LogLine>,
    roll: Option<Roll>,
    /// Banks as of the last event; the thinking player's counts down from it once its
    /// free delay has passed.
    clocks: Clocks,
    delay: Duration,
    finished: Option<String>,
    failed: Option<String>,
}

fn side_style(side: Side) -> Style {
    match side {
        Side::White => Style::new().fg(WHITE),
        Side::Black => Style::new().fg(BLACK),
    }
}

fn glyph(side: Side) -> &'static str {
    match side {
        Side::White => "○",
        Side::Black => "●",
    }
}

impl App {
    pub fn new(
        names: [String; 2],
        match_id: i64,
        seed: u64,
        rounds: u32,
        delay: Duration,
        control: Arc<Control>,
    ) -> Self {
        App {
            names,
            match_id,
            seed,
            control,
            round: 1,
            rounds,
            leg: 1,
            white_player: 1,
            board: Board::start(),
            score: [0, 0],
            log: VecDeque::new(),
            roll: None,
            clocks: [None; 2],
            delay,
            finished: None,
            failed: None,
        }
    }

    fn side_of(&self, player: u8) -> Side {
        if player == self.white_player {
            Side::White
        } else {
            Side::Black
        }
    }

    fn push(&mut self, side: Option<Side>, text: String) {
        if self.log.len() == LOG_CAPACITY {
            self.log.pop_back();
        }
        self.log.push_front(LogLine {
            side,
            text,
            at: Instant::now(),
        });
    }

    fn apply(&mut self, event: Event) {
        match event {
            Event::GameStarted {
                round,
                rounds,
                leg,
                white_player,
                board,
                clocks,
            } => {
                (
                    self.round,
                    self.rounds,
                    self.leg,
                    self.white_player,
                    self.board,
                    self.clocks,
                ) = (round, rounds, leg, white_player, board, clocks);
                self.roll = None;
                let white = &self.names[white_player as usize - 1];
                self.push(
                    None,
                    format!("── round {round}/{rounds} · leg {leg} · {white} plays ○ ──"),
                );
            }
            Event::Thinking {
                player,
                side,
                dice,
                clocks,
            } => {
                self.clocks = clocks;
                self.roll = Some(Roll {
                    player,
                    side,
                    dice,
                    thinking_since: Some(Instant::now()),
                });
            }
            Event::Moved {
                turn_no,
                side,
                player,
                dice,
                notation,
                board,
                decided_by,
                latency_ms,
                clocks,
            } => {
                self.clocks = clocks;
                self.roll = Some(Roll {
                    player,
                    side,
                    dice,
                    thinking_since: None,
                });
                self.board = board;
                let play = match (decided_by, notation.is_empty()) {
                    ("timeout", _) => "⌛ out of time".to_owned(),
                    (_, true) => "(no legal move)".to_owned(),
                    (_, false) => notation,
                };
                let note = match decided_by {
                    "model" | "timeout" => format!("  {:.1}s", latency_ms as f64 / 1000.0),
                    "fallback" => "  [fallback: no valid reply]".to_owned(),
                    "forced" => "  [forced]".to_owned(),
                    _ => String::new(),
                };
                let name = &self.names[player as usize - 1];
                self.push(
                    Some(side),
                    format!(
                        "#{turn_no:<3} {} {name}  {}-{}  {play}{note}",
                        glyph(side),
                        dice.0,
                        dice.1
                    ),
                );
            }
            Event::GameOver {
                round,
                leg,
                winner,
                kind,
                score,
            } => {
                self.score = score;
                let name = &self.names[winner as usize - 1];
                let side = self.side_of(winner);
                self.push(
                    Some(side),
                    format!(
                        "★ {name} wins round {round} leg {leg}: {} (+{})",
                        kind.describe(),
                        kind.points()
                    ),
                );
            }
            Event::MatchOver {
                score,
                winner,
                rounds,
            } => {
                self.score = score;
                if let Some(roll) = &mut self.roll {
                    roll.thinking_since = None;
                }
                let verdict = match winner {
                    Some(player) => format!("{} wins", self.names[player as usize - 1]),
                    None => "draw".to_owned(),
                };
                self.finished = Some(format!(
                    "Match over after {rounds} rounds: {verdict} {}-{}",
                    score[0], score[1]
                ));
            }
            Event::Failed(message) => {
                if let Some(roll) = &mut self.roll {
                    roll.thinking_since = None;
                }
                self.failed = Some(message);
            }
        }
    }

    fn done(&self) -> bool {
        self.finished.is_some() || self.failed.is_some()
    }

    fn header(&self) -> Line<'static> {
        let speed = self.control.speed();
        let speed_text = if speed == MAX_SPEED {
            "max".to_owned()
        } else {
            format!("{speed} ({}ms)", SPEED_DELAYS_MS[speed as usize - 1])
        };
        let mut spans = vec![
            " jevgammon ".bold(),
            format!(
                "match #{} · seed {} · round {}/{} · leg {} · speed {speed_text} ",
                self.match_id, self.seed, self.round, self.rounds, self.leg
            )
            .into(),
        ];
        if self.control.paused() {
            spans.push(" PAUSED ".black().on_yellow());
        }
        Line::from(spans)
    }

    /// Bank `player` has left right now, counting down while it thinks past the delay.
    fn clock_left(&self, player: u8) -> Option<Duration> {
        let left = self.clocks[player as usize - 1]?;
        match self.roll {
            Some(Roll {
                player: mover,
                thinking_since: Some(since),
                ..
            }) if mover == player => {
                Some(left.saturating_sub(since.elapsed().saturating_sub(self.delay)))
            }
            _ => Some(left),
        }
    }

    fn score_line(&self) -> Line<'static> {
        let seat = |player: u8| {
            let side = self.side_of(player);
            let mut spans = vec![Span::styled(
                format!("{} {}", glyph(side), self.names[player as usize - 1]),
                side_style(side).bold(),
            )];
            if let Some(left) = self.clock_left(player) {
                let running = self
                    .roll
                    .is_some_and(|r| r.player == player && r.thinking_since.is_some());
                let mut style = if left < LOW_CLOCK {
                    Style::new().fg(Color::Red)
                } else {
                    Style::new().fg(Color::Gray)
                };
                style = if running {
                    style.add_modifier(Modifier::BOLD)
                } else {
                    style.add_modifier(Modifier::DIM)
                };
                spans.push(Span::styled(format!(" ⏱ {}", format_clock(left)), style));
            }
            spans
        };
        let mut spans = seat(1);
        spans.push(
            format!("   {}  :  {}   ", self.score[0], self.score[1])
                .bold()
                .yellow(),
        );
        spans.extend(seat(2));
        Line::from(spans)
    }

    fn status_line(&self) -> Line<'static> {
        if let Some(message) = &self.failed {
            return Line::from(format!("aborted: {message}")).red().bold();
        }
        if let Some(message) = &self.finished {
            return Line::from(message.clone()).green().bold();
        }
        let Some(roll) = self.roll else {
            return Line::from("");
        };
        let mut spans = vec![
            Span::styled(
                format!(
                    "{} {} rolled ",
                    glyph(roll.side),
                    self.names[roll.player as usize - 1]
                ),
                side_style(roll.side),
            ),
            Span::styled(dice_text(roll.dice), side_style(roll.side).bold()),
        ];
        if let Some(since) = roll.thinking_since {
            spans.push(format!("  thinking… {:.1}s", since.elapsed().as_secs_f64()).dim());
        }
        Line::from(spans)
    }

    fn log_lines(&self, rows: usize, flash: bool) -> Vec<Line<'static>> {
        self.log
            .iter()
            .take(rows)
            .enumerate()
            .map(|(i, entry)| {
                let mut style = entry
                    .side
                    .map(side_style)
                    .unwrap_or_else(|| Style::new().fg(Color::Cyan));
                if i == 0 && flash && entry.at.elapsed() < FLASH {
                    style = style.add_modifier(Modifier::REVERSED | Modifier::BOLD);
                } else if i > 0 {
                    style = style.add_modifier(Modifier::DIM);
                }
                Line::styled(entry.text.clone(), style)
            })
            .collect()
    }

    fn draw(&self, frame: &mut Frame) {
        let area = frame.area();
        let footer = if self.done() {
            " [q] quit "
        } else {
            " [+/-] speed  [1-6] speed  [m] max  [space] pause  [q] quit "
        };
        let block = Block::bordered()
            .title(self.header())
            .title_bottom(Line::from(footer).dim());
        let inner = block.inner(area);
        frame.render_widget(block, area);
        if self.control.speed() == MAX_SPEED {
            self.draw_max(frame, inner);
        } else {
            self.draw_board_view(frame, inner);
        }
    }

    fn draw_max(&self, frame: &mut Frame, area: Rect) {
        let rows = area.height as usize;
        let score_row = rows.saturating_sub(12) / 2;
        let mut lines: Vec<Line> = vec![Line::from(""); score_row];
        lines.push(self.score_line());
        lines.push(
            Line::from(format!(
                "round {}/{} · leg {}",
                self.round, self.rounds, self.leg
            ))
            .dim(),
        );
        lines.push(self.status_line());
        lines.push(Line::from(""));
        let [head, log] =
            Layout::vertical([Constraint::Length(lines.len() as u16), Constraint::Min(0)])
                .areas(area);
        frame.render_widget(Paragraph::new(lines).alignment(Alignment::Center), head);
        // Moves stay left-aligned in a centered column so the flashing line is steady.
        let width = log.width.min(72);
        let column = Rect {
            x: log.x + (log.width - width) / 2,
            width,
            ..log
        };
        frame.render_widget(
            Paragraph::new(self.log_lines(column.height as usize, true)),
            column,
        );
    }

    fn draw_board_view(&self, frame: &mut Frame, area: Rect) {
        let [score, board, status, log] = Layout::vertical([
            Constraint::Length(2),
            Constraint::Length(19),
            Constraint::Length(2),
            Constraint::Min(0),
        ])
        .areas(area);
        frame.render_widget(
            Paragraph::new(self.score_line()).alignment(Alignment::Center),
            score,
        );
        frame.render_widget(
            Paragraph::new(self.board_lines()).alignment(Alignment::Center),
            board,
        );
        frame.render_widget(
            Paragraph::new(self.status_line()).alignment(Alignment::Center),
            status,
        );
        let lines = self.log_lines(log.height as usize, false);
        frame.render_widget(
            Paragraph::new(lines).block(Block::new().title(" moves ".dim())),
            log,
        );
    }

    fn board_lines(&self) -> Vec<Line<'static>> {
        let b = &self.board;
        let frame_style = Style::new().fg(Color::DarkGray);
        let numbers = |points: [usize; 12]| {
            let mut spans = vec![Span::raw(" ")];
            for (i, p) in points.iter().enumerate() {
                if i == 6 {
                    spans.push(Span::styled("  │BAR│  ", frame_style));
                }
                spans.push(Span::styled(format!("{p:^3}"), frame_style));
            }
            spans.push(Span::raw("       "));
            Line::from(spans)
        };
        let cell = |point: usize, depth: usize| -> Span<'static> {
            let n = b.pts[point - 1];
            let count = n.unsigned_abs() as usize;
            let side = if n > 0 { Side::White } else { Side::Black };
            if depth == 4 && count > 5 {
                Span::styled(format!("{count:^3}"), side_style(side).bold())
            } else if depth < count {
                Span::styled(format!(" {} ", glyph(side)), side_style(side))
            } else if depth == 0 {
                Span::styled(" · ", frame_style)
            } else {
                Span::raw("   ")
            }
        };
        let bar_cell = |side: Side, depth: usize| -> Span<'static> {
            let count = b.bar[side as usize];
            if depth == 0 && count > 0 {
                Span::styled(
                    format!("{}{:<2}", glyph(side), count),
                    side_style(side).bold(),
                )
            } else {
                Span::raw("   ")
            }
        };
        let off_cell = |side: Side, depth: usize| -> Span<'static> {
            let count = b.off[side as usize];
            if depth == 0 && count > 0 {
                Span::styled(format!(" {}{count:<3}", glyph(side)), side_style(side))
            } else {
                Span::raw("      ")
            }
        };
        let row = |points: [usize; 12], depth: usize, bar_side: Side| {
            let mut spans = vec![Span::styled("│", frame_style)];
            for (i, &p) in points.iter().enumerate() {
                if i == 6 {
                    spans.push(Span::styled("  │", frame_style));
                    spans.push(bar_cell(bar_side, depth));
                    spans.push(Span::styled("│  ", frame_style));
                }
                spans.push(cell(p, depth));
            }
            spans.push(Span::styled("│", frame_style));
            spans.push(off_cell(bar_side, depth));
            Line::from(spans)
        };
        let top = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24];
        let bottom = [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1];
        let rule = |left: &str, mid: &str, right: &str| {
            Line::styled(
                format!(
                    "{left}{}{mid}{}{right}      ",
                    "─".repeat(20),
                    "─".repeat(20)
                ),
                frame_style,
            )
        };
        let mut lines = vec![numbers(top), rule("┌", "┬───┬", "┐")];
        // Each side's bar and borne-off checkers sit on its home half: black top, white bottom.
        lines.extend((0..5).map(|depth| row(top, depth, Side::Black)));
        // The roll sits in the middle of the board, in the mover's half as in gnubg:
        // white (bottom player) rolls into the right half, black into the left.
        let dice_rows: [String; 3] = match self.roll {
            Some(Roll { dice: (d1, d2), .. }) => [
                "┌───┐ ┌───┐".to_owned(),
                format!("│ {d1} │ │ {d2} │"),
                "└───┘ └───┘".to_owned(),
            ],
            None => Default::default(),
        };
        let dice_style = self
            .roll
            .map_or(Style::new(), |roll| side_style(roll.side).bold());
        for (i, dice) in dice_rows.iter().enumerate() {
            let half = |mine: bool| {
                if mine {
                    Span::styled(format!("{dice:^20}"), dice_style)
                } else {
                    Span::raw(" ".repeat(20))
                }
            };
            let white_rolls = self.roll.is_some_and(|roll| roll.side == Side::White);
            lines.push(Line::from(vec![
                Span::styled("│", frame_style),
                half(self.roll.is_some() && !white_rolls),
                Span::styled(if i == 1 { "│BAR│" } else { "│   │" }, frame_style),
                half(white_rolls),
                Span::styled("│", frame_style),
                Span::raw("      "),
            ]));
        }
        lines.extend((0..5).rev().map(|depth| row(bottom, depth, Side::White)));
        lines.push(rule("└", "┴───┴", "┘"));
        lines.push(numbers(bottom));
        lines.push(Line::from(vec![
            Span::styled(
                format!("○ pips {}", b.mover_pips()),
                side_style(Side::White),
            ),
            Span::raw("      "),
            Span::styled(
                format!("● pips {}", b.opponent_pips()),
                side_style(Side::Black),
            ),
        ]));
        lines
    }
}

/// Runs the interface until the user quits. Quitting mid-match cancels it.
pub fn run(
    terminal: &mut DefaultTerminal,
    mut app: App,
    mut events: mpsc::UnboundedReceiver<Event>,
) -> Result<()> {
    loop {
        while let Ok(event) = events.try_recv() {
            app.apply(event);
        }
        terminal.draw(|frame| app.draw(frame))?;
        if !event::poll(Duration::from_millis(33))? {
            continue;
        }
        let TermEvent::Key(key) = event::read()? else {
            continue;
        };
        if key.kind != KeyEventKind::Press {
            continue;
        }
        let control = &app.control;
        match key.code {
            KeyCode::Char('q') | KeyCode::Esc => break,
            KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => break,
            KeyCode::Char('+' | '=') | KeyCode::Right | KeyCode::Up => {
                control.set_speed(control.speed() + 1)
            }
            KeyCode::Char('-' | '_') | KeyCode::Left | KeyCode::Down => {
                control.set_speed(control.speed().saturating_sub(1))
            }
            KeyCode::Char('m' | '0') => control.set_speed(MAX_SPEED),
            KeyCode::Char(c @ '1'..='6') => control.set_speed(c as u8 - b'0'),
            KeyCode::Char(' ') | KeyCode::Char('p') => control.toggle_pause(),
            _ => {}
        }
    }
    app.control.cancel();
    Ok(())
}
