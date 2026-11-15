//! The local world: a port of sim/cal/world.ts (same draws, same float operations in the same order).
use crate::data::*;
use std::fmt::Write;
use std::rc::Rc;

macro_rules! params {
    ($name:ident { $($k:ident : $v:expr),* $(,)? }) => {
        #[allow(non_snake_case)]
        #[derive(Clone, Debug)]
        pub struct $name { $(pub $k: f64),* }
        impl Default for $name { fn default() -> Self { Self { $($k: $v as f64),* } } }
        impl $name {
            pub fn set(&mut self, key: &str, value: f64) -> bool {
                match key { $(stringify!($k) => { self.$k = value; true })* _ => false }
            }
            pub fn names() -> Vec<&'static str> { vec![$(stringify!($k)),*] }
        }
    };
}
pub(crate) use params;

params!(SimP {
    F: 1.763,
    tau: 0.5,
    outMu: 2569.5668,
    outSd: 1.0346,
    workBase: 0.0866,
    workGig: 0.1199,
    workSat: 0.35,
    knowWeek: 0.4787,
    lookPerH: 0.236,
    wait: 0.1647,
    belief0: 1.5,
    learn: 0.1,
    dropBase: 0.0133,
    dropThin: 0.2263,
    maxGigs: 2,
    evening: 0.25,
    weekend: 0.3,
    r#priv: 0.15,
    homeMu: 16.141,
    homeSd: 0.9528,
    maxDriveMu: 10.8543,
    maxDriveSd: 0.8473,
    freeFrom: 8,
    notifyP: 0.8065,
    dealerShift: -0.05,
    choiceAlpha: 10,
    dropHold: 0.1424,
    notifyDelay: 92.706,
    workPow: 1,
    busyMin: 600,
});

pub const KIND_NAME: [&str; 3] = ["same_day", "next_day", "within_3_days"];
pub const REASON_NAME: [&str; 4] = ["not_ready", "closed", "licence", "no_plates"];

#[derive(Clone, Debug)]
pub struct Stop {
    pub order: usize,
    pub leg: usize,
    pub pickup: bool,
    pub window: Option<(f64, f64)>,
    pub with_plates: bool,
    pub with_charging: bool,
}
pub type Schedule = Vec<(f64, f64)>;
#[derive(Clone, Debug)]
pub struct Post {
    pub stops: Vec<Stop>,
    pub experienced: bool,
    pub manual: bool,
    pub schedule: Schedule,
}
#[derive(Clone, Debug)]
pub enum Action {
    Quote {
        req: usize,
        prices: [Option<f64>; 3],
    },
    Post(Post),
    Reprice {
        gig: usize,
        schedule: Schedule,
    },
    Withdraw {
        gig: usize,
    },
}
/// What the desk answers to. `at` is the world minute at which the event was emitted.
#[derive(Clone, Copy, Debug)]
pub enum Ev {
    Request(usize),
    Won {
        order: usize,
        last_pickup_at: f64,
    },
    Lost(usize),
    VisitFailed {
        order: usize,
        leg: usize,
        reason: u8,
    },
    Expired(usize),
    DeadlineClose {
        order: usize,
        last_pickup_at: f64,
    },
    Booked(usize),
    Dropped(usize),
    Delivered {
        order: usize,
        leg: usize,
        at: f64,
    },
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum GigStatus {
    Open,
    Booked,
    Working,
    Done,
    Withdrawn,
}

pub struct WOrder {
    pub dealer: usize,
    pub option: usize,
    pub price: f64,
    pub deadline: f64,
    pub legs: Rc<Vec<Leg>>,
    pub delivered: bool,
    pub delivered_at: Vec<Option<f64>>,
    pub last_pickup_at: f64,
    gigs: Vec<usize>,
    warned: Vec<f64>,
}

struct GigInfo {
    a_exp: bool,
    a_man: bool,
    s0_from: f64,
    p0: usize,
    p0_priv: bool,
    p0_hours: Option<Hours>,
    drive: f64,
    first: usize,
    last: usize, // usize::MAX: none
    privs: f64,
    stop_pick: Vec<bool>,
    stop_from: Vec<f64>,
    stop_drive: Vec<f64>,
    stop_to: Vec<Option<f64>>,
    stop_dl: Vec<f64>,
    order0: usize,
    aligned: bool,
}
pub struct Gig {
    pub stops: Vec<Stop>,
    pickups: Vec<usize>, // indices into stops
    pub schedule: Schedule,
    pub status: GigStatus,
    posted_at: f64,
    fee: f64,
    driver: usize,
    orders: Vec<usize>,
    first_fee: f64,
    min_day: f64,
    viewers: Vec<u64>,
    info: GigInfo,
}

struct Driver {
    home: usize,
    rating: f64,
    manual: bool,
    completed: f64,
    belief: f64,
    loc: usize,
    busy_until: f64,
    gigs_today: [u8; 32],
    refused: Vec<usize>,
    look_h: u32,
    know: i8,
    booker: bool,
}

#[derive(Clone, Copy)]
enum Q {
    Request(usize),
    Forecast(usize),
    Decide(usize),
    Looks(u32),
    Notify {
        driver: usize,
        gig: usize,
    },
    Warn(usize),
    Expire(usize),
    Plan {
        gig: usize,
        driver: usize,
    },
    Pickup {
        gig: usize,
        driver: usize,
        leg: usize,
    },
    Deliver {
        gig: usize,
        driver: usize,
        leg: usize,
    },
    Free(usize),
}
#[derive(Clone, Copy)]
struct Item {
    at: f64,
    q: Q,
}
/// The event queue: one linked list per world minute, all items in one array. Items of a minute run in the order
/// they were pushed (the order of the sequence numbers in the TypeScript heap); an item with a fraction of a minute
/// is put in its place by time. Items at or after the end of the week are never run, so they are not kept.
struct Queue {
    items: Vec<(Item, u32)>, // item, next in its minute (NIL = last)
    head: Vec<u32>,
    tail: Vec<u32>,
    cur: usize,
}
const NIL: u32 = u32::MAX;
thread_local! {
    static QUEUE_SCRATCH: std::cell::Cell<(Vec<(Item, u32)>, Vec<u32>, Vec<u32>)> = const { std::cell::Cell::new((Vec::new(), Vec::new(), Vec::new())) };
}
impl Drop for Queue {
    fn drop(&mut self) {
        let parts = (std::mem::take(&mut self.items), std::mem::take(&mut self.head), std::mem::take(&mut self.tail));
        QUEUE_SCRATCH.with(|c| c.set(parts));
    }
}
impl Queue {
    fn new() -> Self {
        let n = END as usize + 1;
        // the arrays of the last world played on this thread are used again (no fresh memory per week)
        let (mut items, mut head, mut tail) = QUEUE_SCRATCH.with(|c| c.take());
        items.clear();
        if items.capacity() == 0 { items.reserve(1 << 17); }
        head.clear();
        head.resize(n, NIL);
        tail.clear();
        tail.resize(n, NIL);
        Queue { items, head, tail, cur: n }
    }
    #[inline]
    fn push(&mut self, at: f64, q: Q) {
        if !(at < END) {
            return;
        }
        let i = if at > 0.0 { at as usize } else { 0 };
        let id = self.items.len() as u32;
        let t = self.tail[i];
        if t == NIL {
            self.items.push((Item { at, q }, NIL));
            self.head[i] = id;
            self.tail[i] = id;
        } else if self.items[t as usize].0.at <= at {
            self.items.push((Item { at, q }, NIL));
            self.items[t as usize].1 = id;
            self.tail[i] = id;
        } else {
            // a fraction of a minute: after the last item that is not later
            let mut prev = NIL;
            let mut k = self.head[i];
            while k != NIL && self.items[k as usize].0.at <= at {
                prev = k;
                k = self.items[k as usize].1;
            }
            self.items.push((Item { at, q }, k));
            if prev == NIL { self.head[i] = id; } else { self.items[prev as usize].1 = id; }
        }
        if i < self.cur {
            self.cur = i;
        }
    }
    /// The time of the next item, or infinity.
    #[inline]
    fn peek(&mut self) -> f64 {
        while self.cur < self.head.len() {
            let h = self.head[self.cur];
            if h != NIL {
                return self.items[h as usize].0.at;
            }
            self.cur += 1;
        }
        f64::INFINITY
    }
    /// The item `peek` just showed.
    #[inline]
    fn pop(&mut self) -> Q {
        let h = self.head[self.cur] as usize;
        let (item, next) = self.items[h];
        self.head[self.cur] = next;
        if next == NIL {
            self.tail[self.cur] = NIL;
        }
        item.q
    }
}

// stat slots
pub const ST_LEDGER: usize = 0; // 7 kinds
pub const LEDGER_NAME: [&str; 7] = [
    "revenue",
    "driver_fee",
    "late_refund",
    "failed_visit",
    "waiting",
    "fine",
    "undelivered_penalty",
];
const L_REVENUE: usize = 0;
const L_DRIVER_FEE: usize = 1;
const L_LATE_REFUND: usize = 2;
const L_FAILED_VISIT: usize = 3;
const L_WAITING: usize = 4;
const L_FINE: usize = 5;
const L_UNDELIVERED: usize = 6;
const ST_WARNINGS: usize = 7;
const ST_BOOKINGS: usize = 8;
const ST_BOOK_AT_OPEN: usize = 9;
const ST_BOOK_MIN: usize = 10;
const ST_BOOK60: usize = 11;
const ST_BOOK360: usize = 12;
const ST_BOOKERS: usize = 13;
const ST_DROPS: usize = 14;
const ST_FEE: usize = 15; // + option
const ST_NB: usize = 18; // + bucket
const ST_N: usize = 21;
const ST_REV: usize = 24;
const ST_TYP: usize = 27;
const ST_LATE_B: usize = 30;
const ST_LATE: usize = 33;
const ST_N_NOTE: usize = 36;
const ST_N_PLAIN: usize = 39;
const ST_LATE_NOTE: usize = 42;
const ST_LATE_PLAIN: usize = 45;
pub const N_STAT: usize = 48;
pub fn stat_name(i: usize) -> String {
    match i {
        0..=6 => format!("L_{}", LEDGER_NAME[i]),
        7 => "warnings".into(),
        8 => "bookings".into(),
        9 => "bookAtOpen".into(),
        10 => "bookMin".into(),
        11 => "book60".into(),
        12 => "book360".into(),
        13 => "bookers".into(),
        14 => "drops".into(),
        15..=17 => format!("fee_{}", KIND_NAME[i - 15]),
        18..=20 => format!("n_b{}", i - 18),
        21..=23 => format!("n_{}", KIND_NAME[i - 21]),
        24..=26 => format!("rev_{}", KIND_NAME[i - 24]),
        27..=29 => format!("typ_{}", KIND_NAME[i - 27]),
        30..=32 => format!("late_b{}", i - 30),
        33..=35 => format!("late_{}", KIND_NAME[i - 33]),
        36..=38 => format!("n_note_{}", KIND_NAME[i - 36]),
        39..=41 => format!("n_plain_{}", KIND_NAME[i - 39]),
        42..=44 => format!("late_note_{}", KIND_NAME[i - 42]),
        _ => format!("late_plain_{}", KIND_NAME[i - 45]),
    }
}

pub struct Score {
    pub margin_cents: f64,
    pub won: usize,
    pub on_time: f64,
    pub ranked: bool,
}

pub fn num(x: f64) -> String {
    // the shortest text that reads back as the same number, as JavaScript's String(x) for the values traced
    format!("{}", x)
}

pub struct World<'a> {
    pub st: &'a Static,
    pub data: &'a Seed,
    pub p: SimP,
    pub now: f64,
    seq: u64,
    queue: Queue,
    out: Vec<Ev>,
    woke: bool,
    quotes: Vec<Option<[Option<f64>; 3]>>,
    decided: Vec<bool>,
    /// Shared with the desk, as the request objects are in the TypeScript: the desk replaces the typical fee.
    pub ref_fee: Vec<f64>,
    /// research/supply: money out by order (cents, positive): driver fees; everything else; and whether it ended late.
    pub o_fee: Vec<f64>,
    pub o_tail: Vec<f64>,
    pub o_late: Vec<bool>,
    pub typ_raw: Vec<Option<f64>>,
    pub orders: Vec<Option<WOrder>>,
    pub order_list: Vec<usize>,
    pub gigs: Vec<Gig>,
    drivers: Vec<Driver>,
    margin: f64,
    trust: Vec<(f64, f64)>,
    open_gigs: Vec<usize>,
    working: Vec<Option<Vec<usize>>>,
    n_bookers: f64,
    pub stats: [f64; N_STAT],
    pub touched: [bool; N_STAT],
    pub trace: Option<String>,
    // hash prefixes: fnv("<seed>|<tag>|")
    h_work: u32,
    h_know: u32,
    h_out: u32,
    h_md: u32,
    h_home: u32,
    h_nr: u32,
    h_n: u32,
    h_win: u32,
    h_opt: u32,
    h_drop: u32,
    h_dt: u32,
    h_droph: u32,
    h_dth: u32,
    words: usize,
    /// Bytes that every driver id starts with.
    id_pre: usize,
    /// During the hourly looks: the planned start by (open gig, where the driver is), NaN = not worked out yet.
    tcache: Vec<f64>,
    in_looks: bool,
    /// Per driver: the group of ids that differ in the last byte only, and that byte (u32::MAX: no group).
    id_grp: Vec<(u32, u8)>,
    grp_h: Vec<(u32, u32)>,
    grp_stamp: Vec<u64>,
    post_n: u64,
    /// During the hourly looks: each open gig's fee at this minute.
    fee_cache: Vec<f64>,
    lb_ok: bool,
    pre: &'a SeedPre,
}

impl<'a> World<'a> {
    pub fn new(st: &'a Static, data: &'a Seed, pre_seed: &'a SeedPre, p: SimP, trace: bool) -> Self {
        let pre = |tag: &str| fnv(&format!("{}|{}|", data.seed, tag), FNV0);
        let h_look = pre("look");
        let np = st.np();
        let nd = data.roster.len();
        let mut w = World {
            st,
            data,
            now: 0.0,
            seq: 0,
            queue: Queue::new(),
            out: Vec::new(),
            woke: false,
            quotes: vec![None; data.requests.len()],
            decided: vec![false; data.requests.len()],
            ref_fee: data.requests.iter().map(|r| r.ref_fee).collect(),
            typ_raw: data.requests.iter().map(|r| r.typ_raw).collect(),
            orders: (0..data.requests.len()).map(|_| None).collect(),
            order_list: Vec::new(),
            gigs: Vec::new(),
            drivers: data
                .roster
                .iter()
                .map(|d| Driver {
                    home: d.home,
                    rating: d.rating,
                    manual: d.manual,
                    completed: d.completed,
                    belief: p.belief0,
                    loc: d.home,
                    busy_until: 0.0,
                    gigs_today: [0; 32],
                    refused: Vec::new(),
                    look_h: fnv("|", fnv(&d.id, h_look)),
                    know: -1,
                    booker: false,
                })
                .collect(),
            margin: 0.0,
            o_fee: vec![0.0; data.requests.len()],
            o_tail: vec![0.0; data.requests.len()],
            o_late: vec![false; data.requests.len()],
            trust: Vec::new(),
            open_gigs: Vec::new(),
            working: vec![None; 64],
            n_bookers: 0.0,
            stats: [0.0; N_STAT],
            touched: [false; N_STAT],
            trace: if trace { Some(String::new()) } else { None },
            h_work: pre("work"),
            h_know: pre("know"),
            h_out: pre("out"),
            h_md: pre("md"),
            h_home: pre("home"),
            h_nr: pre("nr"),
            h_n: pre("n"),
            h_win: pre("win"),
            h_opt: pre("opt"),
            h_drop: pre("drop"),
            h_dt: pre("dt"),
            h_droph: pre("droph"),
            h_dth: pre("dth"),
            words: (nd + 63) / 64,
            id_pre: {
                let a = data.roster.first().map_or(&b""[..], |d| d.id.as_bytes());
                data.roster.iter().fold(a.len(), |n, d| n.min(d.id.as_bytes().iter().zip(a).take_while(|(x, y)| x == y).count()))
            },
            tcache: Vec::new(),
            in_looks: false,
            id_grp: Vec::new(),
            grp_h: Vec::new(),
            grp_stamp: Vec::new(),
            post_n: 0,
            fee_cache: Vec::new(),
            pre: pre_seed,
            lb_ok: p.evening >= 0.0 && p.weekend >= 0.0 && p.r#priv >= 0.0 && p.freeFrom >= 0.0 && p.freeFrom < 24.0 && p.F > 0.0,
            p,
        };
        {
            let mut groups = std::collections::HashMap::<&str, u32>::new();
            for d in &data.roster {
                let id = &d.id;
                if id.len() > w.id_pre && id.is_ascii() {
                    let n = groups.len() as u32;
                    let g = *groups.entry(&id[..id.len() - 1]).or_insert(n);
                    w.id_grp.push((g, id.as_bytes()[id.len() - 1]));
                } else {
                    w.id_grp.push((u32::MAX, 0));
                }
            }
            w.grp_h = vec![(0, 0); groups.len()];
            w.grp_stamp = vec![0; groups.len()];
        }
        let n_dealers = data
            .requests
            .iter()
            .map(|r| r.dealer + 1)
            .max()
            .unwrap_or(0);
        w.trust = vec![(0.0, 0.0); n_dealers];
        for (i, r) in data.requests.iter().enumerate() {
            w.push(r.arrived_at, Q::Request(i));
            w.push(r.respond_by, Q::Decide(i));
        }
        for (i, f) in data.forecasts.iter().enumerate() {
            w.push(f.at, Q::Forecast(i));
        }
        let mut h = 7u32;
        while (h as f64) < END / HOUR {
            if h % 24 >= 7 && h % 24 < 23 {
                w.push(h as f64 * HOUR, Q::Looks(h));
            }
            h += 1;
        }
        w
    }

    // ── API used by the desk ──
    pub fn act(&mut self, actions: &[Action]) -> Vec<Option<usize>> {
        actions.iter().map(|a| self.apply(a)).collect()
    }
    /// Runs to the next event that needs an answer, or to `max`. Returns the events emitted on the way.
    pub fn advance(&mut self, actions: &[Action], max: f64) -> (Vec<Option<usize>>, Vec<Ev>) {
        crate::prof!(0);
        let results = self.act(actions);
        loop {
            let next = self.queue.peek();
            if next > max || next >= END {
                self.now = max.min(END);
                break;
            }
            self.now = next;
            self.woke = false;
            while self.queue.peek() == self.now {
                let q = self.queue.pop();
                self.run(q);
            }
            if self.woke {
                break;
            }
        }
        (results, std::mem::take(&mut self.out))
    }
    pub fn score(&self) -> Score {
        let mut late = 0usize;
        for &i in &self.order_list {
            let o = self.orders[i].as_ref().unwrap();
            let fin = if o.delivered_at.iter().all(|t| t.is_some()) {
                o.delivered_at
                    .iter()
                    .fold(f64::NEG_INFINITY, |m, t| m.max(t.unwrap()))
            } else {
                f64::INFINITY
            };
            if fin > o.deadline {
                late += 1;
            }
        }
        let won = self.order_list.len();
        let on_time = if won > 0 {
            1.0 - late as f64 / won as f64
        } else {
            1.0
        };
        Score {
            margin_cents: self.margin,
            won,
            on_time,
            ranked: won > 0 && on_time >= 0.9,
        }
    }
    /// At the end of the world: undelivered orders cost twice their price.
    pub fn close(&mut self) {
        self.now = END;
        for k in 0..self.order_list.len() {
            let i = self.order_list[k];
            let o = self.orders[i].as_ref().unwrap();
            if !o.delivered {
                let cents = -2.0 * o.price;
                self.o_tail[i] += o.price; // the price never came in
                self.o_late[i] = true;
                self.ledger(L_UNDELIVERED, cents, Some(i), None);
            }
        }
    }
    pub fn gig_id(n: usize) -> String {
        format!("G{:05}", n + 1)
    }

    // ── queue, events, account ──
    #[inline]
    fn push(&mut self, at: f64, q: Q) {
        self.queue.push(at, q);
    }
    #[inline]
    fn emit(&mut self, e: Ev, wake: bool) {
        self.out.push(e);
        if wake {
            self.woke = true;
        }
    }
    #[inline]
    fn count(&mut self, k: usize, n: f64) {
        self.stats[k] += n;
        self.touched[k] = true;
    }
    fn ledger(&mut self, kind: usize, cents: f64, order: Option<usize>, gig: Option<usize>) {
        self.margin += cents;
        if let Some(o) = order { if kind != L_DRIVER_FEE && kind != 0 { self.o_tail[o] -= cents; } }
        self.count(ST_LEDGER + kind, cents / 100.0);
        if self.trace.is_some() {
            let o = order.map_or("-".to_string(), |i| self.data.requests[i].id.clone());
            let g = gig.map_or("-".to_string(), Self::gig_id);
            let line = format!(
                "{} ledger {} {} {} {}\n",
                num(self.now),
                LEDGER_NAME[kind],
                num(cents),
                o,
                g
            );
            self.trace.as_mut().unwrap().push_str(&line);
        }
    }
    fn run(&mut self, q: Q) {
        match q {
            Q::Request(i) => {
                if let Some(t) = self.trace.as_mut() {
                    let _ = writeln!(
                        t,
                        "{} price_request {}",
                        num(self.now),
                        self.data.requests[i].id
                    );
                }
                self.emit(Ev::Request(i), true)
            }
            Q::Forecast(_) => {
                if let Some(t) = self.trace.as_mut() {
                    let _ = writeln!(t, "{} forecast", num(self.now));
                }
            }
            Q::Decide(i) => self.decide(i),
            Q::Looks(h) => self.looks(h),
            Q::Notify { driver, gig } => self.look(driver, Some(gig)),
            Q::Warn(o) => self.warn(o),
            Q::Expire(g) => self.expire(g),
            Q::Plan { gig, driver } => self.plan_drop(gig, driver),
            Q::Pickup { gig, driver, leg } => self.pickup(gig, driver, leg),
            Q::Deliver { gig, driver, leg } => self.deliver(gig, driver, leg),
            Q::Free(d) => {
                let dr = &mut self.drivers[d];
                dr.loc = dr.home;
            }
        }
    }

    // ── actions ──
    fn apply(&mut self, a: &Action) -> Option<usize> {
        match a {
            Action::Quote { req, prices } => {
                let r = &self.data.requests[*req];
                if self.now >= r.respond_by || self.decided[*req] {
                    return None;
                }
                self.quotes[*req] = Some(*prices);
                Some(*req)
            }
            Action::Post(p) => self.post(p),
            Action::Reprice { gig, schedule } => {
                let now = self.now;
                let g = self.gigs.get_mut(*gig)?;
                if g.status != GigStatus::Open {
                    return None;
                }
                g.schedule = schedule.clone();
                g.fee = fee_at(&g.schedule, now);
                Some(*gig)
            }
            Action::Withdraw { gig } => {
                let g = self.gigs.get_mut(*gig)?;
                if g.status != GigStatus::Open {
                    return None;
                }
                g.status = GigStatus::Withdrawn;
                self.close_gig(*gig);
                Some(*gig)
            }
        }
    }

    fn post(&mut self, a: &Post) -> Option<usize> {
        crate::prof!(12);
        for s in &a.stops {
            if let Some(w) = s.window {
                if w.1 < self.now {
                    return None;
                }
            }
        }
        let mut orders: Vec<usize> = Vec::with_capacity(2);
        for s in &a.stops {
            if !orders.contains(&s.order) {
                orders.push(s.order);
            }
        }
        for &o in &orders {
            if self.orders[o].is_none() {
                return None;
            }
        }
        let n = self.gigs.len();
        let info = self.gig_info(&a.stops, a.experienced, a.manual, &orders);
        let fee = fee_at(&a.schedule, self.now);
        let first = self.orders[a.stops[0].order].as_ref().unwrap().legs[a.stops[0].leg].p;
        self.gigs.push(Gig {
            stops: a.stops.clone(),
            pickups: (0..a.stops.len()).filter(|&i| a.stops[i].pickup).collect(),
            schedule: a.schedule.clone(),
            status: GigStatus::Open,
            posted_at: self.now,
            fee,
            driver: usize::MAX,
            orders: orders.clone(),
            first_fee: fee,
            min_day: 0.0,
            viewers: vec![0; self.words],
            info,
        });
        for &o in &orders {
            self.orders[o].as_mut().unwrap().gigs.push(n);
        }
        self.open_gigs.push(n);
        let ends = a
            .stops
            .iter()
            .filter_map(|s| s.window.map(|w| w.1))
            .fold(f64::INFINITY, f64::min);
        if ends < f64::INFINITY {
            self.push(ends + 1.0, Q::Expire(n));
        }
        // notifications: drivers living within 30 km of the first pickup hear of it (07:00–23:00)
        let hour = ((self.now % DAY) / HOUR).floor();
        let at = if hour < 7.0 {
            (self.now / DAY).floor() * DAY + 7.0 * HOUR
        } else if hour >= 23.0 {
            ((self.now / DAY).floor() + 1.0) * DAY + 7.0 * HOUR
        } else {
            self.now
        };
        let id = Self::gig_id(n);
        let h_nr = fnv("|", fnv(&id, self.h_nr));
        let h_n = fnv("|", fnv(&id, self.h_n));
        let data = self.data;
        let pre = &data.roster[0].id[..self.id_pre];
        let (h_nr, h_n) = (fnv(pre, h_nr), fnv(pre, h_n));
        // A look can only plan a start between now and the first stop's end (its window, or the order's deadline
        // while that is still ahead): a driver who works on none of those days would look and find nothing.
        let s0 = &a.stops[0];
        let dl = self.orders[s0.order].as_ref().unwrap().deadline;
        let last = match s0.window {
            Some(w) => w.1,
            None => if dl > at + self.p.notifyDelay + 1.0 { dl } else { f64::INFINITY },
        };
        // ... and not before the first pickup can be made: its window's start and the site's hours
        let first_t = {
            let i = &self.gigs[n].info;
            let from = i.s0_from.max(at);
            if i.p0_priv || !i.aligned { from } else { next_open(&i.p0_hours, from) }
        };
        let (day_lo, day_hi) = ((first_t / DAY).floor(), (last / DAY).floor());
        self.post_n += 1;
        let stamp = self.post_n;
        // who can matter: lives near, is in the gig's audience, works on one of those days (in roster order)
        let pre_seed = self.pre;
        let mut cand = [0u64; 32];
        let words = pre_seed.words.min(32);
        assert!(pre_seed.words <= 32);
        let by_day = day_hi < PRE_DAYS as f64 && day_lo >= 0.0;
        for w in 0..words {
            let mut m = pre_seed.near30[first][w];
            if a.experienced { m &= pre_seed.experienced[w]; }
            if a.manual { m &= pre_seed.manual[w]; }
            if by_day {
                let mut any = 0u64;
                let mut day = day_lo as usize;
                while day as f64 <= day_hi { any |= pre_seed.works[day][w]; day += 1; }
                m &= any;
            }
            cand[w] = m;
        }
        for w in 0..words {
          let mut bits = cand[w];
          while bits != 0 {
            let d = w * 64 + bits.trailing_zeros() as usize;
            bits &= bits - 1;
            // the hash of "<gig>|<driver id>": the state after all but the id's last byte is shared by ten drivers
            let (grp, tail) = self.id_grp[d];
            let u = if grp == u32::MAX {
                fin(fnv(&data.roster[d].id[self.id_pre..], h_nr))
            } else {
                let gi = grp as usize;
                if self.grp_stamp[gi] != stamp {
                    self.grp_stamp[gi] = stamp;
                    let mid = &data.roster[d].id[self.id_pre..data.roster[d].id.len() - 1];
                    self.grp_h[gi] = (fnv(mid, h_nr), fnv(mid, h_n));
                }
                fin((self.grp_h[gi].0 ^ tail as u32).wrapping_mul(16777619))
            };
            if u >= self.p.notifyP {
                continue;
            }
            let u2 = if grp == u32::MAX { fin(fnv(&data.roster[d].id[self.id_pre..], h_n)) } else { fin((self.grp_h[grp as usize].1 ^ tail as u32).wrapping_mul(16777619)) };
            let t = at + (u2 * self.p.notifyDelay).floor();
            self.push(t, Q::Notify { driver: d, gig: n });
          }
        }
        for &o in &orders {
            self.schedule_warn(o);
        }
        Some(n)
    }

    fn gig_info(&self, stops: &[Stop], a_exp: bool, a_man: bool, orders: &[usize]) -> GigInfo {
        let st = self.st;
        let leg = |s: &Stop| &self.orders[s.order].as_ref().unwrap().legs[s.leg];
        let s0 = &stops[0];
        let l0 = leg(s0);
        let (mut drive, mut prev, mut first, mut privs) = (0.0, usize::MAX, usize::MAX, 0.0);
        for s in stops {
            if !s.pickup {
                continue;
            }
            let l = leg(s);
            if prev != usize::MAX {
                drive += st.road(prev, l.p);
            }
            drive += st.road(l.p, l.d);
            prev = l.d;
            if first == usize::MAX {
                first = l.p;
            }
            privs = privs + (l.p_priv as u8 as f64) + (l.d_priv as u8 as f64);
        }
        let mut info = GigInfo {
            a_exp,
            a_man,
            s0_from: s0.window.map_or(l0.p_from, |w| w.0),
            p0: l0.p,
            p0_priv: l0.p_priv,
            p0_hours: l0.p_hours,
            drive,
            first,
            last: prev,
            privs,
            stop_pick: Vec::new(),
            stop_from: Vec::new(),
            stop_drive: Vec::new(),
            stop_to: Vec::new(),
            stop_dl: Vec::new(),
            order0: orders[0],
            aligned: l0.p_hours.map_or(true, |h| h.opens % 15.0 == 0.0 && h.closes % 15.0 == 0.0 && h.sat.map_or(true, |s| s[0] % 15.0 == 0.0 && s[1] % 15.0 == 0.0)),
        };
        for s in stops {
            let l = leg(s);
            info.stop_pick.push(s.pickup);
            info.stop_from.push(s.window.map_or(l.p_from, |w| w.0));
            info.stop_drive.push(st.road(l.p, l.d));
            info.stop_to.push(s.window.map(|w| w.1));
            info.stop_dl
                .push(self.orders[s.order].as_ref().unwrap().deadline);
        }
        info
    }
    fn close_gig(&mut self, g: usize) {
        if let Some(i) = self.open_gigs.iter().position(|&x| x == g) {
            self.open_gigs.remove(i);
        }
    }
    fn reopen_gig(&mut self, g: usize) {
        let i = self.open_gigs.partition_point(|&x| x < g);
        self.open_gigs.insert(i, g);
    }

    // ── dealers ──
    fn decide(&mut self, id: usize) {
        crate::prof!(11);
        self.decided[id] = true;
        let data = self.data;
        let st = self.st;
        let r = &data.requests[id];
        let q = self.quotes[id];
        let quoted: Vec<&Opt> = match &q {
            Some(q) => r
                .options
                .iter()
                .filter(|o| matches!(q[o.kind], Some(v) if v < 5.0 * o.list))
                .collect(),
            None => Vec::new(),
        };
        if quoted.is_empty() {
            return self.lost(id);
        }
        let q = q.unwrap();
        // value of speed per option = how often the dealer took it in the played worlds
        let v = |k: usize| (1.0 + r.choice[k]).ln();
        let vmax = r
            .options
            .iter()
            .fold(f64::NEG_INFINITY, |m, o| m.max(v(o.kind)));
        let alpha = self.p.choiceAlpha;
        let eff = |o: &Opt| (q[o.kind].unwrap() / o.list) * ((vmax - v(o.kind)) / alpha).exp();
        let m = quoted.iter().fold(f64::INFINITY, |m, o| m.min(eff(o)));
        let t = self.trust[r.dealer];
        let pickup = r.legs[0].p;
        let drive_h = r.legs.iter().fold(0.0, |s, l| s + st.road(l.p, l.d)) / HOUR;
        let x = ReqX {
            pickup,
            delivery: r.legs[0].d,
            drive_h,
            trade_in: if r.legs.len() > 1 { 1.0 } else { 0.0 },
            priv_d: if r.legs.iter().any(|l| l.d_priv) {
                1.0
            } else {
                0.0
            },
            same_day: if r.options.iter().any(|o| o.kind == 0) {
                1.0
            } else {
                0.0
            },
            n_opt: r.options.len() as f64,
            trust: t.0,
            lates: t.1,
        };
        let day = (r.arrived_at / DAY).floor();
        let off_day = data
            .off_day
            .iter()
            .find(|d| d.0 == day)
            .map_or(0.0, |d| d.1);
        let off_place = data
            .off_place
            .iter()
            .find(|d| d.0 == day && d.1 == pickup)
            .map_or(0.0, |d| d.2);
        let level = data.off_level + off_day + off_place + self.p.dealerShift;
        let chance = win_chance(&st.win, win_base(&st.win, &x), m, level);
        let h_id = fnv(&r.id, self.h_win);
        if fin(h_id) >= chance {
            return self.lost(id);
        }
        // which option: the lowest speed-adjusted multiple; a small fixed random taste breaks ties
        let h_opt = fnv("|", fnv(&r.id, self.h_opt));
        let key = |o: &Opt| eff(o) * (1.0 + 0.01 * fin(fnv(KIND_NAME[o.kind], h_opt)));
        let mut pick = quoted[0];
        let mut best = key(pick);
        for o in &quoted[1..] {
            let k = key(o);
            if k < best {
                best = k;
                pick = o;
            }
        }
        let truth = r.truth.as_ref();
        let ready = r
            .legs
            .iter()
            .enumerate()
            .fold(f64::NEG_INFINITY, |m, (i, l)| {
                m.max(
                    truth
                        .and_then(|t| t[i].as_ref())
                        .map_or(l.p_from, |t| t.ready_at),
                )
            });
        let stated = r
            .legs
            .iter()
            .fold(f64::NEG_INFINITY, |m, l| m.max(l.p_from));
        let mut deadline = move_days(
            pick.deadline,
            ((ready / DAY).floor() - (stated / DAY).floor()).max(0.0),
        );
        let note_dl = truth.map_or(f64::INFINITY, |t| {
            t.iter().flatten().fold(f64::INFINITY, |m, l| {
                m.min(l.note_deadline.unwrap_or(f64::INFINITY))
            })
        });
        if note_dl < deadline {
            deadline = note_dl;
        }
        let legs: Vec<Leg> = r
            .legs
            .iter()
            .map(|l| {
                let mut c = l.clone();
                if !l.p_priv {
                    c.p_to = deadline;
                }
                if !l.d_priv {
                    c.d_to = deadline;
                }
                c
            })
            .collect();
        let mut order = WOrder {
            dealer: r.dealer,
            option: pick.kind,
            price: q[pick.kind].unwrap(),
            deadline,
            legs: Rc::new(legs),
            delivered: false,
            delivered_at: vec![None; r.legs.len()],
            last_pickup_at: 0.0,
            gigs: Vec::new(),
            warned: Vec::new(),
        };
        order.last_pickup_at = self.last_pickup(&order, 0);
        let lp = order.last_pickup_at;
        if let Some(t) = self.trace.as_mut() {
            let _ = writeln!(
                t,
                "{} order_won {} {} {} {} {}",
                num(self.now),
                r.id,
                KIND_NAME[order.option],
                num(order.price),
                num(order.deadline),
                num(lp)
            );
        }
        self.orders[id] = Some(order);
        self.order_list.push(id);
        self.emit(
            Ev::Won {
                order: id,
                last_pickup_at: lp,
            },
            true,
        );
        self.schedule_warn(id);
    }
    fn lost(&mut self, id: usize) {
        if let Some(t) = self.trace.as_mut() {
            let _ = writeln!(
                t,
                "{} order_lost {}",
                num(self.now),
                self.data.requests[id].id
            );
        }
        self.emit(Ev::Lost(id), false);
    }
    /// Last minute to collect the first undelivered car and still deliver every leg by the deadline (stated hours).
    fn last_pickup(&self, o: &WOrder, from_leg: usize) -> f64 {
        let mut drive = 0.0;
        for l in &o.legs[from_leg..] {
            drive += self.st.road(l.p, l.d) + if self.needs_charge(l) { 40.0 } else { 0.0 };
        }
        let mut t = o.deadline - drive;
        let l = &o.legs[from_leg];
        if let (Some(h), false) = (&l.p_hours, l.p_priv) {
            let mut k = 0;
            while k < 5 && !is_open(&l.p_hours, t) {
                let day_start = (t / DAY).floor() * DAY;
                t = if t % DAY >= h.closes {
                    day_start + h.closes - 1.0
                } else {
                    day_start - DAY + h.closes - 1.0
                };
                k += 1;
            }
        }
        t
    }
    #[inline]
    fn needs_charge(&self, l: &Leg) -> bool {
        l.electric && matches!(l.charge, Some(c) if c < 30.0) && self.st.km(l.p, l.d) > 200.0
    }

    // ── deadline warnings ──
    fn has_driver(&self, order: usize) -> bool {
        self.orders[order]
            .as_ref()
            .unwrap()
            .gigs
            .iter()
            .any(|&g| matches!(self.gigs[g].status, GigStatus::Booked | GigStatus::Working))
    }
    fn schedule_warn(&mut self, order: usize) {
        let Some(o) = self.orders[order].as_ref() else {
            return;
        };
        let at = self.now.max(o.last_pickup_at - 3.0 * HOUR);
        self.push(at, Q::Warn(order));
    }
    fn warn(&mut self, order: usize) {
        crate::prof!(19);
        let Some(o) = self.orders[order].as_ref() else {
            return;
        };
        let lp = o.last_pickup_at;
        if o.delivered || self.has_driver(order) || o.warned.contains(&lp) {
            return;
        }
        if self.now < lp - 3.0 * HOUR {
            return;
        }
        self.orders[order].as_mut().unwrap().warned.push(lp);
        if let Some(t) = self.trace.as_mut() {
            let _ = writeln!(
                t,
                "{} deadline_close {} {}",
                num(self.now),
                self.data.requests[order].id,
                num(lp)
            );
        }
        self.emit(
            Ev::DeadlineClose {
                order,
                last_pickup_at: lp,
            },
            true,
        );
        self.count(ST_WARNINGS, 1.0);
    }
    fn expire(&mut self, gig: usize) {
        if self.gigs[gig].status != GigStatus::Open {
            return;
        }
        self.gigs[gig].status = GigStatus::Withdrawn;
        self.close_gig(gig);
        if let Some(t) = self.trace.as_mut() {
            let _ = writeln!(t, "{} gig_expired {}", num(self.now), Self::gig_id(gig));
        }
        self.emit(Ev::Expired(gig), true);
    }

    // ── drivers ──
    #[inline]
    fn works(&mut self, d: usize, day: f64) -> bool {
        let di = day as usize;
        if di < PRE_DAYS {
            return (self.pre.works[di][d / 64] >> (d % 64)) & 1 == 1;
        }
        works_draw(self.data, &self.p, self.h_work, d, day)
    }
    #[inline]
    fn knows(&mut self, d: usize, today: f64, day: f64) -> bool {
        if day <= today + 1.0 {
            return true;
        }
        if self.drivers[d].know < 0 {
            let k = fin(fnv(&self.data.roster[d].id, self.h_know)) < self.p.knowWeek;
            self.drivers[d].know = k as i8;
        }
        self.drivers[d].know == 1
    }
    /// A driver's draws for a day: other options (cents), longest gig (minutes), home time (minutes of the day).
    #[inline]
    fn outside(&mut self, d: usize, day: f64) -> f64 {
        let di = day as usize;
        if di < PRE_DAYS { self.pre.draws[d * PRE_DAYS + di][0] } else { draws(self.data, &self.p, self.h_out, self.h_md, self.h_home, d, day)[0] }
    }
    #[inline]
    fn max_drive(&mut self, d: usize, day: f64) -> f64 {
        let di = day as usize;
        if di < PRE_DAYS { self.pre.draws[d * PRE_DAYS + di][1] } else { draws(self.data, &self.p, self.h_out, self.h_md, self.h_home, d, day)[1] }
    }
    #[inline]
    fn home_at(&mut self, d: usize, day: f64) -> f64 {
        let di = day as usize;
        if di < PRE_DAYS { self.pre.draws[d * PRE_DAYS + di][2] } else { draws(self.data, &self.p, self.h_out, self.h_md, self.h_home, d, day)[2] }
    }
    /// What the gig costs this driver from where they are: the drive, the trips to the pickup and home, extras.
    fn cost(&self, d: usize, g: usize, start: f64) -> f64 {
        let p = &self.p;
        let i = &self.gigs[g].info;
        let dr = &self.drivers[d];
        let per_min = 38.3 / (p.F * (1.0 + p.tau));
        let fixed = 1664.0 / p.F;
        let c = fixed
            + per_min
                * (i.drive
                    + p.tau * (self.st.road(dr.loc, i.first) + self.st.road(i.last, dr.home)));
        let end = start + i.drive;
        let mut extra = 0.0;
        if end % DAY > 18.0 * HOUR {
            extra += p.evening;
        }
        if (start / DAY).floor() % 7.0 == 5.0 {
            extra += p.weekend;
        }
        extra += p.r#priv * i.privs;
        c * (1.0 + extra)
    }
    /// Can this driver do the gig: licence, audience, time windows, their day. Returns the planned start.
    fn feasible(&mut self, d: usize, g: usize) -> Option<f64> {
        crate::prof!(8);
        let st = self.st;
        let now = self.now;
        let (to_pickup, mut t, gdrive, last) = {
            let i = &self.gigs[g].info;
            let dr = &self.drivers[d];
            if i.a_exp && !(dr.rating >= 4.8 && dr.completed >= 50.0) {
                return None;
            }
            if i.a_man && !dr.manual {
                return None;
            }
            let to_pickup = st.road(dr.loc, i.p0);
            let from = i.s0_from.max(now + to_pickup);
            (
                to_pickup,
                if self.in_looks {
                    // every look of this hour is at the same minute: one answer per (gig, place the driver is at)
                    let c = unsafe { &mut *(self.tcache.as_ptr().add(g * st.np() + dr.loc) as *mut f64) };
                    if *c != *c {
                        *c = if i.p0_priv { from } else { next_open(&i.p0_hours, from) };
                    }
                    *c
                } else if i.p0_priv {
                    from
                } else {
                    next_open(&i.p0_hours, from)
                },
                i.drive,
                i.last,
            )
        };
        let day = (t / DAY).floor();
        let today = (now / DAY).floor();
        if day > today && !self.knows(d, today, day) {
            return None;
        }
        if !self.works(d, day) {
            return None;
        }
        {
            let dr = &self.drivers[d];
            if dr.gigs_today[day as usize] as f64 >= self.p.maxGigs || dr.busy_until > t - to_pickup {
                return None;
            }
        }
        if t % DAY > 21.0 * HOUR {
            return None;
        }
        if t % DAY < self.p.freeFrom * HOUR {
            t = (t / DAY).floor() * DAY + self.p.freeFrom * HOUR;
        }
        // the driver's day: longest gig they accept, and when they want to be home
        if gdrive > self.max_drive(d, day) {
            return None;
        }
        let home = day * DAY + self.home_at(d, day);
        let dhome = self.drivers[d].home;
        if t + gdrive
            + (if last == usize::MAX {
                0.0
            } else {
                st.road(last, dhome)
            })
            > home + 2.0 * HOUR
        {
            return None;
        }
        // reach every stop inside its window (stops without their own window: the order's deadline, if not yet past)
        let i = &self.gigs[g].info;
        let mut at = t;
        for k in 0..i.stop_pick.len() {
            if i.stop_pick[k] {
                at = at.max(i.stop_from[k]);
            } else {
                at += i.stop_drive[k];
            }
            let dl = i.stop_dl[k];
            let to = i.stop_to[k].unwrap_or(if dl > now { dl } else { f64::INFINITY });
            if at > to {
                return None;
            }
        }
        Some(t)
    }
    fn looks(&mut self, hour: u32) {
        crate::prof!(15);
        let day = (hour as f64 * HOUR / DAY).floor();
        let di = day as usize;
        if self.working[di].is_none() {
            let list: Vec<usize> = (0..self.drivers.len())
                .filter(|&d| self.works(d, day))
                .collect();
            self.working[di] = Some(list);
        }
        let now = self.now;
        for k in 0..self.open_gigs.len() {
            let g = &mut self.gigs[self.open_gigs[k]];
            let from = g.info.s0_from.max(now);
            // with hours on quarter-hour marks next_open is the first open minute, so a later start is never an earlier day
            let t = if g.info.p0_priv || !g.info.aligned { from } else { next_open(&g.info.p0_hours, from) };
            g.min_day = (t / DAY).floor();
        }
        let np = self.st.np();
        if self.tcache.len() < self.gigs.len() * np {
            self.tcache.resize((self.gigs.len() + 256) * np, f64::NAN);
        }
        for k in 0..self.open_gigs.len() {
            let g = self.open_gigs[k];
            self.tcache[g * np..(g + 1) * np].fill(f64::NAN);
        }
        if self.fee_cache.len() < self.gigs.len() {
            self.fee_cache.resize(self.gigs.len() + 256, 0.0);
        }
        for k in 0..self.open_gigs.len() {
            let g = self.open_gigs[k];
            self.fee_cache[g] = fee_at(&self.gigs[g].schedule, now);
        }
        self.in_looks = true;
        let working = self.working[di].take().unwrap();
        for &d in &working {
            if fin(fnv_int(hour as u64, self.drivers[d].look_h)) >= self.p.lookPerH {
                continue;
            }
            self.look(d, None);
        }
        self.working[di] = Some(working);
        self.in_looks = false;
    }
    fn look(&mut self, d: usize, gig: Option<usize>) {
        crate::prof!(if gig.is_some() { 13 } else { 7 });
        if let Some(g) = gig {
            if self.gigs[g].status != GigStatus::Open {
                return;
            }
        }
        let today = (self.now / DAY).floor();
        if gig.is_none() && !self.works(d, today) {
            return;
        }
        // a gig that cannot start before the day after tomorrow is for drivers who know their week only
        let far_ok = gig.is_some() || self.knows(d, today, today + 2.0);
        let mut best: Option<(usize, f64, f64, f64)> = None; // gig, surplus, start, cost
        let np = self.st.np();
        let mut day_ok = [0u8; 16];
        let n = if gig.is_some() {
            1
        } else {
            self.open_gigs.len()
        };
        for k in 0..n {
            let g = match gig {
                Some(g) => g,
                None => self.open_gigs[k],
            };
            if gig.is_none() {
                // (the list holds open gigs only) the start day is known for this gig from where the driver is:
                // a day they do not work, do not know yet or have filled rules the gig out, as `feasible` would
                let dr = &self.drivers[d];
                if !dr.refused.is_empty() && dr.refused.contains(&g) {
                    continue;
                }
                {
                    let i = &self.gigs[g].info;
                    if (i.a_exp && !(dr.rating >= 4.8 && dr.completed >= 50.0)) || (i.a_man && !dr.manual) {
                        continue;
                    }
                }
                let c = self.tcache[g * np + dr.loc];
                if c == c {
                    let day = (c / DAY).floor();
                    let di = (day - today) as usize;
                    if di < 16 {
                        if day_ok[di] == 0 {
                            let ok = (day <= today || self.knows(d, today, day)) && self.works(d, day) && !(self.drivers[d].gigs_today[day as usize] as f64 >= self.p.maxGigs);
                            day_ok[di] = if ok { 1 } else { 2 };
                        }
                        if day_ok[di] == 2 {
                            continue;
                        }
                        // seen before, and the fee is under what the drive alone costs them plus their other
                        // options that day (extras only add to the cost): no booking, and nothing new to see
                        if self.lb_ok && self.gigs[g].viewers[d / 64] & (1u64 << (d % 64)) != 0 {
                            let (i, dr, p) = (&self.gigs[g].info, &self.drivers[d], &self.p);
                            let per_min = 38.3 / (p.F * (1.0 + p.tau));
                            let fixed = 1664.0 / p.F;
                            let c0 = fixed + per_min * (i.drive + p.tau * (self.st.road(dr.loc, i.first) + self.st.road(i.last, dr.home)));
                            let fee = self.fee_cache[g];
                            if fee < c0 + self.outside(d, day) {
                                continue;
                            }
                        }
                    }
                }
            } else if self.gigs[g].status != GigStatus::Open || self.drivers[d].refused.contains(&g) {
                continue;
            }
            if !far_ok && self.gigs[g].min_day > today + 1.0 {
                continue;
            }
            let Some(start) = self.feasible(d, g) else {
                continue;
            };
            {
                let gg = &mut self.gigs[g];
                let (w, b) = (d / 64, 1u64 << (d % 64));
                if gg.viewers[w] & b == 0 {
                    gg.viewers[w] |= b;
                    if let Some(t) = self.trace.as_mut() {
                        let _ = writeln!(
                            t,
                            "{} gig_viewed {} {}",
                            num(self.now),
                            Self::gig_id(g),
                            self.data.roster[d].id
                        );
                    }
                }
            }
            let fee = if gig.is_none() { self.fee_cache[g] } else { fee_at(&self.gigs[g].schedule, self.now) };
            let cost = self.cost(d, g, start);
            let need = cost + self.outside(d, (start / DAY).floor());
            if fee < need {
                continue;
            }
            // hold out for a raise while the pickup is far: the further, the more
            let gg = &self.gigs[g];
            let hours_left =
                ((self.orders[gg.info.order0].as_ref().unwrap().last_pickup_at - self.now) / HOUR)
                    .max(0.0);
            let hold = self.p.wait
                * (self.drivers[d].belief - 1.0).max(0.0)
                * gg.first_fee
                * (hours_left / 24.0).min(1.0);
            let surplus = fee - need - hold;
            if surplus < 0.0 {
                continue;
            }
            if best.map_or(true, |b| surplus > b.1) {
                best = Some((g, surplus, start, cost));
            }
        }
        if let Some((g, _, start, cost)) = best {
            self.book(d, g, start, cost);
        }
    }
    fn book(&mut self, d: usize, g: usize, start: f64, cost: f64) {
        crate::prof!(16);
        let now = self.now;
        self.gigs[g].status = GigStatus::Booked;
        self.close_gig(g);
        let fee = fee_at(&self.gigs[g].schedule, now);
        {
            let gg = &mut self.gigs[g];
            gg.driver = d;
            gg.fee = fee;
        }
        let day = (start / DAY).floor() as usize;
        self.drivers[d].gigs_today[day] += 1;
        self.drivers[d].busy_until = start + self.p.busyMin;
        if let Some(t) = self.trace.as_mut() {
            let _ = writeln!(
                t,
                "{} gig_booked {} {} {}",
                num(now),
                Self::gig_id(g),
                self.data.roster[d].id,
                num(fee)
            );
        }
        self.emit(Ev::Booked(g), false);
        let (first_fee, posted_at) = (self.gigs[g].first_fee, self.gigs[g].posted_at);
        self.count(ST_BOOKINGS, 1.0);
        if fee == first_fee {
            self.count(ST_BOOK_AT_OPEN, 1.0);
        }
        self.count(ST_BOOK_MIN, now - posted_at);
        if now - posted_at <= 60.0 {
            self.count(ST_BOOK60, 1.0);
        }
        if now - posted_at <= 360.0 {
            self.count(ST_BOOK360, 1.0);
        }
        if !self.drivers[d].booker {
            self.drivers[d].booker = true;
            self.n_bookers += 1.0;
        }
        self.stats[ST_BOOKERS] = self.n_bookers;
        self.touched[ST_BOOKERS] = true;
        // drivers who viewed this order learn how far its fee rose
        let ratio = fee / first_fee.max(1.0);
        let learn = self.p.learn;
        for w in 0..self.words {
            let mut bits = self.gigs[g].viewers[w];
            while bits != 0 {
                let v = w * 64 + bits.trailing_zeros() as usize;
                bits &= bits - 1;
                let o = &mut self.drivers[v];
                o.belief = (1.0 - learn) * o.belief + learn * ratio;
            }
        }
        // planning: a thin booking can be given back (soon after booking, at the latest before the start)
        let surplus_share = ((fee - cost) / fee.max(1.0)).min(1.0).max(0.0);
        let p_drop = self.p.dropBase + self.p.dropThin * (0.3 - surplus_share).max(0.0) / 0.3;
        let gid = Self::gig_id(g);
        let did = &self.data.roster[d].id;
        if fin(fnv(did, fnv("|", fnv(&gid, self.h_drop)))) < p_drop {
            let at = (start - 30.0).min(now + 60.0 + (fin(fnv(&gid, self.h_dt)) * 600.0).floor());
            self.push(at, Q::Plan { gig: g, driver: d });
        } else {
            // the longer a driver holds a booking, the likelier a drop; drops at night are rare
            let hold_h = ((start - now) / HOUR).max(0.0);
            if hold_h > 2.0
                && fin(fnv(did, fnv("|", fnv(&gid, self.h_droph))))
                    < self.p.dropHold * (hold_h / 30.0).min(1.0)
            {
                let mut at = now
                    + 60.0
                    + (fin(fnv(&gid, self.h_dth)) * (start - now - 120.0).max(1.0)).floor();
                let h = ((at % DAY) / HOUR).floor();
                if h >= 23.0 || h < 7.0 {
                    at =
                        (at / DAY).floor() * DAY + (if h >= 23.0 { DAY } else { 0.0 }) + 7.0 * HOUR;
                }
                if at < start - 30.0 {
                    self.push(at, Q::Plan { gig: g, driver: d });
                }
            }
        }
        self.push(
            now.max(start),
            Q::Pickup {
                gig: g,
                driver: d,
                leg: 0,
            },
        );
    }
    fn plan_drop(&mut self, g: usize, d: usize) {
        if self.gigs[g].status != GigStatus::Booked || self.gigs[g].driver != d {
            return;
        }
        self.gigs[g].status = GigStatus::Open;
        self.reopen_gig(g);
        self.gigs[g].driver = usize::MAX;
        self.drivers[d].refused.push(g);
        self.drivers[d].busy_until = 0.0;
        if let Some(t) = self.trace.as_mut() {
            let _ = writeln!(
                t,
                "{} gig_dropped {} {}",
                num(self.now),
                Self::gig_id(g),
                self.data.roster[d].id
            );
        }
        self.emit(Ev::Dropped(g), true);
        self.count(ST_DROPS, 1.0);
        for k in 0..self.gigs[g].orders.len() {
            let o = self.gigs[g].orders[k];
            self.schedule_warn(o);
        }
    }

    // ── driving ──
    fn pickup(&mut self, g: usize, d: usize, leg: usize) {
        crate::prof!(17);
        {
            let gg = &mut self.gigs[g];
            if (gg.status != GigStatus::Booked && gg.status != GigStatus::Working) || gg.driver != d
            {
                return;
            }
            if gg.status == GigStatus::Booked {
                gg.status = GigStatus::Working;
                if let Some(t) = self.trace.as_mut() {
                    let _ = writeln!(
                        t,
                        "{} gig_started {} {}",
                        num(self.now),
                        Self::gig_id(g),
                        self.data.roster[d].id
                    );
                }
            }
        }
        let n_pick = self.gigs[g].pickups.len();
        if leg >= n_pick {
            return self.finish(g);
        }
        let s = self.gigs[g].stops[self.gigs[g].pickups[leg]].clone();
        let legs = self.orders[s.order].as_ref().unwrap().legs.clone();
        let l = &legs[s.leg];
        let data = self.data;
        let tr = data.requests[s.order]
            .truth
            .as_ref()
            .and_then(|t| t.get(s.leg))
            .and_then(|t| t.as_ref());
        let mut t = self.now.max(s.window.map_or(l.p_from, |w| w.0));
        if !l.p_priv {
            t = next_open(&l.p_hours, t);
        }
        let real_open = tr.and_then(|t| t.pickup_hours).or(l.p_hours);
        let mut reason: Option<u8> = None;
        if tr.map_or(false, |tr| {
            t < tr.ready_at || tr.released_at.map_or(false, |r| t < r)
        }) {
            reason = Some(0);
        } else if !l.p_priv && !is_open(&real_open, t) {
            reason = Some(1);
        } else if tr.map_or(false, |tr| tr.manual_gearbox) && !self.drivers[d].manual {
            reason = Some(2);
        } else if tr.map_or(false, |tr| tr.needs_plates) && !s.with_plates {
            reason = Some(3);
        }
        self.now = self.now.max(t);
        if let Some(reason) = reason {
            let share = jround(self.gigs[g].fee / n_pick as f64 / 2.0).max(2500.0);
            self.ledger(L_FAILED_VISIT, -share, Some(s.order), Some(g));
            if let Some(tx) = self.trace.as_mut() {
                let _ = writeln!(
                    tx,
                    "{} visit_failed {} {} {} {}",
                    num(self.now),
                    Self::gig_id(g),
                    data.requests[s.order].id,
                    s.leg,
                    REASON_NAME[reason as usize]
                );
            }
            self.emit(
                Ev::VisitFailed {
                    order: s.order,
                    leg: s.leg,
                    reason,
                },
                true,
            );
            let add = if leg + 1 < n_pick {
                let nx = &self.gigs[g].stops[self.gigs[g].pickups[leg + 1]];
                self.st
                    .road(l.p, self.orders[nx.order].as_ref().unwrap().legs[nx.leg].p)
            } else {
                0.0
            };
            return self.push(
                self.now + add,
                Q::Pickup {
                    gig: g,
                    driver: d,
                    leg: leg + 1,
                },
            );
        }
        if let Some(tx) = self.trace.as_mut() {
            let _ = writeln!(
                tx,
                "{} picked_up {} {} {}",
                num(self.now),
                Self::gig_id(g),
                data.requests[s.order].id,
                s.leg
            );
        }
        let mut drive = self.st.road(l.p, l.d)
            + if s.with_plates { 30.0 } else { 0.0 }
            + if s.with_charging { 40.0 } else { 0.0 };
        if self.needs_charge(l) && !s.with_charging {
            drive += 90.0;
            self.ledger(L_FINE, -10000.0, Some(s.order), Some(g));
        }
        for f in &data.forecasts {
            if (f.places.contains(&l.p) || f.places.contains(&l.d)) && t >= f.from && t < f.to {
                drive = jround(drive * 1.3);
            }
        }
        self.push(
            t + drive,
            Q::Deliver {
                gig: g,
                driver: d,
                leg,
            },
        );
    }
    fn deliver(&mut self, g: usize, d: usize, leg: usize) {
        crate::prof!(18);
        if self.gigs[g].driver != d {
            return;
        }
        let n_pick = self.gigs[g].pickups.len();
        let s = self.gigs[g].stops[self.gigs[g].pickups[leg]].clone();
        let legs = self.orders[s.order].as_ref().unwrap().legs.clone();
        let l = &legs[s.leg];
        let data = self.data;
        let tr = data.requests[s.order]
            .truth
            .as_ref()
            .and_then(|t| t.get(s.leg))
            .and_then(|t| t.as_ref());
        let mut t = self.now;
        if !l.d_priv {
            let real = tr.and_then(|t| t.delivery_hours).or(l.d_hours);
            if !is_open(&real, t) {
                if is_open(&l.d_hours, t) {
                    let w = next_open(&real, t);
                    if w - t <= 120.0 {
                        self.ledger(
                            L_WAITING,
                            -jround((1500.0 * (w - t)) / 60.0),
                            Some(s.order),
                            Some(g),
                        );
                        t = w;
                    } else {
                        t = next_open(&real, t);
                    }
                } else {
                    t = next_open(&real, t);
                }
            }
        }
        self.orders[s.order].as_mut().unwrap().delivered_at[s.leg] = Some(t);
        self.drivers[d].loc = l.d;
        if let Some(tx) = self.trace.as_mut() {
            let _ = writeln!(
                tx,
                "{} delivered {} {} {}",
                num(self.now),
                Self::gig_id(g),
                data.requests[s.order].id,
                s.leg
            );
        }
        self.emit(
            Ev::Delivered {
                order: s.order,
                leg: s.leg,
                at: self.now,
            },
            true,
        );
        let all = self.orders[s.order]
            .as_ref()
            .unwrap()
            .delivered_at
            .iter()
            .all(|x| x.is_some());
        if all {
            self.complete(s.order);
        } else {
            let o = self.orders[s.order].as_ref().unwrap();
            let lp = self.last_pickup(o, o.delivered_at.iter().position(|x| x.is_none()).unwrap());
            self.orders[s.order].as_mut().unwrap().last_pickup_at = lp;
        }
        let add = if leg + 1 < n_pick {
            let nx = &self.gigs[g].stops[self.gigs[g].pickups[leg + 1]];
            self.st
                .road(l.d, self.orders[nx.order].as_ref().unwrap().legs[nx.leg].p)
        } else {
            0.0
        };
        self.push(
            t + add,
            Q::Pickup {
                gig: g,
                driver: d,
                leg: leg + 1,
            },
        );
    }
    fn finish(&mut self, g: usize) {
        self.gigs[g].status = GigStatus::Done;
        // the fee covers the cars delivered; a failed car was already paid as a failed visit
        let n_pick = self.gigs[g].pickups.len() as f64;
        let fee = self.gigs[g].fee;
        let done: Vec<usize> = self.gigs[g]
            .pickups
            .iter()
            .map(|&i| &self.gigs[g].stops[i])
            .filter(|s| self.orders[s.order].as_ref().unwrap().delivered_at[s.leg].is_some())
            .map(|s| self.orders[s.order].as_ref().unwrap().option)
            .collect();
        if !done.is_empty() {
            let o0 = self.gigs[g].orders[0];
            self.ledger(
                L_DRIVER_FEE,
                -jround((fee * done.len() as f64) / n_pick),
                Some(o0),
                Some(g),
            );
        }
        for opt in done {
            self.count(ST_FEE + opt, fee / n_pick / 100.0);
        }
        let done_orders: Vec<usize> = self.gigs[g].pickups.iter().map(|&i| &self.gigs[g].stops[i]).filter(|s| self.orders[s.order].as_ref().unwrap().delivered_at[s.leg].is_some()).map(|s| s.order).collect();
        for o in done_orders { self.o_fee[o] += fee / n_pick; }
        let d = self.gigs[g].driver;
        let busy = self.now + self.st.road(self.drivers[d].loc, self.drivers[d].home);
        self.drivers[d].busy_until = busy;
        self.push(busy, Q::Free(d));
    }
    fn complete(&mut self, id: usize) {
        let st = self.st;
        let rq = &self.data.requests[id];
        let (fin, deadline, price, option, dealer, dh) = {
            let o = self.orders[id].as_mut().unwrap();
            o.delivered = true;
            let fin = o
                .delivered_at
                .iter()
                .fold(f64::NEG_INFINITY, |m, t| m.max(t.unwrap()));
            (
                fin,
                o.deadline,
                o.price,
                o.option,
                o.dealer,
                o.legs.iter().fold(0.0, |s, l| s + st.road(l.p, l.d)) / HOUR,
            )
        };
        let bk = if dh < 2.0 {
            0
        } else if dh < 5.0 {
            1
        } else {
            2
        };
        let late = fin > deadline;
        self.count(ST_NB + bk, 1.0);
        self.count(ST_N + option, 1.0);
        self.count(ST_REV + option, price / 100.0);
        self.count(
            ST_TYP + option,
            self.typ_raw[id].unwrap_or(self.ref_fee[id]) / 100.0,
        );
        if late {
            self.count(ST_LATE_B + bk, 1.0);
            self.count(ST_LATE + option, 1.0);
        }
        self.count(
            if rq.has_note { ST_N_NOTE } else { ST_N_PLAIN } + option,
            1.0,
        );
        if late {
            self.count(
                if rq.has_note {
                    ST_LATE_NOTE
                } else {
                    ST_LATE_PLAIN
                } + option,
                1.0,
            );
        }
        self.ledger(L_REVENUE, price, Some(id), None);
        self.o_late[id] = late;
        let t = self.trust[dealer];
        if late {
            let late_min = fin - deadline;
            let mut bdays = 0;
            let mut d = (deadline / DAY).floor() + 1.0;
            while d <= (fin / DAY).floor() {
                if d % 7.0 < 5.0 {
                    bdays += 1;
                }
                d += 1.0;
            }
            let share = if late_min <= 120.0 {
                0.1
            } else if late_min <= 24.0 * 60.0 {
                0.25
            } else if bdays <= 2 {
                0.5
            } else {
                1.0
            };
            self.ledger(L_LATE_REFUND, -jround(price * share), Some(id), None);
            self.trust[dealer] = ((t.0 / 2.0).floor(), t.1 + 1.0);
        } else {
            self.trust[dealer] = ((t.0 + 1.0).min(25.0), t.1);
        }
    }
}

#[inline]
pub fn fee_at(schedule: &Schedule, t: f64) -> f64 {
    let mut fee = schedule[0].1;
    for s in schedule {
        if s.0 <= t {
            fee = s.1;
        }
    }
    fee
}
fn move_days(deadline: f64, mut days: f64) -> f64 {
    let mut day = (deadline / DAY).floor();
    while days > 0.0 {
        day += 1.0;
        if day % 7.0 < 5.0 {
            days -= 1.0;
        }
    }
    (day * DAY + (deadline % DAY)).min(7.0 * DAY + 20.0 * HOUR)
}

// ── the win model (model.ts) ──
pub struct ReqX {
    pub pickup: usize,
    pub delivery: usize,
    pub drive_h: f64,
    pub trade_in: f64,
    pub priv_d: f64,
    pub same_day: f64,
    pub n_opt: f64,
    pub trust: f64,
    pub lates: f64,
}
#[inline]
pub fn win_base(w: &Win, x: &ReqX) -> f64 {
    w.intercept
        + w.pickup[x.pickup]
        + w.delivery[x.delivery]
        + w.driveH * x.drive_h
        + w.tradeIn * x.trade_in
        + w.privD * x.priv_d
        + w.sameDay * x.same_day
        + w.nOpt * x.n_opt
        + w.trust * x.trust
        + w.lates * x.lates
}
#[inline]
pub fn win_chance(w: &Win, base: f64, markup: f64, world: f64) -> f64 {
    1.0 / (1.0 + (-(base + w.ln_m * markup.ln() + world)).exp())
}

/// What is the same for every play of a week on one set of world parameters: who works which day (a fixed draw per
/// driver and day), who lives within 30 km of each place, who may take which audience. Built once per seed.
pub struct SeedPre {
    pub words: usize,
    /// works[day]: bit d = driver d works that day (days 0..PRE_DAYS)
    pub works: Vec<Vec<u64>>,
    pub near30: Vec<Vec<u64>>,
    pub experienced: Vec<u64>,
    pub manual: Vec<u64>,
    /// draws[d * PRE_DAYS + day] = [other options, longest gig, home time]
    pub draws: Vec<[f64; 3]>,
}
pub const PRE_DAYS: usize = 16;
fn normal(data: &Seed, prefix: u32, d: usize, day: f64) -> f64 {
    let h = fnv_int(day as u64, fnv("|", fnv(&data.roster[d].id, prefix)));
    (-2.0 * (fin(fnv("a", h)) + 1e-12).ln()).sqrt() * (2.0 * std::f64::consts::PI * fin(fnv("b", h))).cos()
}
pub fn draws(data: &Seed, p: &SimP, h_out: u32, h_md: u32, h_home: u32, d: usize, day: f64) -> [f64; 3] {
    [
        p.outMu * (p.outSd * normal(data, h_out, d, day)).exp(),
        p.maxDriveMu * HOUR * (p.maxDriveSd * normal(data, h_md, d, day)).exp(),
        (p.homeMu + p.homeSd * normal(data, h_home, d, day)) * HOUR,
    ]
}
pub fn works_draw(data: &Seed, p: &SimP, h_work: u32, d: usize, day: f64) -> bool {
    let wd = day % 7.0;
    if wd == 6.0 {
        return false;
    }
    let dr = &data.roster[d];
    let l = dr.completed.ln_1p();
    let mut pr = (p.workBase + p.workGig * l * if p.workPow == 1.0 { 1.0 } else { (l / 4.0).powf(p.workPow - 1.0) }).min(0.85);
    if wd == 5.0 {
        pr *= p.workSat;
    }
    let noon = day * DAY + 12.0 * HOUR;
    for f in &data.forecasts {
        if f.places.contains(&dr.home) && f.from <= noon && f.to > noon {
            pr *= 0.6;
        }
    }
    fin(fnv_int(day as u64, fnv("|", fnv(&dr.id, h_work)))) < pr
}
impl SeedPre {
    pub fn new(st: &Static, data: &Seed, p: &SimP) -> SeedPre {
        let nd = data.roster.len();
        let words = (nd + 63) / 64;
        let h_work = fnv(&format!("{}|work|", data.seed), FNV0);
        let bits = |f: &dyn Fn(usize) -> bool| -> Vec<u64> {
            let mut v = vec![0u64; words];
            for d in 0..nd {
                if f(d) {
                    v[d / 64] |= 1 << (d % 64);
                }
            }
            v
        };
        let np = st.np();
        SeedPre {
            words,
            works: (0..PRE_DAYS).map(|day| bits(&|d| works_draw(data, p, h_work, d, day as f64))).collect(),
            near30: (0..np).map(|i| bits(&|d| !(st.km[data.roster[d].home * np + i] > 30.0))).collect(),
            experienced: bits(&|d| data.roster[d].rating >= 4.8 && data.roster[d].completed >= 50.0),
            manual: bits(&|d| data.roster[d].manual),
            draws: {
                let h = |tag: &str| fnv(&format!("{}|{}|", data.seed, tag), FNV0);
                let (ho, hm, hh) = (h("out"), h("md"), h("home"));
                (0..nd * PRE_DAYS).map(|i| draws(data, p, ho, hm, hh, i / PRE_DAYS, (i % PRE_DAYS) as f64)).collect()
            },
        }
    }
}
