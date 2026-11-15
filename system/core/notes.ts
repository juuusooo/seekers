/**
 * notes.ts — reads a dealer's note (Finnish, Swedish, English) for the two facts that make a car late:
 *   readyFrom   the car cannot be collected before this minute   ("valmis vasta huomenna klo 14")
 *   deliverBy   the car must be at the destination by this minute ("perillä viim. to klo 13")
 * Rules of the game: days count from the day the request arrives; a weekday name is 2 to 6 days ahead; digits are
 * a 24-hour clock unless am/pm follows; an hour in words is a working hour (9 to 17); a correction counts, a denied
 * time does not. Checked against the reveals of 48 weeks with an/notes_check.ts.
 */
const DAY = 1440
const WORD_HOURS: [RegExp, number][] = [
  [/yhdeksä|yhdeksält|nio|nine/, 9], [/kymmen|tio\b|\bten\b/, 10], [/yksitoista|yhde[a-zä]*toista|elva|eleven/, 11], [/kaksitoista|kahde[a-zä]*toista|kahteentoista|tolv|twelve|\bnoon\b/, 12],
  [/yhdeltä|yhdelta|yhteen|\byhden\b|\byksi\b|\bett\b|\bone\b/, 13], [/kahdelta|kahteen|\bkahden\b|\bkaksi\b|\btvå\b|\btva\b|\btwo\b/, 14], [/kolmelta|kolmeen|\bkolmen\b|\bkolme\b|\btre\b|\bthree\b/, 15],
  [/neljältä|neljalta|\bneljän\b|neljään|neljaan|\bneljä\b|\bfyra\b|\bfour\b/, 16], [/viideltä|viidelta|\bviiden\b|viiteen|\bviisi\b|\bfem\b|\bfive\b/, 17],
]
const WEEKDAYS: RegExp[] = [
  /\bma\b|maanan?t|maanat|\bmån\b|\bman\b|måndag|mandag|\bmon\b|monday/, /\bti\b|tiist|\btis\b|tisdag|\btue\b|\btues\b|tuesday/, /\bke\b|keskiv|\bons\b|onsdag|\bwed\b|wednesday/,
  /\bto\b|torst|\btors\b|torsdag|\bthu\b|\bthur\b|\bthurs\b|thursday/, /\bpe\b|perjan|\bfre\b|fredag|\bfri\b|friday/, /\bla\b|lauant|\blör\b|lördag|\bsat\b|saturday/,
]
// Words that carry the meaning, for typos ("huoenna", "pejrantaina", "deestination"): a word within one or two
// letters of one of these is read as that word.
const LEXICON = ["huomenna", "ylihuomenna", "tomorrow", "tänään", "today", "maanantaina", "tiistaina", "keskiviikkona", "torstaina", "perjantaina", "maanantai", "tiistai", "keskiviikko", "torstai", "perjantai",
  "monday", "tuesday", "wednesday", "thursday", "friday", "måndag", "tisdag", "onsdag", "torsdag", "fredag", "valmis", "destination", "perillä", "mennessä", "viimeistään", "aikaisintaan", "noudettavissa",
  "senast", "tidigast", "latest", "earliest", "ready", "luovutus", "maksettu", "korjaus", "kiinni"]
function distance(a: string, b: string): number {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array<number>(b.length).fill(0)])
  for (let j = 1; j <= b.length; j++) d[0]![j] = j
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) {
    d[i]![j] = Math.min(d[i - 1]![j]! + 1, d[i]![j - 1]! + 1, d[i - 1]![j - 1]! + (a[i - 1] === b[j - 1] ? 0 : 1))
    if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i]![j] = Math.min(d[i]![j]!, d[i - 2]![j - 2]! + 1)
  }
  return d[a.length]![b.length]!
}
const SPELL = new Map<string, string>()
function spell(word: string): string {
  if (word.length < 5 || /\d/.test(word)) return word
  let known = SPELL.get(word)
  if (known === undefined) {
    known = word
    if (!LEXICON.includes(word)) for (const w of LEXICON) if (Math.abs(w.length - word.length) <= 2 && distance(word, w) <= (w.length >= 8 ? 2 : 1)) { known = w; break }
    SPELL.set(word, known)
  }
  return known
}
const READY = /auton saa|payment|clears|no pickup|först|forst|luovutetaan|kesken|odottaa|workshop|verkstad|maksun|maksettu|pays first|once paid|after payment|betal|valmis|vamis|valmistuu|aikaisintaan|alkaen|alken|saa hakea|haettavissa|voi noutaa|voi hakea|noudettavissa|noudettaivssa|jälkeen|jalkeen|\bready\b|not before|earliest|\bafter\b|pickup from|tidigast|klar\b|efter\b|hämtas|hamtas/
const BY = /tulee hakemaan|picks it up|kunden hämtar|must be there|perill|toimitus|oltava|mennessä|mennessa|menessä|destination|destiation|dsetination|deliver|arriv|at the customer|framme|på plats|pa plats|levere|vara där|vara dar/
const SHUT = /kiinni|closes|closed|nobody|stänger|stangt|stängt|\bauki\b|\bopen\b|öppet/
const BY_WORD = /viim|mennessä|mennessa|menessä|\bby\b|latest|no later|senast|måste|maste|must/
const HOURS_RANGE = /\b\d{1,2}(?:[.:]\d{2})?\s*[-–]\s*\d{1,2}(?:[.:]\d{2})?\b/g
const DENIED = /\(?\s*(?:ei|not|inte|ej)\s+(?:klo\.?|kl\.?|kello|at|klockan)?\s*\d{1,2}(?:[.:]\d{2})?\s*(?:am|pm)?\s*\)?/g

/** Minutes of the day in a clause: the LAST time counts (a correction comes after what it corrects). */
function clock(text: string): number | null {
  let found: number | null = null, at = -1
  const digits = /(?:klo\.?|kl\.?|kello|klockan|at)?\s*\b(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)?\b/g
  for (const m of text.matchAll(digits)) {
    let hour = Number(m[1])
    const minute = Number(m[2] ?? 0)
    if (hour > 24 || minute > 59) continue
    if (m[3] === "pm" && hour < 12) hour += 12
    if (m[0].trim().length <= 2 && !/klo|kl|kello|klockan|at/.test(m[0]) && m[2] === undefined && m[3] === undefined) {
      // a bare number: a time only when a time word stands right before it
      if (!/(?:klo\.?|kl\.?|kello|klockan|huomenna|morgon|tomorrow|tmrw|vasta|viim\.?|latest|by|from|before|after|jälkeen|[a-zåäö]{2,}na|day)\s*$/.test(text.slice(0, m.index! + (m[0].length - m[0].trimStart().length)))) continue
    }
    if (m.index! > at) [found, at] = [hour * 60 + minute, m.index!]
  }
  for (const [word, hour] of WORD_HOURS) {
    const m = word.exec(text)
    if (!m || m.index <= at) continue
    const half = /puoli\s*$|half\s*$|halv\s*$/.test(text.slice(0, m.index))
    ;[found, at] = [hour * 60 - (half ? 30 : 0), m.index]
  }
  return found
}

/** The day a clause names, as days after the arrival day; null = none named (then: the arrival day). */
function dayOffset(text: string, arrivedWeekday: number): number | null {
  if (/ylihuomenna|övermorgon|overmorgon|day after tomorrow/.test(text)) return 2
  if (/huomenna|huomena|i morgon|imorgon|imorron|tomorrow|tomrorow|tomorow|tmrw|tmr\b/.test(text)) return 1
  if (/tänään|tanaan|idag|i dag|today/.test(text)) return 0
  for (let d = 0; d < WEEKDAYS.length; d++) {
    if (!WEEKDAYS[d]!.test(text)) continue
    let ahead = (d - arrivedWeekday + 7) % 7
    if (ahead < 2) ahead += 7
    return ahead
  }
  return null
}

export function readNote(note: string | undefined | null, arrivedAt: number): { readyFrom: number | null; deliverBy: number | null } {
  const out = { readyFrom: null as number | null, deliverBy: null as number | null }
  if (!note) return out
  const day0 = Math.floor(arrivedAt / DAY) * DAY, weekday = Math.floor(arrivedAt / DAY) % 7
  let last: "readyFrom" | "deliverBy" | null = null
  let lastDay = 0
  // Clauses: sentences, and the two languages of a "fi / en" note. A dot inside a time (10.30) or after "viim" is not an end.
  const clauses = note.toLowerCase().replace(/[a-zåäö]+/g, spell).replace(/viim\./g, "viim ").replace(/klo\./g, "klo ").replace(/kl\./g, "kl ").replace(/\bma\./g, "ma ").replace(/\bto\./g, "to ").split(/(?<!\d)\.(?!\d)|\.(?=\s|$)|!|\s\/\s|;/)
  for (const raw of clauses) {
    const text = raw.replace(DENIED, " ").replace(HOURS_RANGE, " ")
    const fix = /korjaus|eikun|ei kun|rättelse|rattelse|correction|sorry|siis/.test(text)
    const by = !SHUT.test(text) && BY.test(text) && (BY_WORD.test(text) || /perill|destination|framme|på plats|hakemaan|picks it up|hämtar/.test(text))
    const ready = !by && !SHUT.test(text) && READY.test(text) && !/ready now|valmis,|heti|redan klar|klar nu/.test(text)
    const role = by ? "deliverBy" : ready ? "readyFrom" : fix ? last : null
    if (!role) continue
    // "ennen klo 19" in a pickup clause is the site's closing time, not a ready time
    const cut = role === "readyFrom" && !/not ready|not before|ei ennen|no pickup|inte före|won.t be ready/.test(text) ? text.replace(/(?<!ei |not |inte )(?:ennen|before|före|innan)\s+(?:klo|kl|kello)?\s*\d{1,2}(?:[.:]\d{2})?/g, " ") : text
    const named = dayOffset(cut, weekday)
    // a correction of the day alone ("Correction: Monday") keeps the time
    const time = clock(cut) ?? (fix && role === last && named !== null && out[role] !== null ? out[role]! % DAY : null)
    if (time === null) continue
    const days = named ?? (fix && role === last ? lastDay : 0)
    out[role] = day0 + days * DAY + time
    last = role
    lastDay = days
  }
  return out
}

// ─── Site hours ──────────────────────────────────────────────────────────────────────────────
// A note can say that a site really closes earlier or opens later than the request states ("Liike kiinni klo 16",
// "Receiving until 15:30 only", "aukioloajat 10-14.30"). Hours with no site named are the pickup site's; the
// delivery site is always named. Right on 99.7% (pickup) and 99.9% (delivery) of 32,600 such notes of won orders,
// and no false alarm on 99.95% of all notes (research/notes/hours.py is the same reader in Python).
type Hours = { opens: number; closes: number; weekdays: number[]; saturday: { opens: number; closes: number } | null }
const H_WORDS: [RegExp, number][] = [
  [/yhdeksä|yhdeksää|\bnio\b|\bnine\b/, 9], [/kymmen|\btio\b|\bten\b/, 10], [/yksitoista|yhde[a-zä]*toista|\belva\b|eleven/, 11], [/kaksitoista|kahde[a-zä]*toi|kahteentoista|\btolv\b|twelve|\bnoon\b/, 12],
  [/yhdeltä|yhteen|\byhden\b|\byksi\b|\bett\b|\bone\b/, 13], [/kahdelta|kahteen|\bkahden\b|\bkaksi\b|\bkahta\b|\btvå\b|\btwo\b/, 14], [/kolmelta|kolmeen|\bkolmen\b|\bkolmea?\b|\btre\b|\bthree\b/, 15],
  [/neljältä|neljään|\bneljän\b|\bneljää?\b|\bfyra\b|\bfour\b/, 16], [/viideltä|viiteen|\bviiden\b|\bviisi\b|viittä|\bfem\b|\bfive\b/, 17],
]
const H_T = String.raw`(\d{1,2})(?:[.:](\d{2}))?(?::?(?:stä|sta|ään|aan|een|n))?\s*(am|pm)?`
const H_RANGE = new RegExp(H_T + String.raw`\s*(?:[-–]|to\b|till\b)\s*` + H_T.replace("(am|pm)?", "(am|pm|noon)?") + "|" + H_T + String.raw`\s*[-–]\s*(noon)`)
const H_FI_RANGE = /(\d{1,2}):?(?:stä|sta)\s+(\d{1,2})(?:[.:](\d{2}))?:?(?:ään|aan|een)/
const H_ONE = new RegExp(String.raw`\b` + H_T + String.raw`\b`, "g")
const H_DENIED = /\(?\b(?:ei|not|inte|ej)\s+(?:klo\.?|kl\.?|kello|at|klockan)?\s*\d{1,2}(?:[.:]\d{2})?\s*(?:am|pm)?\s*\)?/g
const H_DELIVERY = /vast+a+n?ot|vastaanot|kohde|kohtee|kohtes|peril|preil|perl+[aä]|toimitusos|receiv|recieiv|destin|detin|mottag|leverans|drop.?off/
const H_PICKUP = /hämtas|hamtas|hakea|\bshop\b|liike|meillä|onnistuu|auki|kiinni|aukiolo|avoinna|\bopen|clos|öppet|oppet|öppettid|stäng|stang|nouto|noud|haettava|\bhaku\b|collect|pick.?up|hämtning|hamtning|ketään|ketaan|nobody|luovutu|utlämning|utlamning|täällä|taalla|sulke/
const H_SHUT = /pick.?up (?:by|no later)|haku viim|nouto viim|hämtas senast|hämtning senast|ingen|onnistuu|auki|kiinni|aukiolo|avoinna|\bopen|clos|öppet|oppet|öppettid|stäng|stang|sulke|ketään|ketaan|nobody|asti|saakka|until|\btill\b|luovutuks|utlämning|utlamning|vastaanot|receiving|mottagning|\bonly\b|\bvain\b|ennen|before|före|innan/
const H_DEADLINE = /viim|mennessä|mennessa|menessä|\bby\b|latest|no later|senast|måste|maste|must|hakemaan|hämtar|picks it up|silloin/
const H_ARRIVE = /peril|perl+[aä]|toimitus(?!os)|destin|arriv|framme|på plats|pa plats|deliver|oltava|hakemaan|hämtar|picks it up|there/
const H_READY = /från|fran\b|no pickup|before that|valmis|vlamis|valmii|ready|klar\b|alkaen|alken|aikaisintaan|vasta\b|tidigast|först|forst|earliest|not before|\bfrom\b|maksu|payment|pays|betal|huolto|workshop|verkstad|pesu/
const H_CLOSING = /kiinni|clos|stäng|stang|ketään|nobody|asti|saakka|until|sulke/
const H_CALL = /(?:n\.?\s*)?(?:\d+\s*min[a-zåäö]*|tuntia|tnutia|tntia|an hour|en timme)?\s*(?:ennen|before|före|innan)\s+(?:noutoa|kuin|pickup|you|arrival|saapumista|perillä|ankomst|avfärd)/g
const H_LEXICON = ["vastaanotto", "vastaanottava", "vastaanottaja", "vastaanotot", "perillä", "destination", "receiving", "mottagaren", "mottagning", "aukioloajat", "haettava", "pickup", "closes", "kiinni", "sulkee",
  "noudettavissa", "hämtning", "öppettider", "luovutuksia", "utlämning", "kohde", "collect", "before", "stänger", "toimitusosoite", "betalning", "valmis", "korjaus", "correction"]
const H_SPELL = new Map<string, string>()
function hSpell(word: string): string {
  if (word.length < 5) return word
  let known = H_SPELL.get(word)
  if (known === undefined) {
    known = word
    if (!H_LEXICON.includes(word)) for (const w of H_LEXICON) if (Math.abs(w.length - word.length) <= 2 && distance(word, w) <= (w.length >= 9 ? 2 : 1)) { known = w; break }
    H_SPELL.set(word, known)
  }
  return known
}
function hClock(h: string | undefined, m: string | undefined, ap: string | undefined | null): number | null {
  let hour = Number(h)
  const minute = Number(m ?? 0)
  if (ap === "pm" && hour < 12) hour += 12
  return hour <= 24 && minute < 60 ? hour * 60 + minute : null
}
function hLast(text: string): number | null {
  let best: number | null = null, at = -1
  for (const m of text.matchAll(H_ONE)) {
    const v = hClock(m[1], m[2], m[3])
    if (v !== null && m.index! > at) [best, at] = [v, m.index!]
  }
  for (const [word, hour] of H_WORDS) {
    const m = word.exec(text)
    if (!m || m.index <= at) continue
    const half = /(puoli|puolta|half|halv)\s*$/.test(text.slice(0, m.index))
    ;[best, at] = [hour * 60 - (half ? 30 : 0), m.index]
  }
  return best
}

export type NoteHours = { pickupOpens: number | null; pickupCloses: number | null; deliveryOpens: number | null; deliveryCloses: number | null }
/** The real weekday hours a note gives, as minutes of the day; null where the note leaves the stated hours alone. */
export function readHours(note: string | undefined | null, statedPickup: Hours | null, statedDelivery: Hours | null): NoteHours {
  const out: NoteHours = { pickupOpens: null, pickupCloses: null, deliveryOpens: null, deliveryCloses: null }
  if (!note) return out
  let text = note.toLowerCase().replace(/[a-zåäö]+/g, hSpell).replaceAll("viim.", "viim ").replaceAll("klo.", "klo ").replaceAll("kl.", "kl ")
  text = text.replace(H_CALL, " ").replace(/\d+\s*min[a-zåäö]*/g, " ")
  text = text.replace(/(klo|kl|kello|klockan|at|by|until|before|ennen|viimeistään|senast|than)\s+([01]\d|2[0-3])([0-5]\d)\b/g, "$1 $2:$3")
  let last: "pickup" | "delivery" | null = null
  for (const raw of text.split(/(?<!\d)\.(?!\d)|\.(?=\s|$)|!|\s\/\s|;/)) {
    const c = raw.replace(H_DENIED, " ")
    const fix = /korjaus|korjus|eikun|ei kun|rättelse|rattelse|correct|sorry|siis|förlåt|forlat/.test(c)
    let site: "pickup" | "delivery" | null = H_DELIVERY.test(c) ? "delivery" : H_PICKUP.test(c) ? "pickup" : null
    if (site === null && fix && last) site = last
    else if (site === null) continue
    const fr = H_FI_RANGE.exec(c)
    const r = fr ? null : H_RANGE.exec(c)
    let opens: number | null = null, closes: number | null = null
    if (fr) [opens, closes] = [hClock(fr[1], undefined, null), hClock(fr[2], fr[3], null)]
    else if (!r) {
      // one time: a deadline at the destination, a payment or a ready time is not a closing time
      if (!H_SHUT.test(c) && !(fix && last)) { last = null; continue }
      if (H_DEADLINE.test(c) && H_ARRIVE.test(c) && !H_CLOSING.test(c)) { last = null; continue }
      if (/no pickup|before that|maksu|payment|betal/.test(c)) { last = null; continue }
      if (H_READY.test(c) && !/kiinni|clos|stäng|stang|ketään|nobody|asti|saakka|until|sulke|ennen|before|ei enää|ingen|\bby\b/.test(c)) { last = null; continue }
      closes = hLast(c)
    } else if (r[7] !== undefined) [opens, closes] = [hClock(r[7], r[8], r[9]), 720] // "9 am-noon"
    else {
      closes = r[6] === "noon" ? 720 : hClock(r[4], r[5], r[6])
      const a = Number(r[1]), b = Number(r[4])
      opens = hClock(r[1], r[2], r[3] ?? (r[6] === "pm" && a > b ? "am" : r[6] === "pm" && a < b && a < 8 ? "pm" : null))
      if (fix) closes = hLast(c.slice(r.index + r[0].length)) ?? closes
    }
    const stated = site === "delivery" ? statedDelivery : statedPickup
    if (stated === null || closes === null) continue
    if (site === "delivery") { out.deliveryCloses = closes < stated.closes ? closes : null; if (opens !== null) out.deliveryOpens = opens > stated.opens ? opens : null }
    else { out.pickupCloses = closes < stated.closes ? closes : null; if (opens !== null) out.pickupOpens = opens > stated.opens ? opens : null }
    last = site
  }
  return out
}

/** The hours of a site with the note's real weekday hours put in. */
export const realHours = (stated: Hours | null, opens: number | null, closes: number | null): Hours | null => (stated ? { ...stated, opens: opens ?? stated.opens, closes: closes ?? stated.closes } : null)
const DAY_MIN = 1440
/** When the site is open on the day `day` (days from Monday 00:00): [from, to] in world minutes, or null. A null site (private address) is always open. */
function openSpan(hours: Hours | null, day: number): [number, number] | null {
  if (!hours) return [day * DAY_MIN, (day + 1) * DAY_MIN]
  const weekday = day % 7
  if (hours.weekdays.includes(weekday)) return [day * DAY_MIN + hours.opens, day * DAY_MIN + hours.closes]
  if (weekday === 5 && hours.saturday) return [day * DAY_MIN + hours.saturday.opens, day * DAY_MIN + hours.saturday.closes]
  return null
}
/** Pickup minutes of one day that are inside the pickup site's hours and arrive (`travel` minutes later) inside the delivery site's. */
function daySlot(pickup: Hours | null, delivery: Hours | null, travel: number, day: number): [number, number] | null {
  const p = openSpan(pickup, day)
  if (!p) return null
  for (const arriveDay of [day, day + 1]) {
    const d = openSpan(delivery, arriveDay)
    if (!d) continue
    const from = Math.max(p[0], d[0] - travel), to = Math.min(p[1], d[1] - travel)
    if (from <= to) return [from, to]
  }
  return null
}
/** The first pickup slot from minute `from` on that still has `minLeft` minutes in it (looks 9 days ahead). */
export function nextSlot(pickup: Hours | null, delivery: Hours | null, travel: number, from: number, minLeft: number): { from: number; to: number } | null {
  for (let day = Math.floor(from / DAY_MIN), end = day + 9; day <= end; day++) {
    const slot = daySlot(pickup, delivery, travel, day)
    if (slot && slot[1] - Math.max(slot[0], from) >= minLeft) return { from: Math.max(slot[0], from), to: slot[1] }
  }
  return null
}
/** The last minute to collect the car inside both sites' real hours and still arrive by `due`; null when there is none after `from`. */
export function lastSlot(pickup: Hours | null, delivery: Hours | null, travel: number, from: number, due: number): number | null {
  for (let day = Math.floor((due - travel) / DAY_MIN), first = Math.floor(from / DAY_MIN); day >= first; day--) {
    const slot = daySlot(pickup, delivery, travel, day)
    if (!slot) continue
    const to = Math.min(slot[1], due - travel)
    if (to >= Math.max(slot[0], from)) return to
  }
  return null
}

/** The real hours of both sites when the note of a one-car order changes them: the pickup site's hours (null at a
 *  private address) and the delivery site's only when the note changed them (the world handles stated hours itself). */
export function notedHours(note: string | undefined | null, legs: { pickup: { hours: Hours | null }; delivery: { hours: Hours | null } }[]): { pickup: Hours | null; delivery: Hours | null } | null {
  if (!note || legs.length !== 1) return null
  const { pickup, delivery } = legs[0]!
  const h = readHours(note, pickup.hours, delivery.hours)
  if (h.pickupOpens === null && h.pickupCloses === null && h.deliveryOpens === null && h.deliveryCloses === null) return null
  return { pickup: realHours(pickup.hours, h.pickupOpens, h.pickupCloses), delivery: h.deliveryOpens === null && h.deliveryCloses === null ? null : realHours(delivery.hours, h.deliveryOpens, h.deliveryCloses) }
}

