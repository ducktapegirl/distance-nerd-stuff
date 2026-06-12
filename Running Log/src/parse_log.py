#!/usr/bin/env python3
"""
parse_log.py — Parse Alisha's running log HTML files into a CSV.

Usage:   python src/parse_log.py  (from the Running Log/ directory)
Output:  running_log.csv  (written to Running Log/, one level up from this script)
Source:  source/  (HTML log files read from Running Log/source/)

Requires: pip install beautifulsoup4 lxml
"""

import os
import re
import csv
from datetime import date

from bs4 import BeautifulSoup, NavigableString

# ─── Configuration ────────────────────────────────────────────────────────────

SRC_DIR    = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SRC_DIR)   # Running Log/
SOURCE_DIR = os.path.join(BASE_DIR, "source")

# Files in chronological order: (season, year-suffix-string)
FILES = [
    ("fall",   "03"),
    ("winter", "03"),
    ("spring", "04"), ("summer", "04"), ("fall", "04"), ("winter", "04"),
    ("spring", "05"), ("summer", "05"), ("fall", "05"), ("winter", "05"),
    ("spring", "06"), ("summer", "06"), ("fall", "06"), ("winter", "06"),
    ("spring", "07"),
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MONTHS = {
    "January": 1, "February": 2, "March": 3,    "April": 4,
    "May": 5,     "June": 6,     "July": 7,      "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

# Placeholder values that should be treated as missing data
PLACEHOLDERS = {"-", "–", "—", "\u00a0", "", "n/a", "N/A"}

CSV_COLUMNS = [
    "date", "year", "month", "day", "day_of_week", "week_of_year",
    "season",
    "workout_type",
    "minutes", "minutes_raw",
    "miles",
    "pace_min_per_mile",
    "comments", "extras",
    "is_race", "race_name", "race_distance", "race_time",
    "source_file",
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def resolve_year(season, file_year_int, month_int):
    """
    Map (season, file-year-int, month) → calendar year.
    For winter files: December stays in file_year, Jan–Aug bumps to file_year+1.
    Example: winter03 → Dec→2003, Jan/Feb/Mar→2004.
    """
    if season == "winter":
        return 2000 + file_year_int if month_int >= 9 else 2001 + file_year_int
    return 2000 + file_year_int


def cell_text(node):
    """Extract plain text from a tag, collapsing whitespace."""
    return re.sub(r'\s+', ' ', node.get_text(separator=" ")).strip()


def cell_text_with_br(td):
    """
    Extract text from a <td>, replacing <br> tags with newlines instead of
    collapsing them.  Used for Distance: and Time: cells so that multi-event
    entries like 'mile/4x800m' / '5:37.31<br>2:35 split' are preserved.
    """
    parts = []
    for node in td.descendants:
        if isinstance(node, NavigableString):
            # Collapse ALL whitespace within each text node (including HTML
            # indentation newlines) to a single space — only actual <br> tags
            # should become newline separators between events.
            parts.append(re.sub(r"\s+", " ", str(node)))
        elif getattr(node, "name", None) == "br":
            parts.append("\n")
    raw   = "".join(parts)
    lines = [ln.strip() for ln in raw.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def split_race_field(text):
    """
    Split a potentially multi-valued Distance or Time string into a list of
    individual values.  Handles all three separator styles found in the logs:

      newlines  (from <br>):  "5:37.31\\n2:35 split"     → ["5:37.31", "2:35 split"]
      slash:                  "1500/800", "5:20/2:40"     → ["1500","800"] / ["5:20","2:40"]
      comma-space:            "3k steeple, 800"           → ["3k steeple", "800"]

    Also strips trailing slashes left when slash+br are combined:
      "11:49.20/\\n19:24.61"  → ["11:49.20", "19:24.61"]
    """
    if not text:
        return []

    # Split on newlines first (produced by <br>)
    lines = [ln.rstrip("/").strip() for ln in text.split("\n") if ln.strip().rstrip("/")]

    if len(lines) > 1:
        return lines

    # Single line — try slash then comma-space
    line = lines[0] if lines else text.strip()
    for sep in ("/", ", "):
        parts = [p.strip() for p in line.split(sep) if p.strip()]
        if len(parts) > 1:
            return parts

    return [line] if line else []


def clean_time_text(text):
    """
    Strip trailing notes from a race time string, keeping only the numeric
    time portion.  Examples:
      '2:35 split'      → '2:35'
      '5:08.86-PR'      → '5:08.86'
      '2:33.97 - PR'    → '2:33.97'
      '5:57?'           → '5:57'
      '12:02.03 (PR)'   → '12:02.03'
      '2:38.x'          → '2:38.x'   (keep .x — denotes approximate hundredths)
    """
    if not text:
        return text
    text = text.strip().lstrip("(")   # handle "(5:22.38)" style
    m = re.match(r"^(\d+:\d+(?:[.:]\d+|\.x)?)", text)
    return m.group(1) if m else text


def clean_value(text):
    """Return None for placeholder/empty values, otherwise the stripped text."""
    text = re.sub(r'\s+', ' ', text).strip()
    return None if text in PLACEHOLDERS else (text or None)


def parse_minutes(text):
    """
    Convert a minutes/duration string to decimal minutes.
      '45'          → 45.0
      '45:54'       → 45.9   (MM:SS → decimal minutes)
      '23:30 wu/cd' → 23.5   (leading MM:SS, ignores trailing note)
    Returns None if the string can't be parsed.
    """
    if not text:
        return None
    text = text.strip()
    try:
        return float(text)
    except ValueError:
        pass
    m = re.match(r'^(\d+):(\d+):(\d+)', text)
    if m:
        h, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return round(h * 60 + mm + ss / 60, 2)
    m = re.match(r'^(\d+):(\d+)', text)
    if m:
        return round(int(m.group(1)) + int(m.group(2)) / 60, 2)
    return None


def parse_miles(text):
    """
    Convert a miles cell to a float, handling the messy historical formats:
      '8.5'        → 8.5    (plain numeric)
      '8+4'        → 12.0   (main + second session)
      '5+3AM'      → 8.0    (additive; trailing 'AM' is a descriptor)
      '4.5+.5'     → 5.0    (decimal-only second term)
      '5+'         → 5.0    (trailing '+' meaning "at least"; take the leading number)
      '~8'         → 8.0    (approximate)
      '<4.5'       → 4.5    (less-than estimate)
      '&lt;4.5'    → 4.5    (HTML-entity form of '<4.5')
      '-' or ''    → None   (no running miles tracked, e.g. cross-training)
    """
    if not text:
        return None
    t = text.strip().replace("&lt;", "<")
    if not t or t == "-":
        return None
    # Pull out every decimal number ('4.5', '.5', '8') and sum them. This
    # handles plain numbers, additive expressions, trailing '+', leading '~'
    # or '<', and ignores AM/PM-style descriptors after the numbers.
    nums = re.findall(r'\d+\.\d+|\.\d+|\d+', t)
    if not nums:
        return None
    try:
        return round(sum(float(n) for n in nums), 4)
    except ValueError:
        return None


def parse_date_header(header_text):
    """
    Parse 'Friday, November 14' or 'Saturday, Nov 15- Race Name, Location'.
    Returns (day_name, month_int, day_int, race_suffix_or_None), or None if
    the text doesn't look like a workout date header.
    """
    header_text = re.sub(r'\s+', ' ', header_text).strip()

    if not any(header_text.startswith(d) for d in DAYS):
        return None

    day_name = next(d for d in DAYS if header_text.startswith(d))

    m = re.match(
        r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
        r'(January|February|March|April|May|June|July|August|September|'
        r'October|November|December)\s+(\d+)'
        r'(?:st|nd|rd|th)?'                # ordinal suffix on the day number
        r'\s*[-–,]?\s*(.*)',
        header_text,
        re.IGNORECASE,
    )
    if not m:
        return None

    month_name = m.group(1).capitalize()
    # Handle any abbreviated months in the source (safety net)
    if month_name not in MONTHS:
        month_name = next((k for k in MONTHS if k.startswith(month_name)), None)
        if month_name is None:
            return None

    day_int = int(m.group(2))
    suffix  = m.group(3).strip() or None
    # Source occasionally uses "PM"/"AM" for double-day entries — strip when present
    if suffix and re.match(r'^(AM|PM)\b', suffix, re.IGNORECASE):
        suffix = re.sub(r'^(AM|PM)\b\s*[-–,]?\s*', '', suffix, flags=re.IGNORECASE).strip() or None

    return (day_name, MONTHS[month_name], day_int, suffix)


def extract_data(rows):
    """
    Walk <tr> rows (after the date header and the yellow spacer), collecting
    label→value pairs.

    The first data row has inline pairs:
        Workout: | run | Minutes: | 45:54 | Miles: | 5.6
    Subsequent rows span the full width:
        Comments: | long text (colspan=5)
        Extras:   | extra info (colspan=5)
    """
    data = {}
    for row in rows:
        tds = row.find_all("td")
        if not tds:
            continue
        i = 0
        while i < len(tds):
            raw = cell_text(tds[i])
            if raw.endswith(":"):
                label = raw[:-1].strip().lower()
                if i + 1 < len(tds):
                    if label in ("distance", "time"):
                        # Preserve newlines (from <br>) so split_race_field can
                        # use them as separators.  Skip clean_value here because
                        # it collapses \n → space, destroying the structure.
                        raw_val = cell_text_with_br(tds[i + 1])
                        value   = raw_val if raw_val.strip() not in PLACEHOLDERS else None
                    else:
                        value = clean_value(cell_text(tds[i + 1]))
                    data[label] = value
                    i += 2
                else:
                    i += 1
            else:
                i += 1
    return data


# ─── Per-file parser ──────────────────────────────────────────────────────────

def parse_file(filepath, season, file_year_str):
    file_year_int = int(file_year_str)
    entries = []

    with open(filepath, encoding="iso-8859-1", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    # All workout tables are <table border=0 width=600>.
    # lxml may wrap rows in a <tbody>, so we look for rows via tbody when present.
    workout_tables = [
        t for t in soup.find_all("table")
        if str(t.get("border", "")) == "0" and str(t.get("width", "")) == "600"
    ]

    for table in workout_tables:
        # lxml inserts <tbody>; get rows from there if present
        tbody = table.find("tbody")
        rows  = (tbody or table).find_all("tr", recursive=False)
        if not rows:
            continue

        # Row 0: date header
        parsed = parse_date_header(cell_text(rows[0]))
        if parsed is None:
            continue  # e.g. "Season Recap" table

        day_name, month_int, day_int, race_suffix = parsed

        year = resolve_year(season, file_year_int, month_int)
        try:
            entry_date = date(year, month_int, day_int)
        except ValueError:
            entry_date = None

        # Rows[1] is the yellow spacer (bgcolor f3f3f3 / FFFFCC); skip it.
        # Collect only rows that have actual label/value content.
        data_rows = [
            r for r in rows[2:]
            if r.find_all("td") and clean_value(cell_text(r)) is not None
        ]
        data = extract_data(data_rows)

        # Detect race entries by presence of Distance: or Time: labels
        is_race = "distance" in data or "time" in data

        # ── Shared fields (same for every sub-entry in a multi-event day) ──
        miles_raw = data.get("miles") or data.get("total miles")
        miles_num = parse_miles(miles_raw)

        race_name  = race_suffix if is_race and race_suffix else None
        shared = dict(
            date         = entry_date.isoformat() if entry_date else None,
            year         = year,
            month        = month_int,
            day          = day_int,
            day_of_week  = day_name,
            week_of_year = entry_date.isocalendar()[1] if entry_date else None,
            season       = season,
            miles        = miles_num,
            comments     = data.get("comments"),
            extras       = data.get("extras"),
            source_file  = os.path.basename(filepath),
        )

        if is_race:
            # ── Race entry: may contain multiple events ───────────────────
            # Split Distance and Time fields on slash / comma / <br> separators.
            distances = split_race_field(data.get("distance") or "")
            times     = split_race_field(data.get("time")     or "")

            # Pad the shorter list so zip covers every event
            n = max(len(distances), len(times), 1)
            distances += [None] * (n - len(distances))
            times     += [None] * (n - len(times))

            for race_dist, race_time_raw in zip(distances, times):
                race_time_clean = clean_time_text(race_time_raw)

                # Relay legs (4x800m, 4x1600m, etc.): strip the "4x" prefix
                # and mark the time with "*" to indicate it's a split, not a
                # standalone race performance.
                if race_dist and re.match(r'^4x', race_dist.strip(), re.IGNORECASE):
                    race_dist = re.sub(r'^4x', '', race_dist.strip(), flags=re.IGNORECASE)
                    if race_time_clean:
                        race_time_clean += "*"

                entries.append({
                    **shared,
                    "workout_type":      None,
                    "minutes":           None,
                    "minutes_raw":       None,
                    "pace_min_per_mile": None,
                    "is_race":           1,
                    "race_name":         race_name,
                    "race_distance":     race_dist,
                    "race_time":         race_time_clean,
                })

        else:
            # ── Regular workout entry ─────────────────────────────────────
            workout_type = data.get("workout")
            if workout_type:
                workout_type = workout_type.lower().strip()
                workout_type = {"aqua jog": "aquajog"}.get(workout_type, workout_type)

            minutes_raw = data.get("minutes")
            minutes_num = parse_minutes(minutes_raw) if minutes_raw else None

            pace = None
            if minutes_num and miles_num and miles_num > 0:
                pace = round(minutes_num / miles_num, 4)

            entries.append({
                **shared,
                "workout_type":      workout_type,
                "minutes":           minutes_num,
                "minutes_raw":       minutes_raw,
                "pace_min_per_mile": pace,
                "is_race":           0,
                "race_name":         None,
                "race_distance":     None,
                "race_time":         None,
            })

    return entries


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    all_entries = []
    missing     = []

    for season, year_str in FILES:
        filename = f"{season}{year_str}log.html"
        filepath = os.path.join(SOURCE_DIR, filename)

        if not os.path.exists(filepath):
            missing.append(filename)
            continue

        entries = parse_file(filepath, season, year_str)
        all_entries.extend(entries)
        print(f"  {filename}: {len(entries)} entries")

    if missing:
        print(f"\nWarning: missing files: {missing}")

    # Sort chronologically
    all_entries.sort(key=lambda e: e["date"] or "")

    out_path = os.path.join(BASE_DIR, "running_log.csv")  # Running Log/running_log.csv
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        # utf-8-sig writes a BOM so Excel auto-detects UTF-8
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_entries)

    print(f"\nParsed {len(all_entries)} entries from "
          f"{len(FILES) - len(missing)} files -> {out_path}")


if __name__ == "__main__":
    main()
