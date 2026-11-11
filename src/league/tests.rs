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
        label: format!("matchday {day}: {model1} v {model2}"),
        matchday: day,
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
    Rules::new(
        1,
        None,
        Some(300),
        "bg-v2",
        9,
        mirror,
        StartPosition::Standard,
    )
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
        let fixture = derive_fixture(11, &rules(false), &people, &[], None);
        let mut pairs: Vec<(i64, i64)> = fixture.iter().map(Fixture::key).collect();
        pairs.sort();
        pairs.dedup();
        assert_eq!(pairs.len(), n * (n - 1) / 2);
        assert_eq!(fixture.len(), pairs.len());
        let days = if n % 2 == 0 { n - 1 } else { n };
        for day in 1..=days as u32 {
            let mut seen: Vec<&String> = fixture
                .iter()
                .filter(|f| f.matchday == day)
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
        let with_late = derive_fixture(11, &rules(false), &people, &[], None);
        assert_eq!(&with_late[..fixture.len()].len(), &fixture.len());
        for (old, new) in fixture.iter().zip(&with_late) {
            assert_eq!((&old.label, old.seed), (&new.label, new.seed));
        }
        let day = |f: &Fixture| f.matchday;
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
        derive_fixture(seed, &rules(false), &people, &[], None)
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
fn table_ranks_by_points_then_games_won_then_fewer_games_lost_then_error_rate() {
    let names = names(4);
    let r = |a: usize, b: usize, score, games| {
        (names[a].clone(), names[b].clone(), result(score, games))
    };
    let order = |rows: &[Row]| rows.iter().map(|r| r.name.clone()).collect::<Vec<_>>();
    let none = HashMap::new();

    // Equal points: more games won ranks higher (m1 over m0, m2 over m3).
    let rows = table(
        &names,
        &[r(0, 2, [7, 5], [6, 4]), r(1, 3, [9, 3], [7, 3])],
        &none,
    );
    assert_eq!(order(&rows), ["m1", "m0", "m2", "m3"]);

    // Equal points and games won: fewer games lost ranks higher. m1 beat m2 in ten
    // games, m0 needed an extra round.
    let rows = table(
        &names[..3],
        &[r(0, 2, [7, 5], [6, 5]), r(1, 2, [7, 5], [6, 4])],
        &none,
    );
    assert_eq!(order(&rows), ["m1", "m0", "m2"]);
    assert_eq!(places(&rows), [1, 2, 3]);

    // A draw is worth DRAW_POINTS; a win by fewer games still outranks it.
    let results = [r(0, 1, [6, 6], [6, 6]), r(2, 3, [4, 3], [2, 1])];
    let rows = table(&names, &results, &none);
    assert_eq!(order(&rows)[0], "m2");
    assert_eq!(rows[1].points, DRAW_POINTS);
    // m0 and m1 are level on everything and no error rate is known: they share 2nd place.
    assert_eq!(places(&rows), [1, 2, 2, 4]);
    assert_eq!(ranking(&rows)[..3], ["1. m2", "2. m0", "2. m1"]);
    // The lower error rate breaks the tie; a known error rate ranks before an unknown one.
    let rates: HashMap<String, f64> = [("m0".to_owned(), 30.0), ("m1".to_owned(), 23.4)].into();
    let rows = table(&names, &results, &rates);
    assert_eq!(order(&rows)[1..3], ["m1", "m0"]);
    assert_eq!(places(&rows), [1, 2, 3, 4]);
    let rates: HashMap<String, f64> = [("m0".to_owned(), 30.0)].into();
    assert_eq!(order(&table(&names, &results, &rates))[1..3], ["m0", "m1"]);
    // The error rate never outranks points or games.
    let rates: HashMap<String, f64> = [("m3".to_owned(), 1.0)].into();
    assert_eq!(order(&table(&names, &results, &rates))[3], "m3");
    // A player who left is not in the table.
    let rows = table(&names[..2], &[r(0, 2, [7, 5], [6, 4])], &none);
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
        .create_league(
            1,
            &rules(true),
            &players(&["A", "B", "C"]),
            None,
            &Scope::default(),
        )
        .unwrap();
    let two = db
        .create_league(
            2,
            &rules(true),
            &players(&["C", "D", "B"]),
            None,
            &Scope::default(),
        )
        .unwrap();
    let three = db
        .create_league(
            3,
            &rules(false),
            &players(&["B", "C"]),
            None,
            &Scope::default(),
        )
        .unwrap();
    let pair = |id: i64| {
        let row = db.league(id).unwrap();
        let participants = db.participants(id).unwrap();
        derive_fixture(row.seed, &row.rules, &participants, &[], row.scope.pins())
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
        only_pairs_of: row.scope.only_pairs_of.clone(),
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
        scores: std::env::temp_dir().join("jevgammon-no-scores"),
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
        .create_league(7, &rules(true), &models, Some("test."), &Scope::default())
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
    let open = remove_player(&mut db, id, "D", "test").unwrap();
    assert_eq!(open, 0);
    assert_eq!(standings(&db, id).unwrap().len(), 3);
    assert!(stored_matches(&path).iter().all(|m| m.4));
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// A setup that moves to another league (ladder) keeps its results: a pair it already
/// played anywhere counts in the new league's table and is not played again, whatever
/// rules it was played under; it plays only its new pairs, under the new league's rules,
/// and leaves the old league's table while its matches stay valid.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn a_mover_plays_only_pairs_it_never_played() {
    let path = temp_db("mover");
    let mut db = Db::open(&path).unwrap();
    let players = |names: &[&str]| -> Vec<PlayerConfig> {
        names
            .iter()
            .map(|n| PlayerConfig::new(n, "random"))
            .collect()
    };
    // G is in both leagues, as GNUbg weak is; the leagues play different formats.
    let lower = db
        .create_league(
            1,
            &rules(false),
            &players(&["A", "B", "G"]),
            None,
            &Scope::default(),
        )
        .unwrap();
    let upper = db
        .create_league(
            2,
            &rules(true),
            &players(&["C", "D", "G"]),
            None,
            &Scope::default(),
        )
        .unwrap();
    play_out(&path, lower).await;
    play_out(&path, upper).await;
    assert_eq!(stored_matches(&path).len(), 6);

    assert_eq!(remove_player(&mut db, lower, "A", "promoted").unwrap(), 0);
    let addition = add_player(
        &mut db,
        upper,
        &PlayerConfig::new("A", "random"),
        "2026-10-24",
    )
    .unwrap();
    let mut new_pairs = addition.fixtures.clone();
    new_pairs.sort();
    assert_eq!(new_pairs.len(), 2, "{new_pairs:?}");
    assert!(
        new_pairs
            .iter()
            .all(|l| l.contains('A') && !l.contains('G'))
    );

    let after = play_out(&path, upper).await;
    assert_eq!(after.played.len(), 6);
    let stored = stored_matches(&path);
    assert_eq!(stored.len(), 8);
    assert!(stored.iter().all(|m| m.4), "every match stays valid");
    let mirror: Vec<bool> = {
        let conn = rusqlite::Connection::open(&path).unwrap();
        stored[6..]
            .iter()
            .map(|m| {
                conn.query_row(
                    "SELECT mirror_concurrent FROM matches WHERE id = ?1",
                    [m.0],
                    |r| r.get(0),
                )
                .unwrap()
            })
            .collect()
    };
    assert_eq!(
        mirror,
        [true, true],
        "new matches use the new league's rules"
    );
    let upper_table = standings(&db, upper).unwrap();
    assert!(
        upper_table.iter().all(|row| row.counts[0] == 3),
        "{upper_table:?}"
    );
    let lower_table = standings(&db, lower).unwrap();
    assert_eq!(lower_table.len(), 2);
    assert!(
        lower_table.iter().all(|row| row.counts[0] == 1),
        "{lower_table:?}"
    );
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// An early start (`Scope`): a league that plays only one setup's pairs plays exactly those
/// it never played, under its rules (the same dice as any league with the same rules), and
/// neither plays nor waits for the other pairs; its matches count later in the league the
/// setup joins, which then has nothing left to play for it.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn an_early_start_plays_only_its_setups_pairs() {
    let path = temp_db("early");
    let mut db = Db::open(&path).unwrap();
    let players = |names: &[&str]| -> Vec<PlayerConfig> {
        names
            .iter()
            .map(|n| PlayerConfig::new(n, "random"))
            .collect()
    };
    let main = db
        .create_league(
            1,
            &rules(true),
            &players(&["A", "B", "C"]),
            None,
            &Scope::default(),
        )
        .unwrap();
    play_out(&path, main).await;
    assert_eq!(stored_matches(&path).len(), 3);

    let scope = Scope {
        only_pairs_of: Some("X".into()),
        hidden: true,
        ..Scope::default()
    };
    // The setup must be one of the players.
    assert!(
        db.create_league(1, &rules(true), &players(&["A", "B"]), None, &scope)
            .is_err()
    );
    // E is a newcomer too: its pairs with A, B and C stay unplayed.
    let early = db
        .create_league(
            1,
            &rules(true),
            &players(&["A", "B", "C", "E", "X"]),
            None,
            &scope,
        )
        .unwrap();
    assert_eq!(db.league(early).unwrap().scope, scope);
    let after = play_out(&path, early).await;
    assert_eq!(after.fixtures.len(), 4);
    assert_eq!(after.played.len(), 4);
    let stored = stored_matches(&path);
    assert_eq!(stored.len(), 7);
    for (_, one, two, seed, valid) in &stored[3..] {
        assert!(*valid && (one == "X") != (two == "X"), "{one} v {two}");
        assert_eq!(*seed as u64, rules(true).pair_seed(one, two));
        assert_eq!(rules(true).sides(one, two), (one.as_str(), two.as_str()));
    }
    let table = standings(&db, early).unwrap();
    let played = |name: &str| table.iter().find(|r| r.name == name).unwrap().counts[0];
    assert_eq!((played("X"), played("E"), played("A")), (4, 1, 1));

    // The ladder later moves X into the main league: its pairs there are already played.
    let addition = add_player(
        &mut db,
        main,
        &PlayerConfig::new("X", "random"),
        "2026-10-25",
    )
    .unwrap();
    assert!(addition.fixtures.is_empty(), "{:?}", addition.fixtures);
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// Error rates come from the score shards: 500 × mean loss over a setup's scored decisions
/// in valid matches; decisions skipped by GNUbg and decisions not scored yet are counted
/// apart, and a voided match's decisions are left out.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn error_rates_come_from_the_score_shards_of_valid_matches() {
    let path = temp_db("rates");
    let mut db = Db::open(&path).unwrap();
    let models: Vec<PlayerConfig> = ["A", "B", "C"]
        .iter()
        .map(|n| PlayerConfig::new(n, "random"))
        .collect();
    let id = db
        .create_league(5, &rules(true), &models, None, &Scope::default())
        .unwrap();
    play_out(&path, id).await;
    let decisions = |name: &str| -> Vec<i64> {
        let mut statement = db
            .conn()
            .prepare(
                "SELECT t.id FROM turns t JOIN games g ON g.id = t.game_id
                 JOIN matches m ON m.id = g.match_id
                 JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
                 WHERE p.name = ?1 AND t.decided_by = 'model' AND t.legal_count >= 2
                   AND m.valid = 1 ORDER BY t.id",
            )
            .unwrap();
        statement
            .query_map([name], |r| r.get(0))
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap()
    };
    let (a, b) = (decisions("A"), decisions("B"));
    assert!(a.len() > 2 && b.len() > 2);
    let dir = std::env::temp_dir().join(format!("jevgammon-scores-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    for (shard, turns) in [("s0.db", &a), ("s1.db", &b)] {
        let conn = rusqlite::Connection::open(dir.join(shard)).unwrap();
        conn.execute_batch(
            "CREATE TABLE plays (turn_id INTEGER PRIMARY KEY, loss REAL);
             CREATE TABLE skipped (turn_id INTEGER PRIMARY KEY, reason TEXT);",
        )
        .unwrap();
        let loss = if shard == "s0.db" { 0.01 } else { 0.03 };
        // A's last decision is not scored yet; B's first one was skipped.
        for &turn in &turns[..turns.len() - usize::from(shard == "s0.db")] {
            if shard == "s1.db" && turn == turns[0] {
                conn.execute("INSERT INTO skipped VALUES (?1, 'test')", [turn])
                    .unwrap();
            } else {
                conn.execute("INSERT INTO plays VALUES (?1, ?2)", (turn, loss))
                    .unwrap();
            }
        }
    }
    let rates = scores::error_rates(&db, &dir).unwrap();
    let rate_a = rates["A"];
    assert_eq!(
        (rate_a.scored, rate_a.pending, rate_a.skipped),
        (a.len() as u64 - 1, 1, 0)
    );
    assert!((rate_a.rate().unwrap() - 5.0).abs() < 1e-9);
    let rate_b = rates["B"];
    assert_eq!(
        (rate_b.scored, rate_b.pending, rate_b.skipped),
        (b.len() as u64 - 1, 0, 1)
    );
    assert!((rate_b.rate().unwrap() - 15.0).abs() < 1e-9);
    assert_eq!(rates["C"].rate(), None);
    // A voided match's decisions leave the error rate.
    let match_of_a: i64 = db
        .conn()
        .query_row(
            "SELECT g.match_id FROM turns t JOIN games g ON g.id = t.game_id WHERE t.id = ?1",
            [a[0]],
            |r| r.get(0),
        )
        .unwrap();
    db.void_match(match_of_a, "test").unwrap();
    let after = scores::error_rates(&db, &dir).unwrap()["A"];
    assert!(after.scored + after.pending < rate_a.scored + rate_a.pending);
    drop(db);
    let _ = std::fs::remove_dir_all(&dir);
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
    let id = db
        .create_league(3, &rules(false), &models, None, &Scope::default())
        .unwrap();
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
/// finishes while F still fails, and the league neither stops nor ranks.
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
    let id = db
        .create_league(5, &rules(true), &models, None, &Scope::default())
        .unwrap();
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
    assert_eq!(status, "running", "no final ranking without F's matches");

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

/// A config without `start_position` starts from the standard position, as before; a
/// Nackgammon start is refused unless the prompt version names it (bg-v3-nack).
#[test]
fn the_start_defaults_to_standard_and_needs_a_matching_prompt() {
    let parse = |json: &str| serde_json::from_str::<LeagueConfig>(json).unwrap();
    let plain = parse(r#"{"players": [], "prompt_version": "bg-v2"}"#);
    assert_eq!(plain.start_position, None);
    let nack =
        parse(r#"{"players": [], "prompt_version": "bg-v3-nack", "start_position": "nackgammon"}"#);
    assert_eq!(nack.start_position, Some(StartPosition::Nackgammon));
    assert!(
        serde_json::from_str::<LeagueConfig>(r#"{"players": [], "start_position": "nack"}"#)
            .is_err()
    );

    assert_eq!(match_version(&rules(false)).unwrap(), PromptVersion::BgV2);
    let with = |prompt: Option<&str>, start: StartPosition| Rules {
        prompt_version: prompt.map(str::to_owned),
        start_position: start,
        ..rules(false)
    };
    assert_eq!(
        match_version(&with(Some("bg-v3-nack"), StartPosition::Nackgammon)).unwrap(),
        PromptVersion::BgV3Nack
    );
    // A league stored before prompt versions sent bg-v2-history: standard only.
    assert_eq!(
        match_version(&with(None, StartPosition::Standard)).unwrap(),
        PromptVersion::BgV2History
    );
    for prompt in [
        None,
        Some("bg-v2"),
        Some("nack-v2"),
        Some("bg-v3-std-notable"),
    ] {
        assert!(match_version(&with(prompt, StartPosition::Nackgammon)).is_err());
    }
    assert!(match_version(&with(Some("bg-v3-nack"), StartPosition::Standard)).is_err());
}

/// A league whose rules refuse its prompt version is not created.
#[tokio::test]
async fn a_mismatched_nackgammon_league_is_not_created() {
    let path = temp_db("nack-mismatch");
    let setup = Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into());
    let start = Start::New {
        models: vec![
            PlayerConfig::new("random", "random"),
            PlayerConfig::new("safest", "safest"),
        ],
        seed: 1,
        rules: Rules {
            start_position: StartPosition::Nackgammon,
            ..rules(false)
        },
        note: None,
        scope: Scope::default(),
    };
    let mut league_id = None;
    let error = run_inner(
        &path,
        &setup,
        start,
        Harness::default(),
        std::env::temp_dir(),
        &mut league_id,
    )
    .await
    .unwrap_err();
    assert!(format!("{error:#}").contains("use bg-v3-nack"), "{error:#}");
    assert_eq!(league_id, None);
    let count: i64 = Db::open(&path)
        .unwrap()
        .conn()
        .query_row("SELECT COUNT(*) FROM leagues", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 0);
    for suffix in ["", "-wal", "-shm"] {
        let _ = std::fs::remove_file(format!("{}{suffix}", path.display()));
    }
}

/// A pinned pair (`Scope::pinned_pairs`): (opponent, seed, seat_first).
fn pins(list: &[(&str, u64, bool)]) -> PinnedPairs {
    list.iter()
        .map(|&(name, seed, seat_first)| {
            (name.to_owned(), crate::db::PinnedPair { seed, seat_first })
        })
        .collect()
}

fn pinned_scope(owner: &str, list: &[(&str, u64, bool)]) -> Scope {
    Scope {
        only_pairs_of: Some(owner.into()),
        hidden: true,
        pinned_pairs: pins(list),
    }
}

/// Without pins, nothing changes: an empty pin set, or pins of a setup outside the league
/// or for other opponents, give the very fixture (seeds, seats, order) of no pins at all;
/// and the name-derived seed is still the one stored for an original late-entry match
/// (#808, Base Labs Mammoth-1 v Safest under League 1's rules).
#[test]
fn without_pins_every_fixture_and_seed_is_unchanged() {
    let people: Vec<Participant> = names(6)
        .iter()
        .enumerate()
        .map(|(i, name)| participant(i as i64 + 1, name, "2026-10-01"))
        .collect();
    let plain = derive_fixture(11, &rules(true), &people, &[], None);
    let empty = PinnedPairs::new();
    let elsewhere = pins(&[("m1", 42, true)]);
    let unrelated = pins(&[("nobody", 42, true)]);
    for with in [
        derive_fixture(11, &rules(true), &people, &[], Some(("m0", &empty))),
        derive_fixture(
            11,
            &rules(true),
            &people,
            &[],
            Some(("outsider", &elsewhere)),
        ),
        derive_fixture(11, &rules(true), &people, &[], Some(("m0", &unrelated))),
    ] {
        assert_eq!(with, plain);
    }
    // A pin touches its own pair only.
    let one = derive_fixture(11, &rules(true), &people, &[], Some(("m0", &elsewhere)));
    for (a, b) in one.iter().zip(&plain) {
        let pinned = [a.model1.as_str(), a.model2.as_str()].contains(&"m0")
            && [a.model1.as_str(), a.model2.as_str()].contains(&"m1");
        if !pinned {
            assert_eq!(a, b);
        }
    }
    let original = original_matches()
        .into_iter()
        .find(|m| m.id == 808)
        .unwrap();
    let l1 = original.rules();
    assert_eq!(l1.pair_seed("Base Labs Mammoth-1", "Safest"), original.seed);
    assert_eq!(
        l1.sides("Base Labs Mammoth-1", "Safest").0,
        original.player1
    );
}

/// A pinned pair takes the exact u64 seed (above i64::MAX too) and seating, stored and read
/// back unchanged; a league without pins stores NULL.
#[test]
fn a_pinned_pair_takes_its_exact_seed_and_seating() {
    let people: Vec<Participant> = ["R", "A", "B"]
        .iter()
        .enumerate()
        .map(|(i, name)| participant(i as i64 + 1, name, "2026-10-01"))
        .collect();
    let big = u64::MAX - 12_345;
    let set = pins(&[("A", big, true), ("B", 7, false)]);
    let fixture = derive_fixture(3, &rules(true), &people, &[], Some(("R", &set)));
    let pair = |x: &str| {
        fixture
            .iter()
            .find(|f| {
                [f.model1.as_str(), f.model2.as_str()].contains(&x)
                    && [f.model1.as_str(), f.model2.as_str()].contains(&"R")
            })
            .unwrap()
            .clone()
    };
    let (ra, rb) = (pair("A"), pair("B"));
    assert_eq!(
        (ra.model1.as_str(), ra.model2.as_str(), ra.seed),
        ("R", "A", big)
    );
    assert_eq!(
        (rb.model1.as_str(), rb.model2.as_str(), rb.seed),
        ("B", "R", 7)
    );
    let ab = fixture.iter().find(|f| f.key() == (2, 3)).unwrap();
    assert_eq!(ab.seed, rules(true).pair_seed("A", "B"));

    let path = temp_db("pins-store");
    let mut db = Db::open(&path).unwrap();
    let players: Vec<PlayerConfig> = ["R", "A"]
        .iter()
        .map(|n| PlayerConfig::new(n, "random"))
        .collect();
    let id = db
        .create_league(
            3,
            &rules(true),
            &players,
            None,
            &pinned_scope("R", &[("A", big, true), ("B", 7, false)]),
        )
        .unwrap();
    assert_eq!(db.league(id).unwrap().scope.pinned_pairs, set);
    let plain = db
        .create_league(3, &rules(true), &players, None, &Scope::default())
        .unwrap();
    let stored: Option<String> = rusqlite::Connection::open(&path)
        .unwrap()
        .query_row(
            "SELECT pinned_pairs FROM leagues WHERE id = ?1",
            [plain],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(stored, None);
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// Pins hold across a resume and a league-add: the pinned pair already in the league plays
/// with its pin, a resumed league keeps it, and an opponent added later (with its pin given
/// again, unchanged) plays with its own pin. Earlier rows are never edited.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn pins_hold_across_resume_and_league_add() {
    let path = temp_db("pins-resume");
    let mut db = Db::open(&path).unwrap();
    let players: Vec<PlayerConfig> = ["R", "A"]
        .iter()
        .map(|n| PlayerConfig::new(n, "random"))
        .collect();
    let (sa, sb) = (u64::MAX - 1, 1_234_567_890_123);
    let id = db
        .create_league(
            5,
            &rules(true),
            &players,
            None,
            &pinned_scope("R", &[("A", sa, false), ("B", sb, true)]),
        )
        .unwrap();
    play_out(&path, id).await;
    let first = stored_matches(&path);
    assert_eq!(first.len(), 1);
    assert_eq!(
        (first[0].1.as_str(), first[0].2.as_str(), first[0].3 as u64),
        ("A", "R", sa)
    );
    let rows_before = all_match_rows(&path);
    // The same pin again changes nothing; then B joins and the resumed league plays it.
    assert!(!db.set_pinned_pairs(id, &pins(&[("B", sb, true)])).unwrap());
    add_player(&mut db, id, &PlayerConfig::new("B", "random"), "2026-11-11").unwrap();
    play_out(&path, id).await;
    let after = stored_matches(&path);
    assert_eq!(after.len(), 2);
    assert_eq!(
        (after[1].1.as_str(), after[1].2.as_str(), after[1].3 as u64),
        ("R", "B", sb)
    );
    assert_eq!(
        &all_match_rows(&path)[..rows_before.len()],
        &rows_before[..]
    );
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// Every column of every match row, as text, in id order.
fn all_match_rows(path: &std::path::Path) -> Vec<String> {
    let conn = rusqlite::Connection::open(path).unwrap();
    let mut statement = conn.prepare("SELECT * FROM matches ORDER BY id").unwrap();
    let n = statement.column_count();
    statement
        .query_map([], |r| {
            Ok((0..n)
                .map(|i| format!("{:?}", r.get_ref(i).unwrap()))
                .collect::<Vec<_>>()
                .join("|"))
        })
        .unwrap()
        .collect::<rusqlite::Result<_>>()
        .unwrap()
}

/// Pins are validated idempotently: the same pins again are fine (nothing written); another
/// seed or seat for a pinned opponent, a pin against itself, a pin contradicting a played
/// pair's match, pins without only_pairs_of are refused, and a refusal writes nothing.
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn pins_are_validated_idempotently() {
    let path = temp_db("pins-valid");
    let mut db = Db::open(&path).unwrap();
    let players: Vec<PlayerConfig> = ["R", "A"]
        .iter()
        .map(|n| PlayerConfig::new(n, "random"))
        .collect();
    assert!(
        db.create_league(
            5,
            &rules(true),
            &players,
            None,
            &Scope {
                pinned_pairs: pins(&[("A", 1, true)]),
                ..Scope::default()
            }
        )
        .is_err()
    );
    assert!(
        db.create_league(
            5,
            &rules(true),
            &players,
            None,
            &pinned_scope("R", &[("R", 1, true)])
        )
        .is_err()
    );
    let id = db
        .create_league(
            5,
            &rules(true),
            &players,
            None,
            &pinned_scope("R", &[("A", 11, true)]),
        )
        .unwrap();
    assert!(!db.set_pinned_pairs(id, &pins(&[("A", 11, true)])).unwrap());
    assert!(db.set_pinned_pairs(id, &pins(&[("A", 12, true)])).is_err());
    assert!(db.set_pinned_pairs(id, &pins(&[("A", 11, false)])).is_err());
    assert!(
        db.set_pinned_pairs(id, &pins(&[("C", 3, true), ("A", 12, true)]))
            .is_err()
    );
    assert_eq!(
        db.league(id).unwrap().scope.pinned_pairs,
        pins(&[("A", 11, true)])
    );
    assert!(db.set_pinned_pairs(id, &pins(&[("C", 3, true)])).unwrap());
    assert!(
        !db.set_pinned_pairs(id, &pins(&[("C", 3, true), ("A", 11, true)]))
            .unwrap()
    );
    play_out(&path, id).await;
    let rows = all_match_rows(&path);
    // R v A is played with seed 11: a new league may pin it the same way, never otherwise.
    let again = db
        .create_league(
            6,
            &rules(true),
            &players,
            None,
            &pinned_scope("R", &[("A", 11, true)]),
        )
        .unwrap();
    assert!(
        db.create_league(
            6,
            &rules(true),
            &players,
            None,
            &pinned_scope("R", &[("A", 99, true)])
        )
        .is_err()
    );
    assert!(
        db.set_pinned_pairs(again, &pins(&[("A", 11, false)]))
            .is_err()
    );
    let plain = db
        .create_league(7, &rules(true), &players, None, &Scope::default())
        .unwrap();
    assert!(
        db.set_pinned_pairs(plain, &pins(&[("A", 11, true)]))
            .is_err()
    );
    assert_eq!(all_match_rows(&path), rows);
    drop(db);
    let _ = std::fs::remove_file(&path);
}

/// An original match as read from v3.db (src/league/testdata/repeat_originals.json).
#[derive(Deserialize)]
struct Original {
    id: i64,
    player1: String,
    player2: String,
    seed: u64,
    rounds: u32,
    max_turns: u32,
    prompt_version: String,
    order_seed: u64,
    mirror_concurrent: bool,
    games: Vec<OriginalGame>,
    /// round, leg, turn_no, side, player, die1, die2, position, legal_count, chosen_index,
    /// option_order, decided_by
    turns: Vec<OriginalTurn>,
}

#[derive(Deserialize, Debug, PartialEq)]
struct OriginalGame {
    round: u32,
    leg: u8,
    white_player: u8,
    dice_seed: u64,
    opening: [u8; 2],
}

type OriginalTurn = (
    u32,
    u8,
    u32,
    String,
    u8,
    u8,
    u8,
    String,
    u32,
    Option<usize>,
    Option<String>,
    String,
);

impl Original {
    fn rules(&self) -> Rules {
        Rules::new(
            self.rounds,
            None,
            Some(self.max_turns),
            &self.prompt_version,
            self.order_seed,
            self.mirror_concurrent,
            StartPosition::Standard,
        )
    }
}

fn original_matches() -> Vec<Original> {
    #[derive(Deserialize)]
    struct File {
        matches: Vec<Original>,
    }
    serde_json::from_str::<File>(include_str!("testdata/repeat_originals.json"))
        .unwrap()
        .matches
}

/// Plays the original's choices: the play index each turn of the original match chose.
struct Replay {
    choices: HashMap<(u32, u8, u32), usize>,
}

impl crate::players::Engine for Replay {
    fn decide(
        &self,
        req: &crate::players::DecisionRequest<'_>,
    ) -> Result<crate::players::Decision> {
        let index = self
            .choices
            .get(&(req.round, req.leg, req.turn_no))
            .copied()
            .with_context(|| {
                format!(
                    "no original choice for round {} game {} turn {}",
                    req.round, req.leg, req.turn_no
                )
            })?;
        Ok(crate::players::Decision::new(index))
    }
}

/// A repeat under another name, its pair pinned to the original match's seed and seating,
/// with both players making the original's choices, replays every game's dice and every
/// decision's option order exactly: #808 (Base Labs Mammoth-1 v Safest) and one match of
/// each repeat (Drex Max v1 #856, REAX 1.3 #905, Liquid d1-ultra #190, mirror games off).
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn a_pinned_repeat_replays_the_originals_dice_and_option_orders() {
    let setup = Setup::new(std::env::temp_dir(), "http://127.0.0.1:9/v1".into());
    let entrants = [
        "Base Labs Mammoth-1",
        "Drex Max v1",
        "REAX 1.3",
        "Liquid d1-ultra",
    ];
    for original in original_matches() {
        let entrant = entrants
            .iter()
            .find(|e| [&original.player1, &original.player2].contains(&&e.to_string()))
            .unwrap();
        let opponent = if original.player1 == *entrant {
            &original.player2
        } else {
            &original.player1
        };
        let repeat = format!("{entrant} [repeat 1]");
        let path = temp_db(&format!("pins-replay-{}", original.id));
        let mut db = Db::open(&path).unwrap();
        let configs = vec![
            PlayerConfig::new(&repeat, "random"),
            PlayerConfig::new(opponent, "random"),
        ];
        let scope = pinned_scope(
            &repeat,
            &[(opponent, original.seed, original.player1 == *entrant)],
        );
        let id = db
            .create_league(1, &original.rules(), &configs, None, &scope)
            .unwrap();
        let choices: HashMap<(u32, u8, u32), usize> = original
            .turns
            .iter()
            .filter_map(|t| t.9.map(|index| ((t.0, t.1, t.2), index)))
            .collect();
        let players = configs
            .iter()
            .map(|config| {
                let player = Player::engine(
                    "replay",
                    Box::new(Replay {
                        choices: choices.clone(),
                    }),
                );
                (config.name.clone(), Entrant::new(config, player))
            })
            .collect();
        let league = Arc::into_inner(local_league(&path, id)).unwrap();
        let league = Arc::new(League {
            players: RwLock::new(players),
            protocol: Arc::new(Protocol {
                version: PromptVersion::BgV2,
                order_seed: original.order_seed,
                harness: Harness::default(),
            }),
            ..league
        });
        let mut state = State::default();
        state.sync(&db, &league, &setup).await.unwrap();
        tokio::time::timeout(
            Duration::from_secs(120),
            play_league(league.clone(), &db, &setup, state),
        )
        .await
        .expect("the league finishes")
        .unwrap();
        let conn = rusqlite::Connection::open(&path).unwrap();
        let (p1, seed): (String, i64) = conn
            .query_row("SELECT p.name, m.seed FROM matches m JOIN players p ON p.id = m.player1 WHERE m.valid = 1", [], |r| Ok((r.get(0)?, r.get(1)?)))
            .unwrap();
        let first = if original.player1 == *entrant {
            &repeat
        } else {
            opponent
        };
        assert_eq!(
            (&p1, seed as u64),
            (first, original.seed),
            "#{}",
            original.id
        );
        let games: Vec<OriginalGame> = conn
            .prepare("SELECT round_no, leg, white_player, dice_seed, opening_white, opening_black FROM games ORDER BY round_no, leg")
            .unwrap()
            .query_map([], |r| {
                Ok(OriginalGame {
                    round: r.get(0)?,
                    leg: r.get(1)?,
                    white_player: r.get(2)?,
                    dice_seed: r.get::<_, i64>(3)? as u64,
                    opening: [r.get(4)?, r.get(5)?],
                })
            })
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap();
        assert_eq!(games, original.games, "#{}: games", original.id);
        let turns: Vec<OriginalTurn> = conn
            .prepare(
                "SELECT g.round_no, g.leg, t.turn_no, t.side, t.player, t.die1, t.die2, t.position, t.legal_count,
                        t.chosen_index, t.option_order, t.decided_by
                 FROM turns t JOIN games g ON g.id = t.game_id ORDER BY g.round_no, g.leg, t.turn_no",
            )
            .unwrap()
            .query_map([], |r| {
                Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?, r.get(5)?, r.get(6)?, r.get(7)?, r.get(8)?,
                    r.get::<_, Option<i64>>(9)?.map(|i| i as usize), r.get(10)?, r.get(11)?))
            })
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap();
        assert_eq!(turns.len(), original.turns.len(), "#{}: turns", original.id);
        for (got, want) in turns.iter().zip(&original.turns) {
            assert_eq!(got, want, "#{}", original.id);
        }
        drop(conn);
        drop(db);
        for suffix in ["", "-wal", "-shm"] {
            let _ = std::fs::remove_file(format!("{}{suffix}", path.display()));
        }
    }
}
