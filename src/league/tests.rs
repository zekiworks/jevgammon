use super::*;

fn names(n: usize) -> Vec<String> {
    (0..n).map(|i| format!("m{i}")).collect()
}

/// A player id per test name (its first byte).
fn id_of(name: &str) -> i64 {
    name.as_bytes()[0] as i64
}

fn fixture(order: usize, day: u32, model1: &str, model2: &str) -> Fixture {
    Fixture {
        order,
        stage: "league",
        label: format!("matchday {day}: {model1} v {model2}"),
        matchday: Some(day),
        model1: model1.into(),
        model2: model2.into(),
        players: [id_of(model1), id_of(model2)],
        seed: 0,
        match_id: None,
        status: None,
    }
}

fn temp_db(tag: &str) -> PathBuf {
    let path = std::env::temp_dir().join(format!("jevgammon-{tag}-{}.db", std::process::id()));
    for suffix in ["", "-wal", "-shm"] {
        let _ = std::fs::remove_file(format!("{}{suffix}", path.display()));
    }
    path
}

fn rules(mirror: bool) -> Rules {
    Rules::new(1, None, Some(300), "bg-v2", 9, mirror)
}

#[test]
fn a_match_starts_while_both_models_are_below_their_limit_in_fixture_order() {
    let mut pending = vec![
        fixture(1, 1, "A", "B"),
        fixture(2, 1, "C", "D"),
        fixture(3, 2, "A", "C"),
        fixture(4, 2, "B", "D"),
        fixture(5, 3, "A", "D"),
        fixture(6, 3, "B", "C"),
    ];
    // A plays two matches at once, R (a local engine) any number, the others one.
    let limit = |name: &str| match name {
        "A" => 2,
        "R" => usize::MAX,
        _ => 1,
    };
    let free = |_: &Fixture| false;
    let mut running: HashMap<String, usize> = HashMap::new();
    let ids = |started: Vec<Fixture>| started.iter().map(|f| f.order).collect::<Vec<_>>();
    let end = |running: &mut HashMap<String, usize>, a: &str, b: &str| {
        *running.get_mut(a).unwrap() -= 1;
        *running.get_mut(b).unwrap() -= 1;
    };
    assert_eq!(
        ids(take_startable(&mut pending, &mut running, limit, free)),
        [1, 2]
    );
    // C v D ends while A v B still runs: A v C starts as A's second match; B v D still
    // waits for B, A v D for A.
    end(&mut running, "C", "D");
    assert_eq!(
        ids(take_startable(&mut pending, &mut running, limit, free)),
        [3]
    );
    assert_eq!(running["A"], 2);
    // A v B ends: B v D goes first; A v D now waits for D, B v C for B and C.
    end(&mut running, "A", "B");
    assert_eq!(
        ids(take_startable(&mut pending, &mut running, limit, free)),
        [4]
    );
    end(&mut running, "A", "C");
    end(&mut running, "B", "D");
    // C backs off: its match waits, the next one starts.
    let c_backs_off = |f: &Fixture| f.model1 == "C" || f.model2 == "C";
    assert_eq!(
        ids(take_startable(
            &mut pending,
            &mut running,
            limit,
            c_backs_off
        )),
        [5]
    );
    assert_eq!(
        ids(take_startable(&mut pending, &mut running, limit, free)),
        [6]
    );
    assert!(pending.is_empty());
    // An engine without a limit plays all its matches at once.
    let mut pending = vec![
        fixture(7, 4, "R", "E"),
        fixture(8, 5, "F", "R"),
        fixture(9, 6, "R", "G"),
    ];
    assert_eq!(
        ids(take_startable(&mut pending, &mut running, limit, free)),
        [7, 8, 9]
    );
    assert_eq!(running["R"], 3);
}

#[test]
fn backoff_doubles_up_to_the_longest_and_blames_the_failing_player() {
    let limits = (Duration::from_secs(120), Duration::from_secs(600));
    let now = Instant::now();
    let first = Backoff::after(None, "402".into(), now, limits);
    assert_eq!((first.delay, first.failures), (limits.0, 1));
    // Another failure while it runs (a second match of the player) keeps it.
    let same = Backoff::after(Some(&first), "402 again".into(), now, limits);
    assert_eq!((same.until, same.failures), (first.until, 1));
    let mut last = first;
    for delay in [240, 480, 600, 600] {
        let at = last.until;
        last = Backoff::after(Some(&last), "402".into(), at, limits);
        assert_eq!(last.delay, Duration::from_secs(delay));
        assert_eq!(last.until, at + last.delay);
    }
    assert_eq!(last.failures, 5);

    let f = fixture(1, 1, "A", "B");
    let failed = anyhow::anyhow!("402 Payment Required")
        .context(PlayerFault(2))
        .context("round 1");
    assert_eq!(blamed(&f, &failed), Some("B"));
    assert_eq!(blamed(&f, &anyhow::anyhow!("database is locked")), None);
    let mut backoffs = Backoffs::default();
    backoffs.fail(&f, &failed, now, limits);
    let other = fixture(2, 2, "A", "C");
    let (who, backoff) = backoffs.holding(&f, now).unwrap();
    assert_eq!(
        (who, backoff.error.as_str()),
        ("B", "round 1: player 2: 402 Payment Required")
    );
    assert!(backoffs.holding(&other, now).is_none());
    assert!(backoffs.holding(&f, now + limits.0).is_none());
    assert_eq!(backoffs.next_end(now), Some(now + limits.0));
    // A failure no player is to blame for holds the match only, whichever side is first.
    backoffs.fail(&other, &anyhow::anyhow!("disk full"), now, limits);
    assert_eq!(backoffs.holding(&other, now).unwrap().0, "the match");
    assert_eq!(
        backoffs.holding(&fixture(5, 2, "C", "A"), now).unwrap().0,
        "the match"
    );
    assert!(backoffs.holding(&fixture(3, 3, "A", "D"), now).is_none());
    backoffs.clear(&f);
    assert!(backoffs.holding(&f, now).is_none());
}

fn participant(id: i64, name: &str, joined_at: &str) -> Participant {
    Participant {
        player_id: id,
        config: PlayerConfig::new(name, "random"),
        joined_at: joined_at.into(),
    }
}

#[test]
fn fixture_is_a_round_robin_with_one_match_per_model_per_matchday_and_joiners_after() {
    for n in [7, 8] {
        let mut people: Vec<Participant> = names(n)
            .iter()
            .enumerate()
            .map(|(i, name)| participant(i as i64 + 1, name, "2026-10-01"))
            .collect();
        let fixture = derive_fixture(11, &rules(false), &people, &[]);
        let mut pairs: Vec<(i64, i64)> = fixture.iter().map(Fixture::key).collect();
        pairs.sort();
        pairs.dedup();
        assert_eq!(pairs.len(), n * (n - 1) / 2);
        assert_eq!(fixture.len(), pairs.len());
        let days = if n % 2 == 0 { n - 1 } else { n };
        for day in 1..=days as u32 {
            let mut seen: Vec<&String> = fixture
                .iter()
                .filter(|f| f.matchday == Some(day))
                .flat_map(|f| [&f.model1, &f.model2])
                .collect();
            let count = seen.len();
            seen.sort();
            seen.dedup();
            assert_eq!(seen.len(), count, "a model plays twice on matchday {day}");
            assert_eq!(count, n / 2 * 2);
        }
        // Two late joiners: each on a matchday of its own after the founders', against
        // everyone who joined before it.
        people.push(participant(100, "late1", "2026-10-02"));
        people.push(participant(101, "late2", "2026-10-03"));
        let with_late = derive_fixture(11, &rules(false), &people, &[]);
        assert_eq!(&with_late[..fixture.len()].len(), &fixture.len());
        for (old, new) in fixture.iter().zip(&with_late) {
            assert_eq!((&old.label, old.seed), (&new.label, new.seed));
        }
        let day = |f: &Fixture| f.matchday.unwrap();
        let late1: Vec<&Fixture> = with_late[fixture.len()..fixture.len() + n].iter().collect();
        assert!(
            late1
                .iter()
                .all(|f| day(f) == days as u32 + 1 && f.key().1 == 100)
        );
        let late2 = &with_late[fixture.len() + n..];
        assert_eq!(late2.len(), n + 1);
        assert!(
            late2
                .iter()
                .all(|f| day(f) == days as u32 + 2 && f.key().1 == 101)
        );
    }
    let people: Vec<Participant> = names(8)
        .iter()
        .enumerate()
        .map(|(i, name)| participant(i as i64 + 1, name, "x"))
        .collect();
    let labels = |seed| {
        derive_fixture(seed, &rules(false), &people, &[])
            .into_iter()
            .map(|f| f.label)
            .collect::<Vec<_>>()
    };
    assert_ne!(labels(1), labels(2));
}

fn result(score: [u32; 2], games_won: [u32; 2]) -> MatchResult {
    let winner = match score[0].cmp(&score[1]) {
        std::cmp::Ordering::Greater => Some(1),
        std::cmp::Ordering::Less => Some(2),
        std::cmp::Ordering::Equal => None,
    };
    MatchResult {
        score,
        games_won,
        winner,
    }
}

#[test]
fn table_ranks_by_points_then_games_won_then_fewer_games_lost() {
    let names = names(4);
    let r = |a: usize, b: usize, score, games| {
        (names[a].clone(), names[b].clone(), result(score, games))
    };
    let order = |rows: &[Row]| rows.iter().map(|r| r.name.clone()).collect::<Vec<_>>();

    // Equal points: more games won ranks higher (m1 over m0, m2 over m3).
    let rows = table(&names, &[r(0, 2, [7, 5], [6, 4]), r(1, 3, [9, 3], [7, 3])]);
    assert_eq!(order(&rows), ["m1", "m0", "m2", "m3"]);

    // Equal points and games won: fewer games lost ranks higher. m1 beat m2 in ten
    // games, m0 needed an extra round.
    let rows = table(
        &names[..3],
        &[r(0, 2, [7, 5], [6, 5]), r(1, 2, [7, 5], [6, 4])],
    );
    assert_eq!(order(&rows), ["m1", "m0", "m2"]);
    assert!(tie_groups(&rows).is_empty());

    // A draw is worth DRAW_POINTS; a win by fewer games still outranks it.
    let rows = table(&names, &[r(0, 1, [6, 6], [6, 6]), r(2, 3, [4, 3], [2, 1])]);
    assert_eq!(order(&rows)[0], "m2");
    assert_eq!(rows[1].points, DRAW_POINTS);
    // m0 and m1 are level on everything.
    assert_eq!(tie_groups(&rows), vec![1..3]);
    // A player who left is not in the table.
    let rows = table(&names[..2], &[r(0, 2, [7, 5], [6, 4])]);
    assert_eq!(rows.iter().map(|r| r.played).sum::<u32>(), 0);
}

/// The same pair under the same rules gets the same dice and sides in any league, whatever
/// the league's id or seed, and in either entry order; other rules give other dice.
#[test]
fn same_pair_same_rules_same_seed_across_leagues() {
    let path = temp_db("seeds");
    let mut db = Db::open(&path).unwrap();
    let players = |names: &[&str]| -> Vec<PlayerConfig> {
        names
            .iter()
            .map(|n| PlayerConfig::new(n, "random"))
            .collect()
    };
    let one = db
        .create_league(1, &rules(true), &players(&["A", "B", "C"]), None)
        .unwrap();
    let two = db
        .create_league(2, &rules(true), &players(&["C", "D", "B"]), None)
        .unwrap();
    let three = db
        .create_league(3, &rules(false), &players(&["B", "C"]), None)
        .unwrap();
    let pair = |id: i64| {
        let row = db.league(id).unwrap();
        let participants = db.participants(id).unwrap();
        derive_fixture(row.seed, &row.rules, &participants, &[])
            .into_iter()
            .find(|f| {
                let mut names = [f.model1.as_str(), f.model2.as_str()];
                names.sort();
                names == ["B", "C"]
            })
            .unwrap()
    };
    let (in_one, in_two, in_three) = (pair(one), pair(two), pair(three));
    assert_eq!((&in_one.model1, in_one.seed), (&in_two.model1, in_two.seed));
    assert_eq!(in_one.seed, rules(true).pair_seed("C", "B"));
    assert_ne!(in_one.seed, in_three.seed);
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// A league whose players are built from their configs (local engines only).
fn local_league(path: &std::path::Path, id: i64) -> Arc<League> {
    let db = Db::open(path).unwrap();
    let row = db.league(id).unwrap();
    Arc::new(League {
        db_path: path.to_path_buf(),
        id,
        seed: row.seed,
        rules: row.rules.clone(),
        names: RwLock::new(Vec::new()),
        ids: RwLock::new(HashMap::new()),
        players: RwLock::new(HashMap::new()),
        control: Arc::new(Control::new(MAX_SPEED)),
        protocol: Arc::new(Protocol {
            version: PromptVersion::BgV2,
            order_seed: 9,
            harness: Harness::default(),
        }),
        backoff: (Duration::from_secs(1), Duration::from_secs(1)),
    })
}

/// Plays league `id` to its end with local engines.
async fn play_out(path: &std::path::Path, id: i64) -> State {
    let setup = Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into());
    let db = Db::open(path).unwrap();
    let league = local_league(path, id);
    let mut state = State::default();
    state.sync(&db, &league, &setup).await.unwrap();
    let pending = state.pending.len();
    tokio::time::timeout(
        Duration::from_secs(120),
        play_league(league.clone(), &db, &setup, state),
    )
    .await
    .expect("the league finishes")
    .unwrap();
    let mut after = State {
        seen: HashSet::new(),
        ..State::default()
    };
    after.sync(&db, &league, &setup).await.unwrap();
    assert!(after.pending.is_empty());
    assert!(pending <= after.played.len());
    after
}

/// `(id, player1 name, player2 name, seed, valid)` of every league-stage match.
fn stored_matches(path: &std::path::Path) -> Vec<(i64, String, String, i64, bool)> {
    let conn = rusqlite::Connection::open(path).unwrap();
    let mut statement = conn
        .prepare(
            "SELECT m.id, p1.name, p2.name, m.seed, m.valid FROM matches m
             JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2
             WHERE m.stage = 'league' ORDER BY m.id",
        )
        .unwrap();
    statement
        .query_map([], |r| {
            Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?))
        })
        .unwrap()
        .collect::<rusqlite::Result<_>>()
        .unwrap()
}

/// A late joiner plays only its new pairs: the earlier matches are neither replayed nor
/// changed, and the league plays exactly one match against every participant.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn late_join_plays_only_new_pairs() {
    let path = temp_db("late");
    let mut db = Db::open(&path).unwrap();
    let models: Vec<PlayerConfig> = ["A", "B", "C"]
        .iter()
        .map(|n| PlayerConfig::new(n, "random"))
        .collect();
    let id = db
        .create_league(7, &rules(true), &models, Some("test."))
        .unwrap();
    play_out(&path, id).await;
    let before = stored_matches(&path);
    assert_eq!(before.len(), 3);

    let addition =
        add_player(&mut db, id, &PlayerConfig::new("D", "safest"), "2026-10-15").unwrap();
    assert_eq!(addition.fixtures.len(), 3);
    assert!(addition.fixtures.iter().all(|l| l.contains('D')));
    // Already a participant.
    assert!(add_player(&mut db, id, &PlayerConfig::new("D", "safest"), "x").is_err());
    // Another setup under a known name.
    assert!(add_player(&mut db, id, &PlayerConfig::new("A", "safest"), "x").is_err());
    let (note, status): (String, String) = rusqlite::Connection::open(&path)
        .unwrap()
        .query_row(
            "SELECT note, status FROM leagues WHERE id = ?1",
            [id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(note, "test. D added on 2026-10-15.");
    assert_eq!(status, "running");

    let after = play_out(&path, id).await;
    let stored = stored_matches(&path);
    assert_eq!(&stored[..3], &before[..]);
    assert_eq!(stored.len(), 6);
    assert!(
        stored[3..]
            .iter()
            .all(|m| (m.1 == "D") != (m.2 == "D") && m.4)
    );
    for (_, one, two, seed, _) in &stored[3..] {
        let rules = rules(true);
        assert_eq!(*seed as u64, rules.pair_seed(one, two));
        assert_eq!(rules.sides(one, two), (one.as_str(), two.as_str()));
    }
    assert_eq!(after.played.len(), 6);
    let table = standings(&db, id).unwrap();
    assert!(table.iter().all(|row| row.counts[0] == 3), "{table:?}");
    // D leaves: its matches stay valid but leave the table; nothing is left to play.
    let (_, open) = remove_player(&mut db, id, "D", "test").unwrap();
    assert_eq!(open, 0);
    assert_eq!(standings(&db, id).unwrap().len(), 3);
    assert!(stored_matches(&path).iter().all(|m| m.4));
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// A voided match leaves the table and its pair is played again with the same seed and
/// sides; the void match stays in the database.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn void_replays_the_pair() {
    let path = temp_db("void");
    let mut db = Db::open(&path).unwrap();
    let models: Vec<PlayerConfig> = ["A", "B", "C"]
        .iter()
        .map(|n| PlayerConfig::new(n, "random"))
        .collect();
    let id = db.create_league(3, &rules(false), &models, None).unwrap();
    play_out(&path, id).await;
    let before = stored_matches(&path);
    let voided = before[1].clone();
    assert_eq!(db.void_match(voided.0, "test").unwrap(), vec![id]);
    assert!(db.void_match(voided.0, "again").is_err());
    let table = standings(&db, id).unwrap();
    assert_eq!(table.iter().map(|r| r.counts[0]).sum::<u32>(), 2 * 2);
    let after = play_out(&path, id).await;
    assert_eq!(after.played.len(), 3);
    let stored = stored_matches(&path);
    assert_eq!(stored.len(), 4);
    assert!(!stored[1].4, "the voided match stays, void");
    let replay = &stored[3];
    assert_eq!(
        (&replay.1, &replay.2, replay.3, replay.4),
        (&voided.1, &voided.2, voided.3, true)
    );
    let reason: String = rusqlite::Connection::open(&path)
        .unwrap()
        .query_row(
            "SELECT void_reason FROM matches WHERE id = ?1",
            [voided.0],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(reason, "test");
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// Plays like `random` while `fail` is false; otherwise every decision fails like a
/// provider out of credit.
struct Flaky {
    fail: Arc<std::sync::atomic::AtomicBool>,
}

impl crate::players::Engine for Flaky {
    fn decide(
        &self,
        req: &crate::players::DecisionRequest<'_>,
    ) -> Result<crate::players::Decision> {
        if self.fail.load(std::sync::atomic::Ordering::Relaxed) {
            bail!("402 Payment Required: insufficient credits");
        }
        crate::players::baseline::Baseline::Random.decide(req)
    }
}

/// `(model1, model2, match id, match status, match error)`.
type StageRow = (String, String, i64, String, Option<String>);

/// The league stage's matches.
fn league_stage(path: &std::path::Path) -> Vec<StageRow> {
    let conn = rusqlite::Connection::open(path).unwrap();
    let mut statement = conn
        .prepare(
            "SELECT p1.name, p2.name, m.id, m.status, m.error FROM matches m
             JOIN players p1 ON p1.id = m.player1 JOIN players p2 ON p2.id = m.player2
             WHERE m.stage = 'league' AND m.valid = 1 ORDER BY m.id",
        )
        .unwrap();
    statement
        .query_map([], |r| {
            Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?))
        })
        .unwrap()
        .collect::<rusqlite::Result<_>>()
        .unwrap()
}

/// F fails like a provider out of credit: its matches are deferred with the error
/// stored and only F backs off, so every other match (F's opponents' included)
/// finishes while F still fails, and the league neither stops nor starts its playoffs.
/// A stop request ends the run cleanly; once F works again, the next run resumes F's
/// matches under their match ids and finishes the league.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn a_failing_model_backs_off_while_the_others_play_on_and_its_matches_resume() {
    use crate::players::baseline::Baseline;
    let path = temp_db("flaky");
    let mut db = Db::open(&path).unwrap();
    let names: Vec<String> = ["A", "B", "C", "F"].map(String::from).to_vec();
    let models: Vec<PlayerConfig> = names
        .iter()
        .map(|n| PlayerConfig::new(n, "random"))
        .collect();
    let id = db.create_league(5, &rules(true), &models, None).unwrap();
    let fail = Arc::new(std::sync::atomic::AtomicBool::new(true));
    let setup = Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into());
    let league = || {
        let players = models
            .iter()
            .map(|config| {
                let player = if config.name == "F" {
                    Player::engine("flaky", Box::new(Flaky { fail: fail.clone() }))
                } else {
                    Player::engine("random", Box::new(Baseline::Random))
                };
                (config.name.clone(), Entrant::new(config, player))
            })
            .collect();
        let league = local_league(&path, id);
        let league = Arc::into_inner(league).unwrap();
        Arc::new(League {
            players: RwLock::new(players),
            // Long enough that F is not tried again during the first run.
            backoff: (Duration::from_secs(3600), Duration::from_secs(3600)),
            ..league
        })
    };
    let with_f = |row: &StageRow| row.0 == "F" || row.1 == "F";
    let finished = |row: &StageRow| row.3 == "finished";

    let first = league();
    let mut state = State::default();
    state.sync(&db, &first, &setup).await.unwrap();
    assert_eq!(state.pending.len(), 6);
    let watch = async {
        loop {
            let stage = league_stage(&path);
            if stage
                .iter()
                .filter(|r| !with_f(r))
                .filter(|r| finished(r))
                .count()
                == 3
            {
                break;
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
        first.control.cancel();
    };
    let (stopped, ()) = tokio::time::timeout(Duration::from_secs(120), async {
        tokio::join!(play_league(first.clone(), &db, &setup, state), watch)
    })
    .await
    .expect("the matches without F finish while F fails");
    assert!(
        format!("{:#}", stopped.unwrap_err()).contains("stopped on request"),
        "only the stop request ends the run"
    );
    let stage = league_stage(&path);
    let deferred: Vec<_> = stage.iter().filter(|r| with_f(r)).collect();
    assert_eq!(deferred.len(), 3);
    for row in &deferred {
        assert!(!finished(row), "{row:?}");
        let error = row
            .4
            .as_deref()
            .expect("the failure is stored with the match");
        assert!(error.contains("402 Payment Required"), "{error}");
        assert!(error.starts_with("player "), "{error}");
    }
    let match_ids: Vec<i64> = deferred.iter().map(|r| r.2).collect();
    let (status,): (String,) = rusqlite::Connection::open(&path)
        .unwrap()
        .query_row("SELECT status FROM leagues WHERE id = ?1", [id], |r| {
            Ok((r.get(0)?,))
        })
        .unwrap();
    assert_eq!(
        status, "running",
        "no playoffs or final ranking without F's matches"
    );

    fail.store(false, std::sync::atomic::Ordering::Relaxed);
    let second = league();
    let mut state = State::default();
    state.sync(&db, &second, &setup).await.unwrap();
    assert_eq!(state.pending.len(), 3);
    tokio::time::timeout(
        Duration::from_secs(120),
        play_league(second, &db, &setup, state),
    )
    .await
    .expect("the league finishes")
    .unwrap();
    let stage = league_stage(&path);
    assert_eq!(stage.len(), 6);
    assert!(stage.iter().all(finished), "{stage:?}");
    let resumed: Vec<i64> = stage.iter().filter(|r| with_f(r)).map(|r| r.2).collect();
    assert_eq!(
        resumed, match_ids,
        "F's matches resumed under their match ids"
    );
    let (status, ranking): (String, String) = rusqlite::Connection::open(&path)
        .unwrap()
        .query_row(
            "SELECT status, ranking FROM leagues WHERE id = ?1",
            [id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(status, "finished");
    assert!(ranking.contains('F'));
    drop(db);
    let _ = std::fs::remove_file(&path);
}
