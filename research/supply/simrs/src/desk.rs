//! Our side: a port of kit-best/core/engine.ts (the desk's mechanics), algo.ts (prices, fees, pairs, learning),
//! model.ts (booking model, fee planner), cost.ts (realized-cost trees) and the slot functions of notes.ts.
//! The note readers themselves (regular expressions) run in prep.ts; their results arrive with the data.
use crate::data::*;
use crate::world::*;
use std::fmt::Write;
use std::rc::Rc;

params!(P {
    minBookChance: 0.95,
    hardChance: 0.85,
    hardPrice: 0.2,
    costW: 1,
    costUp: 0,
    minProfit: 0.1,
    minSlackH: 3,
    capPerDriver: 3,
    dueCapPer: 0.1,
    fullPrice: 0.25,
    markupMin: 1.28,
    markupMax: 2,
    capLam: 4,
    capConst: 1,
    pairBack: 0.05,
    outage: 0.3,
    outageN: 6,
    outageGap: 0.3,
    worldN: 300,
    lateCost: 4,
    openMin: 0.706,
    openMax: 1.6,
    raiseMax: 0.2,
    steps: 5,
    rampTop: 1.6,
    rampWindowH: 10,
    steepOpen: 1.3,
    steepStep: 0.15,
    lateFee: 0.832,
    pairKm: 30,
    pairSlackH: 6,
    pairCap: 0.9,
    pairTop: 1.3,
    pairHoldH: 4,
    noteHours: 1,
    hoursMinLeftH: 1.5,
    pairFlags: 1,
    priceLearn: 1,
    pS: 0.1,
    pWeek: 0.05,
    pDay: 0.14,
    pDealer: 0,
    pTown: 0,
    dueMon: -0.03,
    dueFri: 0.08,
    typMinN: 5,
    floorLvl: 1,
    // ── research/supply: driver-supply models, all off by default (off = BEST10 to the cent) ──
    ballKm: 0,      // B: outer radius (km, straight line) of the supply and load ball around the pickup; 0 = off (30 km circle, exact place)
    ballIn: 30,     //    full weight inside this radius (the notification radius)
    ballGauss: 0,   //    1 = Gaussian fall-off beyond ballIn (sd = (ballKm - ballIn) / 2), 0 = linear to zero at ballKm
    smoothS: 0,     // S: 0 = the full-town and full-day steps; over 0 = a logistic of that width in utilisation instead
    smoothAt: 1,    //    ... centred at this utilisation (1 = where the old step sits)
    capU: 0,        // Q: capacity cost / (1 - min(0.75, capU x town utilisation)); 0 = constant capacity cost
    wkMon: 0,       // W: price shift (x list) for requests that arrive on Monday (negative = greedier)
    wkTue: 0,       //    ... on Tuesday
    wkLate: 0,      //    ... on Thursday and Friday (positive = pickier)
    backK: 0,       // L: live backlog: price shift = backK x (our orders without a booked driver / roster - backAt)
    backAt: 0.03,   //    the backlog share of the roster that is neutral
    backDown: 0,    //    the most the backlog rule may cut the price (x list); rises are capped at 0.3
    backDueH: 0,
    curve: 0,       // C: 1 = free backlog curve (replaces backK / backPow; uses backDueH): cut below cLo, nothing up to cLo + cDead, then a rise
    cDown: 0.08,    //    the cut at an empty board (x list)
    cLo: 0.04,      //    backlog (orders without a driver / roster) where the cut ends
    cSteep: 1,      //    1 = the cut fades in a straight line from 0 to cLo; more = the full cut holds longer
    cDead: 0,       //    width of the flat stretch after cLo
    cSpan: 0.05,    //    backlog over which the rise goes from 0 to cCap
    cPow: 1,        //    shape of the rise: 1 straight, over 1 late and steep, under 1 early
    cCap: 0.3,      //    the highest rise (x list)
    backPow: 0,     //    over 0 = convex rise above neutral: backUp x ((backlog / backAt)^backPow - 1); the cut below neutral stays linear
    backUp: 0.08,   //    ... its scale (x list)
    resK: 0,        // R: live correction of the cost trees: + resK x mean(realized - predicted cost) of this week's delivered orders
    resN: 30,       //    ... shrunk toward zero as n / (n + resN)
    shortShift: 0,  // M: price shift (x list) for a request whose drive is under shortH hours (negative = win more short cars)
    shortH: 1,
    longShift: 0,   //    ... for a drive over longH hours (positive = win fewer long cars)
    longH: 3,
    floorTyp: 0,    //    lower price for cars cheap to move: shift -floorTyp x (floorTypRef - typical fee / list price) when positive (kit-out's knob)
    floorTypRef: 0.8,
    sdShift: 0,     //    same-day options: price + this x list (positive = dearer same-day)
    sdMinH: 0,      //    same-day options with under this many hours to the last pickup are not sold
    lateW: 0,       // lateness charge: + lateW x P(order ends late) x typical fee; P = logistic of the SECOND head of the cost file (--cost; sim copy only)
    pMean: 0,       // P: where the week's price level starts (log price; 0 = an average week)
    oraWeek: 0,     //    oracle (sim only): 1 = start at this week's true level, as if Monday's learning were instant
    oraDay: 0,      //    oracle (sim only): 1 = start every weekday at its true level too
    dumpRows: 0,    // 1 = keep the cost-tree inputs of every quoted option (for refits)    //    over 0 = count only orders whose last pickup time is within this many hours
});

const LEVEL: u32 = 8;

struct DOrder {
    legs: Rc<Vec<Leg>>,
    dealer: usize,
    option: usize,
    deadline: f64,
    last_pickup_at: f64,
    delivered_at: Vec<Option<f64>>,
}
struct PostRec {
    post: Post,
    orders: Vec<usize>,
}
#[derive(Clone, Copy)]
struct Retry {
    pickup_from: f64,
    manual: bool,
    plates: bool,
}
const FIRST_TRY: Retry = Retry {
    pickup_from: 0.0,
    manual: false,
    plates: false,
};
struct Sites {
    pickup: Option<Hours>,
    delivery: Option<Hours>,
    now: f64,
    min_left: f64,
    drive: f64,
}
struct Quoted {
    g: f64,
    h: [usize; 5],
    lm: f64,
}
struct Answer {
    at: f64,
    place: usize,
    won: f64,
    chance: f64,
}
struct GigX {
    near_p: f64,
    near_d: f64,
    near_p80: f64,
    near_d80: f64,
    drive_h: f64,
    cars: f64,
    priv_p: f64,
    priv_d: f64,
    premium: f64,
    load: f64,
    typ: f64,
}
struct Plan {
    schedule: Schedule,
    fee: f64,
    chance: f64,
    open: f64,
    raise: f64,
}
struct PlanP {
    late_cost: f64,
    open_min: f64,
    open_max: f64,
    steps: f64,
    raise_max: f64,
}

pub struct Desk<'a> {
    st: &'a Static,
    data: &'a Seed,
    pub p: P,
    pub now: f64,
    outbox: Vec<Action>,
    seen: Vec<bool>,
    orders: Vec<Option<DOrder>>,
    order_list: Vec<usize>,
    leg_gigs: Vec<Option<Vec<(usize, usize)>>>,
    booked: Vec<bool>,
    posts: Vec<PostRec>,
    urgent: Vec<bool>,
    solo: Vec<bool>,
    dealers: Vec<(f64, f64)>,
    timers: Vec<(f64, usize)>,
    pair_timers: Vec<(f64, usize)>,
    note_timers: Vec<(f64, usize)>,
    near30: Vec<f64>,
    near80: Vec<f64>,
    sup_ball: Vec<f64>,
    ball_w: Vec<f64>,
    // counters kept in step with `orders` (exact: integer counts of what the TypeScript recounts each time)
    open_from: Vec<f64>,
    open_all: f64,
    open1_p: Vec<f64>,
    open1_d: Vec<f64>,
    due_on: [f64; 64],
    // the algorithm's memory
    quoted: Vec<Option<f64>>,
    pq: Vec<Option<Quoted>>,
    answers_at: Vec<Answer>,
    ans_z: Vec<f64>,
    ans_won: Vec<f64>,
    ans_from: usize,
    ans_chance: Vec<f64>,
    world_level: f64,
    pf_x: Vec<f64>,
    pf_p: Vec<f64>,
    n_dealer: usize,
    n_state: usize,
    pub n_quoted: u32,
    pub n_declined: u32,
    pub journal: Option<String>,
    tabs: PlanTabs,
    singles: Vec<usize>,
    pf_act: Vec<usize>,
    ln_m: std::cell::RefCell<Vec<(u64, u64, Vec<(f64, f64)>)>>,
    pub dump_x: std::cell::RefCell<Vec<(usize, usize, [f64; 38])>>,
    pred: std::cell::RefCell<Vec<[f64; 3]>>,
}

fn sched_str(s: &Schedule) -> String {
    s.iter()
        .map(|x| format!("{}:{}", num(x.0), num(x.1)))
        .collect::<Vec<_>>()
        .join(",")
}

impl<'a> Desk<'a> {
    pub fn new(st: &'a Static, data: &'a Seed, p: P, journal: bool) -> Self {
        let n = data.requests.len();
        let np = st.np();
        let near = |radius: f64| -> Vec<f64> {
            (0..np)
                .map(|pl| {
                    data.roster
                        .iter()
                        .filter(|d| st.km(pl, d.home) <= radius)
                        .count() as f64
                })
                .collect()
        };
        // research/supply: the ball's weight by distance, and the weighted drivers around each place
        let kern = |d: f64| -> f64 {
            if d <= p.ballIn { 1.0 } else if p.ballKm <= p.ballIn { 0.0 }
            else if p.ballGauss > 0.0 { let sd = (p.ballKm - p.ballIn) / 2.0; (-0.5 * ((d - p.ballIn) / sd).powi(2)).exp() }
            else { (1.0 - (d - p.ballIn) / (p.ballKm - p.ballIn)).max(0.0) }
        };
        let ball_w: Vec<f64> = if p.ballKm > 0.0 { (0..np * np).map(|k| kern(st.km(k / np, k % np))).collect() } else { Vec::new() };
        let sup_ball: Vec<f64> = if p.ballKm > 0.0 { (0..np).map(|pl| data.roster.iter().fold(0.0, |s, d| s + ball_w[pl * np + d.home])).collect() } else { Vec::new() };
        let n_dealer = st.price.dealer.len();
        let n_state = 66 + n_dealer;
        let n_dealers = data
            .requests
            .iter()
            .map(|r| r.dealer + 1)
            .max()
            .unwrap_or(0);
        let mut pf_p = vec![0.0; n_state * n_state];
        for i in 0..n_state {
            let sd = if i == 0 {
                p.pWeek
            } else if i < 6 {
                p.pDay
            } else if i < 6 + n_dealer {
                p.pDealer
            } else {
                p.pTown
            };
            pf_p[i * n_state + i] = sd * sd;
        }
        let mut pf_x0 = vec![0.0; n_state.max(256)];
        pf_x0[0] = p.pMean + p.oraWeek * (data.off_level.clamp(-3.0, 3.0) + 0.287) / st.win.ln_m.abs();
        for &(day, off) in &data.off_day { let d = day as usize; if d < 5 { pf_x0[1 + d] = p.oraDay * off.clamp(-3.0, 3.0) / st.win.ln_m.abs(); } }
        let pf_act: Vec<usize> = (0..n_state).filter(|&i| pf_p[i * n_state + i] != 0.0).collect();
        assert!(n_state <= 256);
        Desk {
            st,
            data,
            now: 0.0,
            outbox: Vec::new(),
            seen: vec![false; n],
            orders: (0..n).map(|_| None).collect(),
            order_list: Vec::new(),
            leg_gigs: (0..n).map(|_| None).collect(),
            booked: Vec::new(),
            posts: Vec::new(),
            urgent: vec![false; n],
            solo: vec![false; n],
            dealers: vec![(0.0, 0.0); n_dealers],
            timers: Vec::new(),
            pair_timers: Vec::new(),
            note_timers: Vec::new(),
            near30: near(30.0),
            near80: near(80.0),
            sup_ball,
            ball_w,
            open_from: vec![0.0; np],
            open_all: 0.0,
            open1_p: vec![0.0; np],
            open1_d: vec![0.0; np],
            due_on: [0.0; 64],
            quoted: vec![None; n],
            pq: (0..n).map(|_| None).collect(),
            answers_at: Vec::new(),
            ans_z: Vec::new(),
            ans_won: Vec::new(),
            ans_from: 0,
            ans_chance: Vec::new(),
            world_level: 0.0,
            pf_x: pf_x0,
            pf_p,
            n_dealer,
            n_state,
            n_quoted: 0,
            n_declined: 0,
            journal: if journal { Some(String::new()) } else { None },
            tabs: PlanTabs::new(PlanTabsData { tabs: Vec::new(), pre: PlanPre { z0: 0, now: u64::MAX, n: 0, z: [0.0; 72] } }),
            singles: Vec::new(),
            pf_act,
            ln_m: std::cell::RefCell::new(Vec::new()),
            dump_x: std::cell::RefCell::new(Vec::new()),
            pred: std::cell::RefCell::new(vec![[f64::NAN; 3]; n]),
            p,
        }
    }

    // ── playing a week (playPractice) ──
    pub fn play(&mut self, w: &mut World) {
        while self.now < END {
            let day = (self.now / DAY).floor();
            let actions = std::mem::take(&mut self.outbox);
            let max = END
                .min((day + 1.0) * DAY)
                .min((self.now + 1.0).max(self.next_timer()));
            let (results, events) = w.advance(&actions, max);
            self.read_results(w, actions, &results);
            self.now = w.now;
            for e in events {
                self.handle(w, e);
            }
            self.fire_timers(w);
        }
    }

    // ── events ──
    fn handle(&mut self, w: &mut World, e: Ev) {
        crate::prof!(20);
        match e {
            Ev::Request(i) => {
                self.denoise(w, i);
                self.quote(w, i);
            }
            Ev::Won {
                order,
                last_pickup_at,
            } => {
                self.learn(order, true);
                self.win(w, order, last_pickup_at);
            }
            Ev::Lost(i) => self.learn(i, false),
            Ev::VisitFailed { order, leg, reason } => self.retry(w, order, leg, reason),
            Ev::Expired(g) => self.repost(w, g),
            Ev::DeadlineClose {
                order,
                last_pickup_at,
            } => {
                if self.p.lateFee > 0.0 {
                    self.timers.push((last_pickup_at + 1.0, order));
                }
                self.raise(w, order);
            }
            Ev::Booked(g) => self.booked[g] = true,
            Ev::Dropped(g) => {
                self.booked[g] = false;
                if self.is_pair(g) && self.is_live(g) {
                    self.split(w, g, true);
                }
            }
            Ev::Delivered { order, leg, at } => self.delivered(order, leg, at),
        }
    }
    fn denoise(&mut self, w: &mut World, i: usize) {
        if w.typ_raw[i].is_some() {
            return;
        }
        let r = &self.data.requests[i];
        if r.typ_min_n.unwrap_or(f64::INFINITY) < self.p.typMinN {
            return;
        }
        let Some(pred) = r.typ_pred else { return };
        w.typ_raw[i] = Some(w.ref_fee[i]);
        w.ref_fee[i] = pred;
    }
    fn quote(&mut self, w: &mut World, i: usize) {
        self.seen[i] = true;
        let r = &self.data.requests[i];
        if let Some(prices) = self.algo_quote(w, i) {
            if let Some(j) = self.journal.as_mut() {
                let q = r.options.iter().find(|o| prices[o.kind].is_some()).unwrap();
                let _ = writeln!(
                    j,
                    "quote {} {} {}",
                    r.id,
                    num(self.now),
                    num(prices[q.kind].unwrap() / q.list)
                );
            }
            self.n_quoted += 1;
            self.outbox.push(Action::Quote { req: i, prices });
            return;
        }
        self.n_declined += 1;
        let first = &r.options[0];
        if LEVEL >= 4 {
            let mut prices = [None; 3];
            prices[first.kind] = Some(first.list * 10.0);
            self.outbox.push(Action::Quote { req: i, prices });
        }
    }
    fn fees_for(&self, w: &World, o: usize, legs: &[usize]) -> Schedule {
        let order = self.orders[o].as_ref().unwrap();
        let fee = (w.ref_fee[o] * legs.len() as f64) / order.legs.len() as f64;
        self.algo_fees(o, fee, legs, self.urgent[o])
    }
    fn next_timer(&self) -> f64 {
        let m = |t: &Vec<(f64, usize)>| t.iter().fold(f64::INFINITY, |m, x| m.min(x.0));
        m(&self.timers)
            .min(m(&self.pair_timers))
            .min(m(&self.note_timers))
    }
    fn fire_timers(&mut self, w: &mut World) {
        crate::prof!(10);
        let mut i = self.note_timers.len();
        while i > 0 {
            i -= 1;
            let (at, o) = self.note_timers[i];
            if at > self.now {
                continue;
            }
            self.note_timers.remove(i);
            if self.orders[o].is_some()
                && !self.urgent[o]
                && self.gigs_of(o).iter().any(|&g| !self.booked[g])
            {
                if let Some(j) = self.journal.as_mut() {
                    let _ = writeln!(
                        j,
                        "note_warn {} {}",
                        self.data.requests[o].id,
                        num(self.now)
                    );
                }
                self.raise(w, o);
            }
        }
        let mut i = self.pair_timers.len();
        while i > 0 {
            i -= 1;
            let (at, g) = self.pair_timers[i];
            if at > self.now {
                continue;
            }
            self.pair_timers.remove(i);
            if self.is_pair(g) && self.is_live(g) && !self.booked[g] {
                if let Some(j) = self.journal.as_mut() {
                    let _ = writeln!(j, "pair_timeout {} {}", World::gig_id(g), num(self.now));
                }
                self.split(w, g, true);
            }
        }
        let mut i = self.timers.len();
        while i > 0 {
            i -= 1;
            let (at, o) = self.timers[i];
            if at > self.now {
                continue;
            }
            self.timers.remove(i);
            let Some(order) = self.orders[o].as_ref() else {
                continue;
            };
            if order.last_pickup_at > self.now {
                continue;
            }
            for g in self.gigs_of(o) {
                if !self.booked[g] && !self.is_pair(g) {
                    let schedule = self.fees_for(w, o, &legs_of(&self.posts[g].post));
                    self.outbox.push(Action::Reprice { gig: g, schedule });
                }
            }
        }
    }
    fn delivered(&mut self, o: usize, leg: usize, at: f64) {
        if let Some(m) = self.leg_gigs[o].as_mut() {
            m.retain(|x| x.0 != leg);
        }
        let Some(order) = self.orders[o].as_mut() else {
            return;
        };
        let was_open = order.delivered_at.iter().any(|t| t.is_none());
        order.delivered_at[leg] = Some(at);
        if order.delivered_at.iter().all(|t| t.is_some()) {
            if was_open {
                let l0 = &order.legs[0];
                self.open_from[l0.p] -= 1.0;
                self.open_all -= 1.0;
                if order.legs.len() == 1 {
                    self.open1_p[l0.p] -= 1.0;
                    self.open1_d[l0.d] -= 1.0;
                }
            }
            // on time builds trust, late halves it
            let d = self.dealers[order.dealer];
            let late = order
                .delivered_at
                .iter()
                .fold(f64::NEG_INFINITY, |m, t| m.max(t.unwrap()))
                > order.deadline;
            self.dealers[order.dealer] = if late {
                ((d.0 / 2.0).floor(), d.1 + 1.0)
            } else {
                ((d.0 + 1.0).min(25.0), d.1)
            };
        }
    }
    fn win(&mut self, w: &mut World, o: usize, last_pickup_at: f64) {
        crate::prof!(3);
        if !self.seen[o] || self.orders[o].is_some() {
            return;
        }
        let st = self.st;
        let wo = w.orders[o].as_ref().unwrap();
        let order = DOrder {
            legs: wo.legs.clone(),
            dealer: wo.dealer,
            option: wo.option,
            deadline: wo.deadline,
            last_pickup_at,
            delivered_at: vec![None; wo.legs.len()],
        };
        let l0 = &order.legs[0];
        self.open_from[l0.p] += 1.0;
        self.open_all += 1.0;
        if order.legs.len() == 1 {
            self.open1_p[l0.p] += 1.0;
            self.open1_d[l0.d] += 1.0;
        }
        self.due_on[(order.deadline / DAY).floor() as usize] += 1.0;
        let r = &self.data.requests[o];
        if r.ready_from.is_some() || r.deliver_by.is_some() {
            self.solo[o] = true;
        }
        if let Some(by) = r.deliver_by {
            let drive = order.legs.iter().fold(0.0, |s, l| s + st.road(l.p, l.d));
            if by - drive < order.last_pickup_at {
                self.note_timers
                    .push(((self.now + 1.0).max(by - drive - 3.0 * HOUR), o));
            }
        }
        let (deadline, lp, drive0) = (order.deadline, order.last_pickup_at, st.road(l0.p, l0.d));
        let n_legs = order.legs.len();
        self.orders[o] = Some(order);
        self.order_list.push(o);
        if let Some(sites) = self.sites_of(o) {
            self.solo[o] = true;
            if let Some(real) =
                last_slot(&sites.pickup, &sites.delivery, drive0, self.now, deadline)
            {
                if real < lp {
                    self.note_timers
                        .push(((self.now + 1.0).max(real - 3.0 * HOUR), o));
                }
            }
        }
        if self.try_pair(w, o) {
            return;
        }
        let legs: Vec<usize> = (0..n_legs).collect();
        self.post(w, o, &legs, FIRST_TRY);
    }
    fn sites_of(&self, o: usize) -> Option<Sites> {
        if !(self.p.noteHours > 0.0) {
            return None;
        }
        let noted = self.data.requests[o].noted.as_ref()?;
        let l = &self.orders[o].as_ref().unwrap().legs[0];
        Some(Sites {
            pickup: noted.pickup,
            delivery: noted.delivery,
            now: self.now,
            min_left: self.p.hoursMinLeftH * HOUR,
            drive: self.st.road(l.p, l.d),
        })
    }
    fn undelivered(&self, o: usize) -> Vec<usize> {
        let d = &self.orders[o].as_ref().unwrap().delivered_at;
        (0..d.len()).filter(|&i| d[i].is_none()).collect()
    }

    /// The open one-car gigs of other orders, and whether `order` can ride with one of them.
    fn try_pair(&mut self, w: &mut World, o: usize) -> bool {
        crate::prof!(9);
        let st = self.st;
        let n_legs = self.orders[o].as_ref().unwrap().legs.len();
        if LEVEL < 3 || n_legs != 1 {
            return false;
        }
        let r = &self.data.requests[o];
        if self.p.pairFlags > 0.0 && (r.plates || r.manual) {
            return false;
        }
        if self.sites_of(o).is_some() {
            return false;
        }
        self.send(w);
        let mut best: Option<(usize, [usize; 2], Schedule, f64)> = None;
        self.prune_singles();
        for si in 0..self.singles.len() {
            let g = self.singles[si];
            let rec = &self.posts[g];
            if self.booked[g]
                || !self.is_live(g)
                || rec.post.stops.iter().any(|s| s.with_plates)
                || rec.post.manual
            {
                continue;
            }
            if rec.orders.len() != 1 {
                continue;
            }
            let other = rec.orders[0];
            let Some(oo) = self.orders[other].as_ref() else {
                continue;
            };
            if other == o || oo.legs.len() != 1 || self.urgent[other] || self.solo[other] {
                continue;
            }
            for chain in [[o, other], [other, o]] {
                let (mut drive, mut slack, mut typical) = (0.0, f64::INFINITY, 0.0);
                let mut t = self.now;
                for k in 0..2 {
                    let ord = self.orders[chain[k]].as_ref().unwrap();
                    let leg = &ord.legs[0];
                    if k > 0 {
                        let between =
                            st.road(self.orders[chain[k - 1]].as_ref().unwrap().legs[0].d, leg.p);
                        drive += between;
                        t += between;
                    }
                    t = t.max(leg.p_from);
                    slack = slack.min(ord.last_pickup_at - t);
                    let d = st.road(leg.p, leg.d);
                    drive += d;
                    t += d;
                    typical += w.ref_fee[chain[k]];
                }
                if drive > 12.0 * HOUR || slack < 0.0 {
                    continue;
                }
                let (a, b) = (
                    &self.orders[chain[0]].as_ref().unwrap().legs[0],
                    &self.orders[chain[1]].as_ref().unwrap().legs[0],
                );
                let join_km = st.km(a.d, b.p);
                let back_km = st.km(b.d, a.p);
                if let Some((schedule, score)) =
                    self.algo_pair(chain, typical, join_km, back_km, slack)
                {
                    if best.as_ref().map_or(true, |b| score > b.3) {
                        best = Some((g, chain, schedule, score));
                    }
                }
            }
        }
        let Some((gig, chain, schedule, _)) = best else {
            return false;
        };
        let mut stops = Vec::new();
        for &c in &chain {
            stops.extend(without_windows(
                self.stops_for(c, &[0], FIRST_TRY, None),
                self.now,
            ));
        }
        let experienced = chain
            .iter()
            .any(|&c| self.orders[c].as_ref().unwrap().legs[0].premium);
        if w.act(&[Action::Withdraw { gig }])[0].is_none() {
            return false;
        } // a driver booked it in the same minute
        if let Some(j) = self.journal.as_mut() {
            let _ = writeln!(j, "wd {} {}", World::gig_id(gig), num(self.now));
        }
        let others: Vec<usize> = chain.iter().copied().filter(|&c| c != o).collect();
        for &c in &others {
            self.leg_gigs[c] = None;
        }
        let post = Post {
            stops,
            experienced,
            manual: false,
            schedule,
        };
        let action = [Action::Post(post)];
        let posted = w.act(&action);
        if let Some(id) = posted[0] {
            self.read_results(w, action.into(), &posted);
            if self.p.pairHoldH > 0.0 {
                self.pair_timers.push((
                    (self.now + 30.0).max(self.now + self.p.pairHoldH * HOUR),
                    id,
                ));
            }
            if let Some(j) = self.journal.as_mut() {
                let _ = writeln!(
                    j,
                    "pair {} {} {} {}",
                    World::gig_id(id),
                    self.data.requests[chain[0]].id,
                    self.data.requests[chain[1]].id,
                    num(self.now)
                );
            }
            return true;
        }
        for &c in &others {
            let legs = self.undelivered(c);
            self.post(w, c, &legs, FIRST_TRY);
        }
        false
    }

    /// Takes a gig with cars of several orders apart: every order gets its own gig again.
    fn split(&mut self, w: &mut World, gig: usize, withdraw: bool) {
        if gig >= self.posts.len() {
            return;
        }
        if withdraw {
            self.send(w);
            if w.act(&[Action::Withdraw { gig }])[0].is_none() {
                return;
            }
        }
        let orders = self.posts[gig].orders.clone();
        for o in orders {
            if let Some(m) = self.leg_gigs[o].as_mut() {
                m.retain(|x| x.1 != gig);
            }
            self.solo[o] = true;
            if self.orders[o].is_some() {
                let und = self.undelivered(o);
                if !und.is_empty() && self.gigs_of(o).is_empty() {
                    self.post(w, o, &und, FIRST_TRY);
                }
            }
        }
    }
    #[inline]
    fn is_pair(&self, gig: usize) -> bool {
        gig < self.posts.len() && self.posts[gig].orders.len() > 1
    }
    fn is_live(&self, gig: usize) -> bool {
        gig < self.posts.len()
            && self.posts[gig].post.stops.iter().any(|s| {
                self.leg_gigs[s.order]
                    .as_ref()
                    .map_or(false, |m| m.iter().any(|x| x.0 == s.leg && x.1 == gig))
            })
    }

    /// Posts a gig again when one of its windows ended before a driver booked it.
    fn repost(&mut self, w: &mut World, gig: usize) {
        if gig >= self.posts.len() || !self.is_live(gig) {
            return;
        }
        if self.is_pair(gig) {
            self.split(w, gig, false);
            return;
        }
        let action = self.posts[gig].post.clone();
        for s in &action.stops {
            if let Some(m) = self.leg_gigs[s.order].as_mut() {
                m.retain(|x| x.0 != s.leg);
            }
        }
        let o = action.stops[0].order;
        if self.orders[o].is_none() {
            return;
        }
        let legs = legs_of(&action);
        let stops = match self.sites_of(o) {
            Some(sites) => self.stops_for(
                o,
                &legs,
                Retry {
                    pickup_from: 0.0,
                    manual: action.manual,
                    plates: action.stops.iter().any(|s| s.with_plates),
                },
                Some(&sites),
            ),
            None => without_windows(action.stops.clone(), f64::INFINITY),
        };
        let schedule = self.fees_for(w, o, &legs);
        self.outbox.push(Action::Post(Post {
            stops,
            experienced: action.experienced,
            manual: action.manual,
            schedule,
        }));
    }

    /// After a deadline warning, the order's unbooked gigs get the urgent fees (pairs are split first).
    fn raise(&mut self, w: &mut World, o: usize) {
        if self.orders[o].is_none() {
            return;
        }
        self.urgent[o] = true;
        self.send_post_of(w, o);
        for g in self.gigs_of(o) {
            if self.is_pair(g) && !self.booked[g] {
                self.split(w, g, true);
            }
        }
        for g in self.gigs_of(o) {
            if self.is_pair(g) {
                continue;
            }
            if !self.booked[g] {
                let schedule = self.fees_for(w, o, &legs_of(&self.posts[g].post));
                self.outbox.push(Action::Reprice { gig: g, schedule });
            }
        }
    }
    fn retry(&mut self, w: &mut World, o: usize, leg: usize, reason: u8) {
        let Some(order) = self.orders[o].as_ref() else {
            return;
        };
        let r = &self.data.requests[o];
        let pickup_from = if reason <= 1 {
            // when to try a car again after it was not ready or the site was closed
            let promised = r
                .options
                .iter()
                .find(|x| x.kind == order.option)
                .map_or(order.deadline, |x| x.deadline);
            let delay = (order.deadline - promised).max(0.0);
            (self.now + 2.0 * HOUR).max(order.legs[leg].p_from + delay)
        } else {
            0.0
        };
        if let Some(m) = self.leg_gigs[o].as_mut() {
            m.retain(|x| x.0 != leg);
        }
        self.post(
            w,
            o,
            &[leg],
            Retry {
                pickup_from,
                manual: reason == 2,
                plates: reason == 3,
            },
        );
    }
    fn post(&mut self, w: &mut World, o: usize, legs: &[usize], mut retry: Retry) {
        // the note often says what the first visit would otherwise find out the hard way
        let r = &self.data.requests[o];
        if r.plates || r.manual {
            retry.plates = retry.plates || r.plates;
            retry.manual = retry.manual || r.manual;
        }
        let experienced = self.orders[o]
            .as_ref()
            .unwrap()
            .legs
            .iter()
            .any(|l| l.premium);
        let sites = self.sites_of(o);
        let stops = without_windows(self.stops_for(o, legs, retry, sites.as_ref()), self.now);
        let schedule = self.fees_for(w, o, legs);
        self.outbox.push(Action::Post(Post {
            stops,
            experienced,
            manual: retry.manual,
            schedule,
        }));
        if legs.len() == 1 {
            return;
        }
        // a trade-in over the 12-hour limit goes as one gig per car
        self.send(w);
        if self.gigs_of(o).is_empty() {
            for &leg in legs {
                self.post(w, o, &[leg], retry);
            }
        }
    }
    fn gigs_of(&self, o: usize) -> Vec<usize> {
        let mut out: Vec<usize> = Vec::new();
        if let Some(m) = self.leg_gigs[o].as_ref() {
            for x in m {
                if !out.contains(&x.1) {
                    out.push(x.1);
                }
            }
        }
        out
    }
    fn carry(&mut self, w: &World, post: Post, gig: usize) {
        assert_eq!(
            gig,
            self.posts.len(),
            "gigs are carried in the order the world numbers them"
        );
        let mut orders: Vec<usize> = Vec::with_capacity(2);
        for s in &post.stops {
            if !orders.contains(&s.order) {
                orders.push(s.order);
            }
            let m = self.leg_gigs[s.order].get_or_insert_with(Vec::new);
            match m.iter_mut().find(|x| x.0 == s.leg) {
                Some(x) => x.1 = gig,
                None => m.push((s.leg, gig)),
            }
        }
        if self.journal.is_some() {
            let o = post.stops[0].order;
            if let Some(order) = self.orders[o].as_ref() {
                let legs = legs_of(&post);
                let typical = if orders.len() > 1 {
                    orders.iter().fold(0.0, |s, &i| s + w.ref_fee[i])
                } else {
                    (w.ref_fee[o] * legs.len() as f64) / order.legs.len() as f64
                };
                let ready = post.stops[0]
                    .window
                    .map_or(order.legs[legs[0]].p_from, |x| x.0);
                let stops: Vec<String> = post
                    .stops
                    .iter()
                    .map(|s| {
                        format!(
                            "{}{}{}{}{}",
                            self.data.requests[s.order].id,
                            s.leg,
                            if s.pickup { "p" } else { "d" },
                            s.window
                                .map_or("".into(), |x| format!("[{}-{}]", num(x.0), num(x.1))),
                            if s.with_plates { "P" } else { "" }
                        )
                    })
                    .collect();
                let line = format!(
                    "post {} {} {} {} {} {} {} {} {}\n",
                    World::gig_id(gig),
                    self.data.requests[o].id,
                    num(self.now),
                    num(typical),
                    num(order.last_pickup_at),
                    num(ready),
                    self.urgent[o] as u8,
                    sched_str(&post.schedule),
                    stops.join(";")
                );
                self.journal.as_mut().unwrap().push_str(&line);
            }
        }
        if orders.len() == 1 && self.orders[orders[0]].as_ref().map_or(false, |x| x.legs.len() == 1) {
            self.singles.push(gig);
        }
        self.posts.push(PostRec { post, orders });
        self.booked.push(false);
    }
    /// `singles`: the gigs that carry one one-car order and can still be a partner or a ride back. A gig leaves the
    /// list for good once it carries nothing (its legs moved to a later gig or were delivered) or its order became
    /// urgent or goes alone: none of these is ever undone, so dropping it changes no later answer.
    fn prune_singles(&mut self) {
        let mut list = std::mem::take(&mut self.singles);
        list.retain(|&g| { let o = self.posts[g].orders[0]; self.is_live(g) && !self.urgent[o] && !self.solo[o] });
        self.singles = list;
    }
    fn send_post_of(&mut self, w: &mut World, o: usize) {
        if self
            .outbox
            .iter()
            .any(|a| matches!(a, Action::Post(p) if p.stops[0].order == o))
        {
            self.send(w);
        }
    }
    fn send(&mut self, w: &mut World) {
        let actions = std::mem::take(&mut self.outbox);
        if !actions.is_empty() {
            let results = w.act(&actions);
            self.read_results(w, actions, &results);
        }
    }
    fn read_results(&mut self, w: &World, actions: Vec<Action>, results: &[Option<usize>]) {
        for (i, action) in actions.into_iter().enumerate() {
            let Some(id) = results[i] else { continue };
            match action {
                Action::Post(post) => self.carry(w, post, id),
                Action::Reprice { gig, schedule } => {
                    if let Some(j) = self.journal.as_mut() { let _ = writeln!(j, "reprice {} {} {}", World::gig_id(gig), num(self.now), sched_str(&schedule)); }
                }
                Action::Withdraw { gig } => {
                    if let Some(j) = self.journal.as_mut() { let _ = writeln!(j, "wd {} {}", World::gig_id(gig), num(self.now)); }
                }
                Action::Quote { .. } => {}
            }
        }
    }
}

fn legs_of(post: &Post) -> Vec<usize> {
    let mut out: Vec<usize> = Vec::with_capacity(2);
    for s in &post.stops { if s.pickup && !out.contains(&s.leg) { out.push(s.leg); } }
    out
}
fn without_windows(mut stops: Vec<Stop>, before: f64) -> Vec<Stop> {
    for s in &mut stops { if let Some(w) = s.window { if w.1 < before { s.window = None; } } }
    stops
}
fn narrower(mut stop: Stop, window: (f64, f64), base: (f64, f64)) -> Stop {
    if window.0 > base.0 || window.1 < base.1 { stop.window = Some(window); }
    stop
}
/// The kit's keyword note reader: the text work is done in prep.ts, this applies its ranges and clock times.
fn window_from_note(parts: &Option<WinParts>, window: (f64, f64), delivery: bool) -> (f64, f64) {
    let Some(parts) = parts else { return window };
    if parts.delivery != delivery { return window; }
    let day_start = |t: f64| (t / DAY).floor() * DAY;
    let (mut from, mut to) = window;
    for r in &parts.ranges {
        from = from.max(day_start(from) + r[0]);
        to = to.min(day_start(to) + r[1]);
    }
    for c in &parts.clocks {
        let time = day_start(window.0) + c[0];
        if c[1] == 1.0 { from = from.max(time); } else { to = to.min(time); }
    }
    if from <= to { (from, to) } else { window }
}

// ── notes.ts: slots inside the real site hours ──
fn open_span(hours: &Option<Hours>, day: f64) -> Option<(f64, f64)> {
    let Some(h) = hours else { return Some((day * DAY, (day + 1.0) * DAY)) };
    let weekday = day % 7.0;
    if weekday >= 0.0 && (h.wd >> (weekday as u32)) & 1 == 1 { return Some((day * DAY + h.opens, day * DAY + h.closes)); }
    if weekday == 5.0 { if let Some(s) = h.sat { return Some((day * DAY + s[0], day * DAY + s[1])); } }
    None
}
fn day_slot(pickup: &Option<Hours>, delivery: &Option<Hours>, travel: f64, day: f64) -> Option<(f64, f64)> {
    let p = open_span(pickup, day)?;
    for arrive in [day, day + 1.0] {
        let Some(d) = open_span(delivery, arrive) else { continue };
        let from = p.0.max(d.0 - travel);
        let to = p.1.min(d.1 - travel);
        if from <= to { return Some((from, to)); }
    }
    None
}
fn next_slot(pickup: &Option<Hours>, delivery: &Option<Hours>, travel: f64, from: f64, min_left: f64) -> Option<(f64, f64)> {
    let mut day = (from / DAY).floor();
    let end = day + 9.0;
    while day <= end {
        if let Some(slot) = day_slot(pickup, delivery, travel, day) {
            if slot.1 - slot.0.max(from) >= min_left { return Some((slot.0.max(from), slot.1)); }
        }
        day += 1.0;
    }
    None
}
fn last_slot(pickup: &Option<Hours>, delivery: &Option<Hours>, travel: f64, from: f64, due: f64) -> Option<f64> {
    let mut day = ((due - travel) / DAY).floor();
    let first = (from / DAY).floor();
    while day >= first {
        if let Some(slot) = day_slot(pickup, delivery, travel, day) {
            let to = slot.1.min(due - travel);
            if to >= slot.0.max(from) { return Some(to); }
        }
        day -= 1.0;
    }
    None
}

// ── model.ts: the booking model and the fee planner ──
#[inline]
fn sigmoid(z: f64) -> f64 {
    1.0 / (1.0 + crate::fexp::exp(-z))
}
#[inline]
fn fee_logit(b: &Book, r: f64) -> f64 {
    b.r * r + b.r_hi1 * (r - 1.0).max(0.0) + b.r_hi2 * (r - 1.4).max(0.0)
}
/// log1p tables for whole minutes and whole hours (the same expressions the planner would compute each time).
struct Ln1p { hours: Vec<f64>, minutes: Vec<f64> }
static LN1P: std::sync::LazyLock<Ln1p> = std::sync::LazyLock::new(|| Ln1p {
    hours: (0..73).map(|k| (k as f64).ln_1p()).collect(),
    minutes: (0..=LN_MIN_MAX).map(|m| (m as f64 / HOUR).ln_1p()).collect(),
});
const LN_MIN_MAX: usize = 30240;
/// log1p(minutes / 60) for minutes >= 0.
#[inline]
fn ln1p_min(t: &Ln1p, minutes: f64) -> f64 {
    let m = minutes as usize;
    if m as f64 == minutes && m <= LN_MIN_MAX { t.minutes[m] } else { (minutes / HOUR).ln_1p() }
}
/// What a search grid (opening fees x raises) needs over and over: the opening fees as the search steps through
/// them, and for the estimate the fee levels open_min + 0.05 n with exp(-fee logit) of each.
pub struct PlanTab {
    key: [f64; 4],
    ok: bool,
    s: usize,
    opens: Vec<f64>,
    r: Vec<f64>,
    f: Vec<f64>,
}
pub struct PlanPre { z0: u64, now: u64, n: usize, z: [f64; 72] }
pub struct PlanTabsData { tabs: Vec<PlanTab>, pre: PlanPre }
pub type PlanTabs = std::cell::RefCell<PlanTabsData>;
fn plan_tab(b: &Book, p: &PlanP) -> PlanTab {
    let mut opens = Vec::new();
    let mut open = p.open_min;
    while open <= p.open_min.max(p.open_max) + 1e-9 && opens.len() <= 64 {
        opens.push(open);
        open += 0.05;
    }
    let ok = p.open_min >= 0.0 && p.late_cost >= 0.0 && p.steps >= 0.0 && p.steps <= 72.0 && p.steps.fract() == 0.0 && !opens.is_empty() && opens.len() <= 64;
    let s = if ok { p.steps as usize } else { 0 };
    let n = opens.len() + 4 * s + 16;
    let r: Vec<f64> = (0..n).map(|i| p.open_min + 0.05 * i as f64).collect();
    let f = r.iter().map(|&x| crate::fexp::exp(-fee_logit(b, x))).collect();
    PlanTab { key: [p.open_min, p.open_max, p.raise_max, p.steps], ok, s, opens, r, f }
}

/// The cheapest fee schedule for a gig: every opening fee and raise, hour by hour to the last pickup time.
/// Same result as model.ts plan(), bit for bit. First an estimate of every candidate's cost (the same sum with
/// exp(-a-b) taken as exp(-a) x exp(-b), right to about 1e-10); then only the candidates whose estimate is within
/// 1e-8 of the lowest are evaluated with the original operations, in the original order. A candidate left out
/// costs more than the cheapest by far more than the estimate can be wrong, so it could never be chosen.
fn plan(b: &Book, x: &GigX, now: f64, typical: f64, last_pickup_at: f64, ready_at: f64, p: &PlanP, tabs: &PlanTabs) -> Plan {
    crate::prof!(4);
    let hours = ((last_pickup_at - now) / HOUR).ceil().max(1.0).min(72.0) as usize;
    let c = &b.c;
    let tab = &*LN1P;
    // the part of the base logit that does not depend on the hour (the first terms of the sum, in the same order)
    let mut z0 = b.intercept;
    z0 += c[0] * x.near_p.ln_1p();
    z0 += c[1] * x.near_d.ln_1p();
    z0 += c[2] * x.near_p80.ln_1p();
    z0 += c[3] * x.near_d80.ln_1p();
    z0 += c[4] * x.drive_h;
    z0 += c[5] * if x.drive_h >= 5.0 { 1.0 } else { 0.0 };
    z0 += c[6] * if x.cars > 1.0 { 1.0 } else { 0.0 };
    z0 += c[7] * x.priv_p;
    z0 += c[8] * x.priv_d;
    z0 += c[9] * x.premium;
    z0 += c[10] * x.load.min(3.0);
    z0 += c[11] * x.typ.max(1.0).ln();
    #[cfg(feature = "prof")]
    let g1 = crate::prof::on::Guard(14, crate::prof::on::tsc());
    let mut base = [0.0f64; 72];
    // The sum up to the age term is the same for every option of a request (same gig, same minute): kept from the
    // last call and reused when gig and minute are the same. The terms after it are added in the original order.
    let mut tabs_mut = tabs.borrow_mut();
    let pre = &mut tabs_mut.pre;
    if !(pre.z0 == z0.to_bits() && pre.now == now.to_bits()) {
        pre.z0 = z0.to_bits();
        pre.now = now.to_bits();
        pre.n = 0;
    }
    let whole = now >= 0.0 && now < 1e9 && now.fract() == 0.0;
    while pre.n < hours {
        let k = pre.n;
        let t = now + k as f64 * HOUR;
        let (hour, day) = if whole {
            let ti = now as u64 + 60 * k as u64;
            (((ti % 1440) / 60) as f64, ((ti / 1440) % 7) as f64)
        } else {
            (((t % DAY) / HOUR).floor(), (t / DAY).floor() % 7.0)
        };
        let age = (t - now).max(0.0) / HOUR;
        let mut z = z0;
        z += c[12] * if hour >= 23.0 || hour < 7.0 { 1.0 } else { 0.0 };
        z += c[13] * if hour >= 7.0 && hour < 10.0 { 1.0 } else { 0.0 };
        z += c[14] * if hour >= 16.0 && hour < 20.0 { 1.0 } else { 0.0 };
        z += c[15] * if hour >= 20.0 && hour < 23.0 { 1.0 } else { 0.0 };
        z += c[16] * if day == 5.0 { 1.0 } else { 0.0 };
        z += c[17] * if day == 6.0 { 1.0 } else { 0.0 };
        z += c[18] * if age == k as f64 { tab.hours[k] } else { age.ln_1p() };
        pre.z[k] = z;
        pre.n += 1;
    }
    for k in 0..hours {
        let t = now + k as f64 * HOUR;
        let left = ((last_pickup_at - t) / HOUR).max(0.0).min(96.0);
        let mut z = pre.z[k];
        // left = min(96, max(0, minutes / 60)): for whole minutes in [0, 5760] that is minutes / 60 itself
        let lm = last_pickup_at - t;
        z += c[19] * if lm >= 0.0 && lm <= 5760.0 { ln1p_min(tab, lm) } else { left.ln_1p() };
        z += c[20] * if left < 3.0 { 1.0 } else { 0.0 };
        z += c[21] * ln1p_min(tab, (ready_at - t).max(0.0));
        z += c[22] * 0.0;
        base[k] = z;
    }
    drop(tabs_mut);
    #[cfg(feature = "prof")]
    drop(g1);
    // the original evaluation of one candidate
    let cost_of = |open: f64, raise: f64| -> (f64, f64) {
        // the fees and chances of all hours first (the chances side by side), then the sums in hour order
        let (mut r, mut fl, mut ch) = ([0.0f64; 72], [0.0f64; 72], [0.0f64; 72]);
        for k in 0..hours {
            r[k] = open + raise * (k as f64).min(p.steps);
            fl[k] = fee_logit(b, r[k]);
        }
        crate::fexp::sigmoid_sum(&base[..hours], &fl[..hours], &mut ch[..hours]);
        let (mut unbooked, mut cost) = (1.0, 0.0);
        for k in 0..hours {
            cost += unbooked * ch[k] * r[k];
            unbooked *= 1.0 - ch[k];
        }
        (cost + unbooked * p.late_cost, unbooked)
    };
    let key = [p.open_min, p.open_max, p.raise_max, p.steps];
    let mut tabs_all = tabs.borrow_mut();
    let tabs = &mut tabs_all.tabs;
    let ti = match tabs.iter().position(|t| t.key == key) {
        Some(i) => i,
        None => {
            if tabs.len() >= 8 { tabs.clear(); }
            tabs.push(plan_tab(b, p));
            tabs.len() - 1
        }
    };
    let pt = &tabs[ti];
    let n_open = pt.opens.len();
    const RAISES: [(f64, usize); 4] = [(0.0, 0), (0.05, 1), (0.1, 2), (0.2, 4)];
    let allowed = |raise: f64| !(raise > p.raise_max + 1e-9 || (raise > 0.0 && p.steps < 1.0));
    // the estimate of every candidate, eight opening fees side by side
    #[cfg(feature = "prof")]
    let g2 = crate::prof::on::Guard(21, crate::prof::on::tsc());
    let mut est = [f64::INFINITY; 4 * 64];
    let mut use_est = pt.ok;
    if use_est {
        let mut e = [0.0f64; 72];
        for k in 0..hours { e[k] = crate::fexp::exp(-base[k]); }
        let wide = crate::fexp::has8();
        let mut lowest = f64::INFINITY;
        let margin = 1e-8 * (2.0 + p.late_cost + pt.r[pt.r.len() - 1]);
        for (ri, &(raise, m)) in RAISES.iter().enumerate() {
            if !allowed(raise) { continue; }
            let mut i0 = 0;
            while i0 < n_open {
                let cut = lowest + margin;
                let mut cost = [0.0f64; 8];
                // what is paid so far + the rest at the current fee (fees only rise) or the late cost is the least
                // a candidate can still cost: when that is above the lowest estimate for all eight, they are out
                let kept = if wide {
                    unsafe { crate::fexp::est8(&e[..hours], &pt.f, &pt.r, i0, m, pt.s, p.late_cost, cut, &mut cost) }
                } else {
                    let mut unb = [1.0f64; 8];
                    let mut kept = true;
                    for k in 0..hours {
                        let off = i0 + m * k.min(pt.s);
                        let (fs, rs, ek) = (&pt.f[off..off + 8], &pt.r[off..off + 8], e[k]);
                        if k & 3 == 0 {
                            let mut least = f64::INFINITY;
                            for l in 0..8 { least = least.min(cost[l] + unb[l] * rs[l].min(p.late_cost)); }
                            if least > cut { kept = false; break; }
                        }
                        for l in 0..8 {
                            let ch = 1.0 / (1.0 + ek * fs[l]);
                            cost[l] += unb[l] * ch * rs[l];
                            unb[l] *= 1.0 - ch;
                        }
                    }
                    for l in 0..8 { cost[l] += unb[l] * p.late_cost; }
                    kept
                };
                if !kept { i0 += 8; continue; }
                for l in 0..8.min(n_open - i0) {
                    let a = cost[l];
                    est[ri * 64 + i0 + l] = a;
                    if !(a >= 0.0) || !a.is_finite() { use_est = false; }
                    if a < lowest { lowest = a; }
                }
                i0 += 8;
            }
        }
        let limit = lowest + margin;
        for a in est.iter_mut() { if *a <= limit { *a = f64::NEG_INFINITY; } } // marked: evaluate
    }
    #[cfg(feature = "prof")]
    drop(g2);
    #[cfg(feature = "prof")]
    let _g3 = crate::prof::on::Guard(23, crate::prof::on::tsc());
    let (mut best_cost, mut best_chance, mut best_open, mut best_raise) = (f64::INFINITY, 0.0, p.open_max, 0.0);
    for (ri, &(raise, _)) in RAISES.iter().enumerate() {
        if !allowed(raise) { continue; }
        if use_est {
            for i in 0..n_open {
                if est[ri * 64 + i] != f64::NEG_INFINITY { continue; }
                let (cost, unbooked) = cost_of(pt.opens[i], raise);
                if cost < best_cost { best_cost = cost; best_chance = 1.0 - unbooked; best_open = pt.opens[i]; best_raise = raise; }
            }
        } else {
            let mut open = p.open_min;
            while open <= p.open_min.max(p.open_max) + 1e-9 {
                let (cost, unbooked) = cost_of(open, raise);
                if cost < best_cost { best_cost = cost; best_chance = 1.0 - unbooked; best_open = open; best_raise = raise; }
                open += 0.05;
            }
        }
    }
    let steps = if best_raise > 0.0 { jround(p.steps) } else { 0.0 } as usize;
    let schedule = (0..=steps).map(|k| (now + k as f64 * HOUR, jround(typical * (best_open + k as f64 * best_raise)).max(1.0))).collect();
    Plan { schedule, fee: best_cost * typical, chance: best_chance, open: best_open, raise: best_raise }
}
/// Raise early, not near the pickup: a gig nobody booked climbs hourly from its last planned fee to `ramp_top` × typical.
fn with_ramp(mut schedule: Schedule, typical: f64, last_pickup_at: f64, ramp_top: f64, ramp_window_h: f64) -> Schedule {
    let last = *schedule.last().unwrap();
    let end = last_pickup_at - 3.0 * HOUR;
    let start = (last.0 + HOUR).max(last_pickup_at - ramp_window_h * HOUR);
    let top = jround(typical * ramp_top);
    if top <= last.1 || end < start { return schedule; }
    let n = (48.0 - schedule.len() as f64).min((((end - start) / HOUR).floor() + 1.0).max(1.0));
    let mut k = 0.0;
    while k < n {
        schedule.push((start + k * HOUR, jround(last.1 + ((top - last.1) * (k + 1.0)) / n)));
        k += 1.0;
    }
    schedule
}
/// Sum of the trees' leaves, in tree order. Every tree has depth <= `depth` and its leaves point at themselves
/// (data.rs), so eight trees walk side by side for a fixed number of steps.
fn predict(t: &FastTrees, x: &[f64]) -> f64 {
    crate::prof!(5);
    assert!(x.len() >= t.n_features);
    const LANES: usize = 8;
    let mut sum = t.base;
    let n = t.roots.len();
    let mut k = 0;
    while k < n {
        let m = (n - k).min(LANES);
        let mut i = [0usize; LANES];
        for j in 0..m { i[j] = t.roots[k + j] as usize; }
        for _ in 0..t.depth {
            for j in 0..LANES {
                // in range by construction: every `l` and `l + 1` is a node, every `f` a feature (checked above)
                let nd = unsafe { t.nodes.get_unchecked(i[j]) };
                i[j] = nd.l as usize + (!(unsafe { *x.get_unchecked(nd.f as usize) } <= nd.t)) as usize;
            }
        }
        for j in 0..m { sum += t.val[i[j]]; }
        k += m;
    }
    sum
}

// ── algo.ts ──
impl<'a> Desk<'a> {
    fn plan_p(&self) -> PlanP {
        PlanP { late_cost: self.p.lateCost, open_min: self.p.openMin, open_max: self.p.openMax, steps: self.p.steps, raise_max: self.p.raiseMax }
    }
    fn gig_x(&self, legs: &[&Leg], typical_cents: f64, counts_itself: bool) -> GigX {
        let st = self.st;
        let first = legs[0].p;
        let last = legs[legs.len() - 1].d;
        let near_p = self.near30[first];
        let any = |f: fn(&Leg) -> bool| if legs.iter().any(|l| f(l)) { 1.0 } else { 0.0 };
        GigX {
            near_p, near_d: self.near30[last], near_p80: self.near80[first], near_d80: self.near80[last],
            drive_h: legs.iter().fold(0.0, |s, l| s + st.road(l.p, l.d)) / HOUR, cars: legs.len() as f64,
            priv_p: any(|l| l.p_priv), priv_d: any(|l| l.d_priv), premium: any(|l| l.premium),
            load: (self.open_from[first] - if counts_itself { 1.0 } else { 0.0 }).max(0.0) / near_p.max(1.0), typ: typical_cents / 100.0,
        }
    }
    /// Our one-car orders whose gig is open and not booked.
    fn open_singles(&self) -> Vec<usize> {
        crate::prof!(6);
        let mut out = Vec::new();
        for &g in &self.singles {
            if self.booked[g] || !self.is_live(g) || self.is_pair(g) { continue; }
            let o = self.posts[g].post.stops[0].order;
            if let Some(order) = self.orders[o].as_ref() { if order.legs.len() == 1 && !self.urgent[o] && !self.solo[o] { out.push(o); } }
        }
        out
    }

    /// Which options to sell and at what price: None = decline.
    fn algo_quote(&mut self, w: &World, i: usize) -> Option<[Option<f64>; 3]> {
        crate::prof!(1);
        let st = self.st;
        let p = &self.p;
        let req = &self.data.requests[i];
        let now = self.now;
        let ref_fee = w.ref_fee[i];
        let note_dl = req.deliver_by;
        let stated = req.legs.iter().fold(req.arrived_at, |m, l| m.max(l.p_from));
        // a car that is ready a day or more later moves its deadline by the same days (weekends do not count)
        let moved = |deadline: f64| {
            let mut days = ((req.ready_from.unwrap_or(0.0) / DAY).floor() - (stated / DAY).floor()).max(0.0);
            let mut day = (deadline / DAY).floor();
            while days > 0.0 { day += 1.0; if day % 7.0 < 5.0 { days -= 1.0; } }
            day * DAY + (deadline % DAY)
        };
        let due = |o: &Opt| match note_dl { Some(n) => moved(o.deadline).min(n), None => moved(o.deadline) };
        let drive = req.legs.iter().fold(0.0, |s, l| s + st.road(l.p, l.d));
        let ready = stated.max(req.ready_from.unwrap_or(0.0));
        let sites = if p.noteHours > 0.0 { req.noted.as_ref() } else { None };
        let last_pickup = |o: &Opt| match sites { Some(s) => last_slot(&s.pickup, &s.delivery, drive, ready, due(o)).unwrap_or(f64::NEG_INFINITY), None => due(o) - drive };

        // capacity rules: a full pickup town or a full deadline day is priced higher, not declined
        let supply = req.legs.iter().fold(f64::INFINITY, |m, l| m.min(self.near30[l.p]));
        // research/supply: town utilisation u = our open orders around the pickup over capPerDriver x the drivers around it
        let np = st.np();
        let pick0 = req.legs[0].p;
        let u_town = if p.ballKm > 0.0 {
            let load = (0..np).fold(0.0, |s, q| s + self.open_from[q] * self.ball_w[pick0 * np + q]);
            let cap = p.capPerDriver * self.sup_ball[pick0];
            if cap > 0.0 { load / cap } else { 1e9 }
        } else { let cap = p.capPerDriver * supply; if cap > 0.0 { self.open_from[pick0] / cap } else { 1e9 } };
        let supply_models = p.ballKm > 0.0 || p.smoothS > 0.0 || p.capU > 0.0;
        let town_full = if supply_models { u_town >= 1.0 } else { self.open_from[req.legs[0].p] >= p.capPerDriver * supply };
        let n_roster = self.data.roster.len() as f64;
        let due_cap = jround(p.dueCapPer * n_roster);
        let day_full = |deadline: f64| { let day = (deadline / DAY).floor(); due_cap > 0.0 && day <= 4.0 && self.due_on[day as usize] >= due_cap };
        let day_soft = |deadline: f64| -> f64 { let day = (deadline / DAY).floor(); if due_cap > 0.0 && day <= 4.0 { sigmoid((self.due_on[day as usize] / due_cap - p.smoothAt) / p.smoothS) } else { 0.0 } };

        // for each option: the cheapest fee schedule, its expected cost, and the chance a driver books in time
        let legs: Vec<&Leg> = req.legs.iter().collect();
        let gig = self.gig_x(&legs, ref_fee, false);
        let pp = self.plan_p();
        let mut plans: Vec<(&Opt, Plan)> = Vec::with_capacity(3);
        for o in &req.options {
            let lp = last_pickup(o);
            if !(lp - ready >= p.minSlackH * HOUR) || !(lp - now >= 0.0) { continue; }
            if o.kind == 0 && p.sdMinH > 0.0 && lp - now < p.sdMinH * HOUR { continue; }
            plans.push((o, plan(&st.book, &gig, now, ref_fee, lp, ready, &pp, &self.tabs)));
        }
        let use_cost = p.costW > 0.0;
        // research/supply R: how far this week's delivered orders ended from what the trees said (multiples of the typical fee)
        let mut res_shift = 0.0;
        if p.resK != 0.0 && use_cost {
            let pred = self.pred.borrow();
            let (mut sum, mut cnt) = (0.0, 0.0);
            for &k in &w.order_list {
                let o = w.orders[k].as_ref().unwrap();
                let pr = pred[k][o.option];
                if o.delivered && pr.is_finite() { sum += ((w.o_fee[k] + w.o_tail[k]) / w.ref_fee[k].max(1.0)).min(4.0) - pr; cnt += 1.0; }
            }
            if cnt > 0.0 { res_shift = p.resK * sum / (cnt + p.resN); }
        }
        // costRow's counts over our orders that are the same for every option
        let (pick, del) = (req.legs[0].p, req.legs[req.legs.len() - 1].d);
        let (mut chain_in, mut chain_out) = (0.0, 0.0);
        if use_cost && !plans.is_empty() {
            for q in 0..st.np() {
                if st.km(q, pick) <= 30.0 { chain_in += self.open1_d[q]; }
                if st.km(del, q) <= 30.0 { chain_out += self.open1_p[q]; }
            }
        }
        let dealer = self.dealers[req.dealer];
        let min_chance = if p.hardPrice > 0.0 { p.minBookChance.min(p.hardChance) } else { p.minBookChance };
        let mut options: Vec<(&Opt, Plan, f64)> = Vec::with_capacity(3);
        let (mut xb_mean, mut xb_q80, mut binned) = ([0u8; 256], [0u8; 256], false);
        for (o, pl) in plans {
            let cost = if !use_cost { pl.fee } else {
                let d = due(o);
                let near_p = self.near30[pick];
                let typ = ref_fee.max(1.0);
                let due_day = (d / DAY).floor();
                let due_load = if due_day >= 0.0 && due_day < 64.0 { self.due_on[due_day as usize] } else { 0.0 };
                let roster = n_roster.max(1.0);
                let any = |f: fn(&Leg) -> bool| if req.legs.iter().any(|l| f(l)) { 1.0 } else { 0.0 };
                let x = [
                    drive / HOUR, (typ / 100.0).ln(), w.typ_raw[i].unwrap_or(typ) / typ, near_p, self.near30[del], self.near80[pick], self.near80[del],
                    self.open_from[pick] / near_p.max(1.0), self.open_all / roster, any(|l| l.p_priv), any(|l| l.d_priv),
                    any(|l| l.premium), any(|l| l.electric), req.legs.len() as f64,
                    req.options.len() as f64, o.kind as f64, (d - drive - now) / HOUR, (ready - now).max(0.0) / HOUR, (d - ready - drive) / HOUR,
                    ((now % DAY) / HOUR).floor(), (now / DAY).floor() % 7.0, due_day.min(8.0), due_load / roster, chain_in, chain_out, dealer.0, dealer.1,
                    req.ready_from.is_some() as u8 as f64, note_dl.is_some() as u8 as f64,
                    pl.fee / typ, pl.chance, pl.open, pl.raise, st.lat[pick], st.lon[pick], st.lat[del], st.lon[del], roster,
                ];
                // the ranks of the inputs among the trees' thresholds: all of them for the request's first option,
                // then only the inputs that differ between options
                if p.dumpRows > 0.0 { self.dump_x.borrow_mut().push((i, o.kind, x)); }
                const VARY: [usize; 9] = [15, 16, 18, 21, 22, 29, 30, 31, 32];
                let head = |bt: &BinTrees, ft: &FastTrees, xb: &mut [u8; 256], fresh: bool| -> f64 {
                    if !bt.ok { return predict(ft, &x); }
                    if fresh { for f in 0..bt.thr.len().min(x.len()) { xb[f] = bt.rank(f, x[f]); } } else { for &f in &VARY { if f < bt.thr.len() { xb[f] = bt.rank(f, x[f]); } } }
                    bt.walk(xb)
                };
                let mean = head(&st.bin_mean, &st.fast_mean, &mut xb_mean, !binned);
                // costUp = 0 leaves the mean as it is: mean + 0 × anything finite
                let est = if p.costUp == 0.0 { mean } else { mean + p.costUp * (head(&st.bin_q80, &st.fast_q80, &mut xb_q80, !binned) - mean).max(0.0) };
                let est = if p.lateW > 0.0 { est + p.lateW * sigmoid(head(&st.bin_q80, &st.fast_q80, &mut xb_q80, !binned)) } else { est };
                binned = true;
                if p.resK != 0.0 { self.pred.borrow_mut()[i][o.kind] = est; }
                let est = est + res_shift;
                (1.0 - p.costW) * pl.fee + p.costW * est * ref_fee
            };
            if pl.chance >= min_chance { options.push((o, pl, cost)); }
        }
        if options.is_empty() { return None; }

        // one markup for the request: the highest chance to win × (price − expected fee − capacity cost)
        let n = options.len() as f64;
        let list = options.iter().fold(0.0, |s, o| s + o.0.list) / n;
        let fee = options.iter().fold(0.0, |s, o| s + o.2) / n;
        let x = ReqX {
            pickup: req.legs[0].p, delivery: req.legs[0].d, drive_h: drive / HOUR, trade_in: if req.legs.len() > 1 { 1.0 } else { 0.0 },
            priv_d: if req.legs.iter().any(|l| l.d_priv) { 1.0 } else { 0.0 }, same_day: if req.options.iter().any(|o| o.kind == 0) { 1.0 } else { 0.0 },
            n_opt: req.options.len() as f64, trust: dealer.0, lates: dealer.1,
        };
        let base = win_base(&st.win, &x);
        let hour_now = ((now % DAY) / HOUR).floor();
        let today = (now / DAY).floor() * DAY;
        let mut shift = 0.0;
        if p.smoothS > 0.0 { shift += p.fullPrice * sigmoid((u_town - p.smoothAt) / p.smoothS); } else if town_full { shift += p.fullPrice; }
        if drive / HOUR < p.shortH { shift += p.shortShift; }
        if drive / HOUR > p.longH { shift += p.longShift; }
        if p.floorTyp > 0.0 { shift -= p.floorTyp * (p.floorTypRef - ref_fee / list).max(0.0); }
        // research/supply W: greedier early in the week, pickier late
        let day_now = (now / DAY).floor();
        if day_now == 0.0 { shift += p.wkMon; } else if day_now == 1.0 { shift += p.wkTue; } else if day_now == 3.0 || day_now == 4.0 { shift += p.wkLate; }
        // research/supply L: live backlog of our orders that no driver has booked, against the roster
        if p.backK != 0.0 || p.curve > 0.0 {
            let mut open = 0.0;
            for &o in &self.order_list {
                let Some(order) = self.orders[o].as_ref() else { continue };
                if !order.delivered_at.iter().any(|t| t.is_none()) { continue; }
                if p.backDueH > 0.0 && order.last_pickup_at - now > p.backDueH * HOUR { continue; }
                if !self.gigs_of(o).iter().any(|&g| self.booked[g]) { open += 1.0; }
            }
            let b = open / n_roster.max(1.0);
            if p.curve > 0.0 {
                let mid = p.cLo + p.cDead;
                shift += if b <= p.cLo { -p.cDown * (((p.cLo - b) / p.cLo.max(1e-9)) * p.cSteep).min(1.0) } else if b <= mid { 0.0 } else { p.cCap * ((b - mid) / p.cSpan.max(1e-9)).min(1.0).powf(p.cPow) };
            } else {
            shift += if p.backPow > 0.0 && b > p.backAt { (p.backUp * ((b / p.backAt).powf(p.backPow) - 1.0)).min(0.3) } else { (p.backK * (b - p.backAt)).max(-p.backDown).min(0.3) };
            }
        }
        // a car that rides back with an open gig of ours costs a driver no trip home
        if req.legs.len() == 1 {
            let leg = &req.legs[0];
            if self.open_singles().iter().any(|&o| { let l = &self.orders[o].as_ref().unwrap().legs[0]; st.km(l.d, leg.p) <= p.pairKm && st.km(leg.d, l.p) <= p.pairKm }) { shift -= p.pairBack; }
        }
        // competitor outage: today's answers near this pickup beating the win model by outageGap
        if hour_now >= 8.0 && hour_now < 18.0 {
            let (mut cnt, mut sum) = (0.0, 0.0);
            // (not in time order: the world's clock can step back after a pickup that waits for opening)
            for a in &self.answers_at {
                if a.at >= today + 8.0 * HOUR && st.km(a.place, req.legs[0].p) <= 80.0 { cnt += 1.0; sum = sum + a.won - a.chance; }
            }
            if cnt >= p.outageN && sum / cnt >= p.outageGap { shift += p.outage; }
        }
        // capacity cost: a car that holds a driver longer must earn more
        let lam_c = p.capLam * 100.0 * (drive / HOUR + p.capConst) / (1.0 - (p.capU * u_town).min(0.75));
        let mut markup = p.markupMin;
        let mut best = f64::NEG_INFINITY;
        let parts = if p.priceLearn > 0.0 { Some(self.price_parts(req, drive, dealer)) } else { None };
        let (mut mu, mut scale) = (0.0, 1.0);
        if let Some((g, h)) = &parts {
            mu = *g;
            let mut v = 0.0;
            for &a in h { mu += self.pf_x[a]; for &b in h { v += self.pf_p[a * self.n_state + b]; } }
            scale = (p.pS * p.pS + 0.37 * v).sqrt();
        }
        // BEST10: in a cheap week or on a cheap day the floor follows the learned level
        if let (Some((_, h)), true) = (&parts, p.floorLvl > 0.0) {
            let level = self.pf_x[0] + self.pf_x[h[1]];
            if level < 0.0 { shift += (p.floorLvl * level).max(-0.2); }
        }
        // the markups tried and their logs: the same for every request with the same shift (a handful of values)
        let start = p.markupMin + shift;
        let top = p.markupMin.max(p.markupMax) + shift + 1e-9;
        let mut cache = self.ln_m.borrow_mut();
        let ci = match cache.iter().position(|c| c.0 == start.to_bits() && c.1 == top.to_bits()) {
            Some(ci) => ci,
            None => {
                let mut list = Vec::new();
                let mut m = start;
                while m <= top { list.push((m, m.ln())); m += 0.01; }
                if cache.len() >= 64 { cache.clear(); }
                cache.push((start.to_bits(), top.to_bits(), list));
                cache.len() - 1
            }
        };
        for &(m, ln_m) in &cache[ci].2 {
            let chance = if parts.is_some() { 1.0 / (1.0 + crate::fexp::exp(-(mu - ln_m) / scale)) } else { 1.0 / (1.0 + (-(base + st.win.ln_m * ln_m + self.world_level)).exp()) };
            let value = chance * (m * list - fee - lam_c);
            if value > best { best = value; markup = m; }
        }
        drop(cache);

        let mut prices = [None; 3];
        let mut any = false;
        for (o, pl, cost) in &options {
            let due_day = (due(o) / DAY).floor();
            let by_day = (if due_day >= 7.0 { p.dueMon } else if due_day == 4.0 { p.dueFri } else { 0.0 }) + if o.kind == 0 { p.sdShift } else { 0.0 };
            let price = jround(o.list * (markup + by_day) * (if p.smoothS > 0.0 { 1.0 + p.fullPrice * day_soft(o.deadline) } else if day_full(o.deadline) { 1.0 + p.fullPrice } else { 1.0 }) * (if pl.chance < p.minBookChance { 1.0 + p.hardPrice } else { 1.0 }));
            if price >= cost * (1.0 + p.minProfit) { prices[o.kind] = Some(price); any = true; }
        }
        if !any { return None; }
        // what we expected, so learn() can compare it with the dealer's answer
        self.quoted[i] = Some(base + st.win.ln_m * markup.ln());
        if let Some((g, h)) = parts { self.pq[i] = Some(Quoted { g, h, lm: markup.ln() }); }
        Some(prices)
    }
    /// ln(price it takes to win, × list): the fixed parts and the indices of this week's learned parts.
    fn price_parts(&self, req: &Req, drive: f64, d: (f64, f64)) -> (f64, [usize; 5]) {
        let pr = &self.st.price;
        let (a, b) = (req.legs[0].p, req.legs[0].d);
        let dealer = (self.n_dealer as f64 - 1.0).min(req.dealer_num) as usize;
        let hour = ((req.arrived_at % DAY) / HOUR).floor().max(7.0).min(18.0) as usize;
        let g = pr.c + pr.b[0] * (0.01 * d.0).ln_1p() + pr.b[1] * (drive / 600.0) + pr.b[2] * (req.legs.len() as f64 - 1.0) + pr.b[3] * (req.options.len() as f64 - 1.0)
            + pr.lane[a * 30 + b] + pr.pick[a] + pr.del[b] + pr.hour[hour] + pr.dealer[dealer] + (self.st.win.lates * d.1) / self.st.win.ln_m.abs();
        (g, [0, 1 + (req.arrived_at / DAY).floor().min(4.0) as usize, 6 + dealer, 6 + self.n_dealer + a, 36 + self.n_dealer + b])
    }

    /// The fee schedule of a gig. `fee` is the gig's share of the typical fee.
    fn algo_fees(&self, o: usize, fee: f64, legs: &[usize], urgent: bool) -> Schedule {
        crate::prof!(22);
        let st = self.st;
        let p = &self.p;
        let now = self.now;
        let req = &self.data.requests[o];
        let order = self.orders[o].as_ref().unwrap();
        let job_drive = order.legs.iter().fold(0.0, |s, l| s + st.road(l.p, l.d));
        let mut lp = match req.deliver_by { Some(by) => order.last_pickup_at.min(by - job_drive), None => order.last_pickup_at };
        let sites = if p.noteHours > 0.0 { req.noted.as_ref() } else { None };
        if let Some(s) = sites { lp = lp.min(last_slot(&s.pickup, &s.delivery, job_drive, order.legs[0].p_from, order.deadline).unwrap_or(lp)); }
        // late anyway: paying more buys nothing, so go back to lateFee and climb slowly
        if urgent && p.lateFee > 0.0 && now >= lp {
            return (0..5).map(|k| (now + k as f64 * 6.0 * HOUR, jround(fee * p.lateFee.max(2.0).min(p.lateFee + 0.2 * k as f64)).max(1.0))).collect();
        }
        // after a deadline warning: steepOpen, then +steepStep every half hour
        if urgent { return (0..5).map(|k| (now + k as f64 * 30.0, jround(fee * (p.steepOpen + k as f64 * p.steepStep)).max(1.0))).collect(); }
        let gl: Vec<&Leg> = legs.iter().map(|&l| &order.legs[l]).collect();
        let schedule = plan(&st.book, &self.gig_x(&gl, fee, true), now, fee, lp, gl[0].p_from, &self.plan_p(), &self.tabs).schedule;
        if p.rampTop > 0.0 { with_ramp(schedule, fee, lp, p.rampTop, p.rampWindowH) } else { schedule }
    }

    /// Two cars, one driver: the schedule of the two-car gig and its score among partners.
    fn algo_pair(&self, chain: [usize; 2], typical: f64, join_km: f64, back_km: f64, slack: f64) -> Option<(Schedule, f64)> {
        let p = &self.p;
        if join_km > p.pairKm || slack < p.pairSlackH * HOUR { return None; }
        let legs: Vec<&Leg> = chain.iter().map(|&c| &self.orders[c].as_ref().unwrap().legs[0]).collect();
        let lp = self.now + slack;
        let mut pp = self.plan_p();
        pp.open_max = p.openMax.min(p.pairCap);
        let best = plan(&self.st.book, &self.gig_x(&legs, typical, true), self.now, typical, lp, legs[0].p_from, &pp, &self.tabs);
        let cap = jround(typical * p.pairCap);
        let schedule: Schedule = best.schedule.iter().map(|s| (s.0, s.1.min(cap))).collect();
        Some((with_ramp(schedule, typical, lp, p.pairTop, p.rampWindowH), -join_km - 0.5 * back_km))
    }

    /// This week's competitor price level, from one win or loss.
    fn learn(&mut self, id: usize, won: bool) {
        crate::prof!(2);
        let p = &self.p;
        let won = if won { 1.0 } else { 0.0 };
        let n = self.n_state;
        if p.priceLearn > 0.0 {
            if let Some(q) = self.pq[id].take() {
                // rows whose prior spread is 0 stay all zero for the week: only the others (`act`) are worked on
                let act = &self.pf_act;
                let col = |pm: &[f64], out: &mut [f64]| { for &i in act.iter() { out[i] = q.h.iter().fold(0.0, |s, &j| s + pm[i * n + j]) / p.pS; } };
                let chance = 1.0 / (1.0 + (-(q.g + q.h.iter().fold(0.0, |s, &i| s + self.pf_x[i]) - q.lm) / p.pS).exp());
                let wt = chance * (1.0 - chance);
                let mut pa = [0.0f64; 256];
                col(&self.pf_p, &mut pa);
                let k = wt / (1.0 + (wt * q.h.iter().fold(0.0, |s, &i| s + pa[i])) / p.pS);
                for &i in act.iter() { if pa[i] != 0.0 { for &j in act.iter() { self.pf_p[i * n + j] -= pa[i] * pa[j] * k; } } }
                let mut gain = [0.0f64; 256];
                col(&self.pf_p, &mut gain);
                for &i in act.iter() { self.pf_x[i] += gain[i] * (won - chance); }
            }
        }
        let Some(expected) = self.quoted[id].take() else { return };
        // for the outage rule: each answer with where it was and what the model expected
        self.answers_at.push(Answer { at: self.now, place: self.data.requests[id].legs[0].p, won, chance: 1.0 / (1.0 + (-(expected + self.world_level)).exp()) });
        self.ans_z.push(expected);
        self.ans_won.push(won);
        // the last worldN answers: the window slides over the two lists (emptied of old answers now and then)
        let mut from = self.ans_from;
        while (self.ans_z.len() - from) as f64 > p.worldN { from += 1; }
        if from > 4096 {
            self.ans_z.drain(..from);
            self.ans_won.drain(..from);
            from = 0;
        }
        self.ans_from = from;
        let (zs, wons) = (&self.ans_z[from..], &self.ans_won[from..]);
        self.ans_chance.resize(zs.len(), 0.0);
        // one-number logistic fit (4 Newton steps) with a prior
        let sd = self.st.win.worldSd;
        let prior = 1.0 / (sd * sd);
        let mut wl = self.world_level;
        for _ in 0..4 {
            let (mut slope, mut curve) = (-wl * prior, prior);
            // the chances first (side by side), then the two sums in the order of the answers
            crate::fexp::sigmoid_shift(zs, wl, &mut self.ans_chance);
            for k in 0..zs.len() {
                let chance = self.ans_chance[k];
                slope += wons[k] - chance;
                curve += chance * (1.0 - chance);
            }
            wl += slope / curve;
        }
        self.world_level = wl;
    }

    /// A pickup and a delivery for each leg; a charging stop for an EV under 30%; windows narrowed by the note.
    fn stops_for(&self, o: usize, legs: &[usize], retry: Retry, sites: Option<&Sites>) -> Vec<Stop> {
        let req = &self.data.requests[o];
        let order = self.orders[o].as_ref().unwrap();
        let mut out = Vec::with_capacity(legs.len() * 2);
        for &leg in legs {
            let l = &order.legs[leg];
            let low = l.electric && matches!(l.charge, Some(c) if c < 30.0);
            let first = Stop { order: o, leg, pickup: true, window: None, with_plates: retry.plates, with_charging: low };
            let second = Stop { order: o, leg, pickup: false, window: None, with_plates: false, with_charging: false };
            if let Some(s) = sites {
                // real site hours from the note: one day's slot at a time
                let travel = s.drive + if retry.plates { 30.0 } else { 0.0 } + if low { 40.0 } else { 0.0 };
                let start = s.now.max(l.p_from).max(retry.pickup_from).max(req.ready_from.unwrap_or(0.0));
                let mut slot = next_slot(&s.pickup, &s.delivery, travel, start, s.min_left);
                if let (Some(sl), true) = (slot, l.p_priv) { slot = if sl.1 < l.p_from || sl.0 > l.p_to { None } else { Some((sl.0.max(l.p_from), sl.1.min(l.p_to))) }; }
                if let Some(sl) = slot {
                    let mut a = first.clone();
                    if !l.p_priv { a.window = Some(sl); }
                    let mut b = second.clone();
                    if s.delivery.is_some() { b.window = Some(((sl.0 + travel).max(l.d_from), sl.1 + travel)); }
                    out.push(a);
                    out.push(b);
                    continue;
                }
            }
            let pw = (l.p_from, l.p_to);
            let noted = window_from_note(&req.win, pw, false);
            let start = noted.0.max(retry.pickup_from).max(req.ready_from.unwrap_or(0.0));
            let pickup_window = (start, noted.1.max(start));
            let delivery_base = (l.d_from, l.d_from.max(order.deadline));
            let kit = window_from_note(&req.win, delivery_base, true);
            let delivery_window = match req.deliver_by { Some(by) if by > kit.0 => (kit.0, kit.1.min(by)), _ => kit };
            out.push(narrower(first, pickup_window, pw));
            out.push(narrower(second, delivery_window, delivery_base));
        }
        out
    }
}
