#!/usr/bin/env python3
"""Bahn-Spread research paper trail. Same system as /root/system/research/ (see README.md).
Safe when several sessions write at once (file lock). Every command adds a line to ACTIVITY.md.

  log.py find WORD [WORD ...]
        RECALL. Lines of LEDGER / KNOWLEDGE / BACKLOG / GOTCHAS and topic logs (also archive/)
        holding every word. Run before any new test.
  log.py open TOPIC "hypothesis" "base, seeds, metric" "kill criteria"
        Start a study: creates TOPIC/LOG.md (or adds a block), puts an `open` row on the ledger.
  log.py close TOPIC STATUS "test, base, seeds, numbers" "verdict"
        Finish it: the topic's open row becomes the result row, on top.
  log.py add TOPIC STATUS "test, base, seeds, numbers" "verdict"
        One-shot: a quick test or a dead end that had no open row.
  log.py archive TOPIC
        Move a finished topic folder to archive/ and repoint its ledger links.
  log.py note "text"
        Anything that is not research (housekeeping, tools, bugs): one line in ACTIVITY.md only.
  log.py topics
        Topics with row counts by status.

STATUS: open | shipped (in the best model) | ship-candidate (gain, not yet proved on h- seeds)
        | no-edge | inconclusive | parked | fact (a measurement)

The ledger is research only: a row needs a question and a result (or an open plan). Folder moves,
clean-ups, tool and doc changes, bug fixes, replay checks and "started" notes are NOT ledger rows:
use `note`.
"""

import fcntl
import getpass
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "LEDGER.md"
ACTIVITY = HERE / "ACTIVITY.md"
STATUSES = (
    "open",
    "shipped",
    "ship-candidate",
    "no-edge",
    "inconclusive",
    "parked",
    "fact",
)
SEP = "|---|---|---|---|---|"
INDEX = ("LEDGER.md", "KNOWLEDGE.md", "BACKLOG.md", "GOTCHAS.md")


def cell(text):
    return " ".join(text.split()).replace("|", "\\|")


def plain(topic):
    return re.sub(r"\[(.*?)\]\(.*?\)", r"\1", topic)


def cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]


def is_row(line):
    return line.startswith("| ") and not line.startswith("| When")


def activity(action, topic, extra=""):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    with open(ACTIVITY, "a") as f:
        f.write(f"{stamp} {getpass.getuser()} {action} {topic} {extra}".rstrip() + "\n")


def topic_cell(topic):
    for base in (topic, f"archive/{topic}"):
        if (HERE / base / "LOG.md").exists():
            return f"[{topic}]({base}/LOG.md)"
    return topic


def write_ledger(change):
    """change(lines) edits the ledger lines in place, under the lock."""
    with open(LEDGER, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        lines = f.read().splitlines()
        change(lines)
        tmp = LEDGER.with_suffix(".tmp")
        tmp.write_text("\n".join(lines) + "\n")
        os.replace(tmp, LEDGER)


def add(topic, status, text, verdict, close=False):
    status = status.lower()
    if status not in STATUSES:
        sys.exit(f"STATUS must be one of: {', '.join(STATUSES)}")
    row = f"| {datetime.now():%d %b %H:%M} | {topic_cell(topic)} | {status} | {cell(text)} | {cell(verdict)} |"

    def change(lines):
        if close:
            mine = [
                i
                for i, ln in enumerate(lines)
                if is_row(ln)
                and plain(cells(ln)[1]) == topic
                and cells(ln)[2] == "open"
            ]
            if not mine:
                sys.exit(f"no open row for topic '{topic}': use `add`")
            del lines[mine[0]]
        lines.insert(lines.index(SEP) + 1, row)

    write_ledger(change)
    activity(
        "CLOSE" if close else "OPEN" if status == "open" else "LOG",
        topic,
        f"status={status}",
    )
    print(row)
    if status != "open":
        print(
            "Next: KNOWLEDGE.md if a belief changed, GOTCHAS.md if a trap bit, delete the BACKLOG.md row."
        )


def open_topic(topic, hypothesis, plan, kill):
    folder = HERE / topic
    folder.mkdir(exist_ok=True)
    log = folder / "LOG.md"
    if not log.exists():
        log.write_text(f"# {topic}: log\n")
    with open(log, "a") as f:
        f.write(
            f"\n## {datetime.now():%d %b %H:%M} · open\n"
            f"- **Hypothesis:** {hypothesis}\n"
            f"- **Base, seeds, metric:** {plan}\n"
            f"- **Kill criteria:** {kill}\n"
            f"- **What I did:**\n- **Result / verdict:**\n- **Next:**\n"
        )
    add(topic, "open", f"{hypothesis} ({plan})", f"kill: {kill}")
    print(f"Detail goes in {log.relative_to(HERE)}")


def find(words):
    low = [w.lower() for w in words]
    files = (
        [HERE / n for n in INDEX]
        + sorted(HERE.glob("*/LOG.md"))
        + sorted(HERE.glob("archive/*/LOG.md"))
    )
    hits = 0
    for path in files:
        for line in path.read_text().splitlines():
            if line.strip() and all(w in line.lower() for w in low):
                print(f"{path.relative_to(HERE)}: {line}\n")
                hits += 1
    activity("RECALL", "+".join(words), f"hits={hits}")
    print(f"{hits} hits." + ("" if hits else " Nothing on record: new ground."))


def archive(topic):
    src, dst = HERE / topic, HERE / "archive" / topic
    if not src.is_dir() or dst.exists():
        sys.exit(f"cannot archive '{topic}'")
    dst.parent.mkdir(exist_ok=True)

    def change(lines):
        for i, ln in enumerate(lines):
            lines[i] = ln.replace(f"]({topic}/", f"](archive/{topic}/")

    write_ledger(change)
    src.rename(dst)
    activity("ARCHIVE", topic)
    print(f"{topic} -> archive/{topic}")


def topics():
    seen = defaultdict(Counter)
    for line in LEDGER.read_text().splitlines():
        if is_row(line):
            c = cells(line)
            seen[plain(c[1])][c[2]] += 1
    for topic, c in sorted(seen.items(), key=lambda kv: -sum(kv[1].values())):
        print(
            f"{topic:16} {sum(c.values()):3}  "
            + "  ".join(f"{k} {v}" for k, v in c.most_common())
        )


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "find":
        find(a[1:])
    elif len(a) == 5 and a[0] == "open":
        open_topic(*a[1:])
    elif len(a) == 5 and a[0] in ("add", "close"):
        add(*a[1:], close=a[0] == "close")
    elif len(a) == 2 and a[0] == "archive":
        archive(a[1])
    elif len(a) == 2 and a[0] == "note":
        activity("NOTE", a[1])
    elif a == ["topics"]:
        topics()
    else:
        sys.exit(__doc__)
