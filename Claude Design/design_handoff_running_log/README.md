# Handoff: College Running Log Dashboard

## Overview
A personal athletic data dashboard for visualizing 4 years of college running (Fall 2003 – Spring 2007). The dashboard displays training history through interactive charts: a color-coded heatmap calendar, weekly mileage bars, cumulative mileage line chart, workout mix donut, race results timeline, and pattern analysis charts. It also includes a searchable training notes log.

The title is **"College Running Log — Strava Before Strava"** — this predates Strava, so the app is a personal retroactive log.

---

## About the Design Files
The files in this bundle are **high-fidelity design references created as HTML prototypes**. They show the intended look, feel, and behavior of the dashboard. Your task is to **recreate these designs in your existing codebase** using its established framework, component library, and patterns — not to ship the HTML files directly. If no framework is established yet, React + TypeScript is recommended given the data-heavy, component-rich nature of this UI.

---

## Fidelity
**High-fidelity.** The prototype uses final colors, typography, spacing, layout, and interactions. Recreate pixel-closely using your codebase's patterns. All exact token values are listed below.

---

## Design Tokens

### Colors (Dark Mode — default)
```
--bg-base:        #0d1117   /* Page background */
--bg-surface:     #161b22   /* Card surfaces */
--bg-elevated:    #1c2230   /* Elevated elements, note rows */
--bg-glass:       rgba(22, 27, 34, 0.7)  /* Frosted glass cards */
--border:         rgba(48, 54, 61, 0.8)
--border-subtle:  rgba(48, 54, 61, 0.4)

--text-primary:   #e6edf3
--text-secondary: #8b949e
--text-tertiary:  #484f58

--accent:         #58a6ff   /* Primary accent — user-tweakable */
--accent-glow:    rgba(88, 166, 255, 0.15)
--accent-dim:     rgba(88, 166, 255, 0.08)
```

### Colors (Light Mode — prefers-color-scheme: light)
```
--bg-base:        #f6f8fa
--bg-surface:     #ffffff
--bg-elevated:    #f0f2f5
--bg-glass:       rgba(255, 255, 255, 0.8)
--border:         rgba(208, 215, 222, 0.9)
--border-subtle:  rgba(208, 215, 222, 0.5)
--text-primary:   #1a2332
--text-secondary: #57606a
--text-tertiary:  #afb8c1
--accent:         #0969da
```

### Workout Type Colors
These are used in the heatmap, donut chart, race cards, and badges. User can tweak them.
```
Easy run:   #2dd4bf  (teal)
Tempo run:  #f59e0b  (amber)
Long run:   #a78bfa  (violet)
Race:       #f87171  (coral/red)
Workout:    #60a5fa  (blue)
```

### Typography
```
Font family (body):    'Geist', system-ui, sans-serif
Font family (numbers): 'Geist Mono', 'Fira Code', monospace
```

Load from Google Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

### Type Scale
```
Page section label:  10px, mono, 600, letter-spacing 0.12em, uppercase, text-tertiary
Page title (h1):     22px, sans, 600, letter-spacing -0.02em, text-primary
Subtitle/date:       12px, sans, 400, text-secondary
Card title:          12px, sans, 600, letter-spacing 0.08em, uppercase, text-secondary
Stat number (large): 26px, mono, 600, letter-spacing -0.03em, text-primary
Big stat/PR:         30–32px, mono, 700, letter-spacing -0.04em, text-primary
Body / note text:    13px, sans, 400, text-secondary
Small label:         11px, sans, 400, text-secondary; uppercase + letter-spacing 0.04em for labels
Tiny / legend:       9–10px, mono, text-tertiary
```

### Spacing & Radius
```
Card border-radius:       16px
Stat card border-radius:  12px
Button/pill radius:        8px
Small badge radius:        4–6px
Card padding:             24px
Stat card padding:        18px 20px
Gap between cards:        16–20px
Gap between stat cards:   10px
Main content padding:     32px 28px 80px
Max content width:        900px
```

### Shadows & Borders
- Cards: `border: 1px solid var(--border-subtle)` — no box-shadow by default
- Hover state: `box-shadow: 0 0 0 1px var(--accent-dim)`
- Backdrop filter: `blur(16px)` on cards, `blur(20px)` on sidebar

### Motion
```
Easing:      cubic-bezier(0.16, 1, 0.3, 1)
Fast:        120ms
Medium:      240ms
Entrance:    fadeUp — opacity 0→1, translateY 12px→0, 240ms
```

### Background Gradient (decorative)
```css
background:
  radial-gradient(ellipse 80% 50% at 20% -10%, rgba(88,166,255,0.06) 0%, transparent 60%),
  radial-gradient(ellipse 60% 40% at 80% 110%, rgba(167,139,250,0.04) 0%, transparent 60%);
```

---

## Layout

### Shell
- **Full viewport height**, `flex-direction: column`, `overflow: hidden` on outer wrapper
- **Sticky top nav bar** + **main content** (flex: 1, overflow-y: auto)
- Top nav has `backdrop-filter: blur(20px)`, `border-bottom: 1px solid var(--border-subtle)`

### Top nav bar (two rows)
**Row 1 — top strip** (height 48px):
- Left: **Wordmark** — "College Running Log" (14px, 700, letter-spacing -0.02em) + "2003–2007" (mono, 10px, text-tertiary) + "· 6,120 mi" (mono, 10px, text-secondary), all inline with `gap: 10px`
- Right: **"Strava API Dashboard"** button — Strava orange `#fc4c02`, 11px 600, Strava chevron SVG icon (12×12), `background: rgba(252,76,2,0.08)`, `border: 1px solid rgba(252,76,2,0.25)`, 7px radius, hover darkens both. Links to `https://www.strava.com/dashboard`.
- Max-width 1100px, centered, padding `0 32px`

**Row 2 — tab nav** (no fixed height, padding 10px top/11px bottom):
- 6 tab buttons, each with: icon glyph + label, `font-size: 13px`
- Active: `color: var(--accent)`, `border-bottom: 2px solid var(--accent)`, weight 600
- Inactive: `color: var(--text-secondary)`, `border-bottom: 2px solid transparent`
- Hover: color → text-primary
- Margin-bottom: -1px to overlap the header's bottom border (clean underline flush)
- Max-width 1100px, centered, padding `0 32px`

### Main content
- Max-width **1100px**, centered, padding `32px 32px 80px`
- **Page header** — eyebrow (mono 10px uppercase, text-tertiary) + `<h1>` section name (26px, 700, letter-spacing -0.03em)
- Content area below holds the active section

---

## Sections / Views

### 1. Overview
**Components:**
- **Stat Cards row** — 6 cards in a flex row (wraps on mobile). Each card: frosted glass bg, 12px radius, 18px/20px padding. Large mono number (26px, 600), small label below (11px, uppercase).
  - Stats: Total Miles (6,120), Avg Mi/Week (37), Peak Week (63), Races (100), Longest Streak (47d), Active Days (82%)
- **Training Notes Search** — see component spec below
- **Training Calendar (Heatmap)** — see component spec below
- **Cumulative Mileage chart** — see component spec below

### 2. Training Volume
**Components:**
- **Weekly Mileage bar chart** — SVG bar chart, 200 weeks of data, bars colored with accent color (not workout type). Below chart: 3 inline stats (Avg Week, Peak Week, Total Weeks).
- **4 seasonal sparkline cards** — 2×2 grid. Each: large mono number (32px, 700) for avg mi/wk, small sparkline chart below using accent color.

### 3. Workout Mix
**Components:**
- **2-column grid:**
  - Left: **Donut chart** (140px, workout type colors) + legend list with color swatches and percentages. Segments: Easy 62%, Long 14%, Tempo 12%, Workout 8%, Race 4%.
  - Right: **Easy Run Pace Over Time** — area line chart, accent color gradient fill, with axis labels (8:30/mi → 7:00/mi). Caption: "Avg easy pace improved by ~1:30/mi over 4 years."
- **3-column stat cards** — Easy Runs (789), Tempo Runs (153), Long Runs (178). Each shows count + color swatch for its type.

### 4. Performance
**Components:**
- **2×2 PR cards** — each shows: label (uppercase 11px), large mono time (30px, 700), sub-label (season), and a 4px-wide colored vertical bar accent on the right.
  - 5K PR: 14:44 (Winter 2007) — race color
  - 10K PR: 30:44 (Spring 2007) — tempo color
  - 8K XC PR: 25:11 (Fall 2006) — long color
  - Mile PR: 4:28 (Winter 2006) — easy color
- **5K Progression line chart** — SVG polyline with dot markers, accent color. ~10 data points showing improvement over 4 years.

### 5. Races
**Components:**
- **Tab switcher** — 3 tabs: Cross Country / Indoor Track / Outdoor Track. Pill-style: active tab has glass bg + shadow; tabs sit inside a pill container (`background: var(--bg-elevated)`, 10px radius).
- **Race cards list** — vertical stack of race rows. Each row: type badge (colored), season + distance (secondary text), time (mono 16px 600), place (secondary), optional **PR badge** (coral bg/border, 9px, "PR").
- **Summary bar** — below list, accent-dim bg, showing PR count.

### 6. Patterns
**Components:**
- **2-column bar charts:**
  - Avg Miles by Day of Week — 7 bars (Mo–Su), accent color, opacity scales with value
  - Avg Weekly Miles by Month — 12 bars (J–D), accent color, opacity scales with value
- **Streak Analysis card** — 3-column stat grid: Longest Streak (47 days), Current Streak (12 days), Total Streaks 7d+ (28 streaks).

---

## Component Specs

### GlassCard
Reusable container for all chart/content sections.
```
background: rgba(22, 27, 34, 0.7)
backdrop-filter: blur(16px)
border: 1px solid rgba(48, 54, 61, 0.4)
border-radius: 16px
padding: 24px
animation: fadeUp on mount
```
Optional `title` prop renders a 12px uppercase 600-weight label at top with 20px margin-bottom.

### StatCard
```
background: var(--bg-glass)
border: 1px solid var(--border-subtle)
border-radius: 12px
padding: 18px 20px
flex: 1, min-width: 90px
hover: border-color → var(--border), box-shadow: 0 0 0 1px var(--accent-dim)
```

### Training Notes Search
- Search input: `background: var(--bg-elevated)`, 8px radius, focus border = accent color, search icon (⌕) left-padded, × clear button when filled
- Filter pills: one per type (All, Easy, Tempo, Long, Workout, Race). Active pill uses that type's bg/border/text color. Inactive: transparent bg, text-secondary.
- Results count: mono 11px, text-tertiary. Matching query shown in accent color.
- Note rows: `background: var(--bg-elevated)`, 8px radius, click to expand. Collapsed: single-line truncated. Row contains: type badge, date (mono 11px), miles (mono 11px), note text (13px), expand chevron (▾).
- **Scroll area height: 218px** (shows ~3 entries before scrolling)
- Keyword highlighting: `background: rgba(88,166,255,0.35)`, 2px border-radius

### Training Calendar (Heatmap)
- One row per year (2003–2007), each showing a grid of 7 rows × N weeks
- Each cell: 11×11px, 2px border-radius, 2px gap
- Day-of-week labels (M T W T F S S) on left; month labels above (every ~4 weeks)
- **Two color modes** — toggle control sits below the card title:
  - **"Workout Type"**: cell color from workout type palette, opacity = `0.3 + (miles/14) * 0.7`
  - **"Miles Intensity"**: all cells use accent color, opacity = `0.15 + (miles/14) * 0.85`
- Rest days: `var(--border-subtle)`, opacity 0.3
- Hover: scale(1.4) transition
- Legend updates per mode: type mode shows color swatches; intensity mode shows a gradient bar (0 mi → 14+ mi)

### Cumulative Mileage Chart
- SVG polyline on gradient fill (accent → transparent)
- Year markers: dashed vertical lines with year label
- Ends with large mono "6,120 total miles" right-aligned below chart

### Bar Chart (Weekly Mileage)
- SVG bars, `preserveAspectRatio="none"`, viewBox 600×120
- Bar width: `max(2, (600/numWeeks) - 1)`, 1px border-radius
- Color: accent (for volume/patterns charts), workout type color (for type-specific charts)
- Opacity: `0.6 + (miles/maxMiles) * 0.4`

### Donut Chart
- Pure SVG path arcs (no library)
- Inner radius ~22% of size, outer ~38%
- Segment opacity: 0.85

### Sparkline
- SVG polyline + filled area (color at 12% opacity)
- strokeWidth: 2, strokeLinejoin: round

### Race Card
```
background: var(--bg-elevated)
border: 1px solid var(--border-subtle)
border-radius: 10px
padding: 14px 18px
hover: border-color → var(--border)
```
Row: type badge | date + distance | time (mono 16px 600) | place | PR badge (optional)

### PR Badge
```
background: rgba(248, 113, 113, 0.15)
border: 1px solid rgba(248, 113, 113, 0.3)
color: #f87171
font-size: 9px, weight 700, letter-spacing 0.08em
padding: 2px 7px, border-radius: 4px
```

### Type Badge (in notes + race rows)
Each type has its own bg/border/text triplet:
```
easy:    bg rgba(45,212,191,0.12)  border rgba(45,212,191,0.3)  text #2dd4bf
tempo:   bg rgba(245,158,11,0.12)  border rgba(245,158,11,0.3)  text #f59e0b
long:    bg rgba(167,139,250,0.12) border rgba(167,139,250,0.3) text #a78bfa
race:    bg rgba(248,113,113,0.12) border rgba(248,113,113,0.3) text #f87171
workout: bg rgba(96,165,250,0.12)  border rgba(96,165,250,0.3)  text #60a5fa
```

---

## Interactions & Behavior

| Interaction | Behavior |
|---|---|
| Sidebar nav click | Switches active section; active item gets accent color + dim bg |
| Sidebar toggle (←/→) | Animates width 220px ↔ 60px over 240ms; icon-only mode shows only icon glyphs |
| Stat card hover | Border lightens, accent glow ring appears |
| Heatmap cell hover | Cell scales up 1.4×; tooltip shows "N mi — type" |
| Notes search input | Live filters entries; clears with × button |
| Notes type filter | Pill toggles; filters list to that workout type |
| Note row click | Expands inline to show full note text; ▾ rotates 180° |
| Heatmap mode toggle | Instantly re-colors all 1,000+ cells via state; legend swaps |
| Race tab click | Switches race category; list re-renders |
| Strava button hover | Background and border darken toward orange |
| All cards mount | fadeUp animation (opacity + translateY) |

---

## State Management

```typescript
// App level
activeSection: 'overview' | 'volume' | 'workout-mix' | 'performance' | 'races' | 'patterns'
sidebarOpen: boolean

// Overview section
heatmapMode: 'type' | 'gradient'

// Training Notes Search
query: string          // live search text
filterType: string     // 'all' | 'easy' | 'tempo' | 'long' | 'workout' | 'race'
expanded: number|null  // index of expanded note row

// Races section
activeTab: 'crossCountry' | 'indoorTrack' | 'outdoorTrack'

// Tweaks (user preferences — persist to localStorage)
accentColor: string    // hex, default #58a6ff
easyColor: string      // hex, default #2dd4bf
tempoColor: string     // hex, default #f59e0b
longColor: string      // hex, default #a78bfa
raceColor: string      // hex, default #f87171
```

---

## Data Shape

The dashboard expects data in roughly this shape. Hook up your real data source (CSV, DB, Strava API) to these structures:

```typescript
interface Run {
  date: string;        // ISO date "2005-04-22"
  miles: number;
  type: 'easy' | 'tempo' | 'long' | 'workout' | 'race';
  note?: string;
}

interface Race {
  year: number;
  season: string;      // "Fall 2006"
  race: string;        // "Conference XC"
  distance: string;    // "8K"
  time: string;        // "25:11"
  pr: boolean;
  place: string;       // "12th"
}

interface DashboardData {
  runs: Run[];
  races: {
    crossCountry: Race[];
    indoorTrack: Race[];
    outdoorTrack: Race[];
  };
  stats: {
    totalMiles: number;
    avgMilesPerWeek: number;
    peakWeekMiles: number;
    totalRaces: number;
    longestStreak: number;         // days
    activeDayPercentage: number;   // 0–100
  };
}
```

The heatmap is derived by bucketing `runs` into year → week → day. Weekly volume is derived by grouping runs by ISO week. Cumulative mileage is a running sum over `runs` sorted by date.

---

## Assets

- **Strava chevron SVG** (inline in prototype):
  ```svg
  <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.599h4.172L10.463 0l-7 13.828h4.169"/>
  ```
- **No other external assets** — all charts are pure SVG/CSS, no icon library, no chart library.

---

## Files in This Package

| File | Description |
|---|---|
| `Running Log Dashboard.html` | Full hi-fi prototype — single HTML file with all components and sample data. Open in any browser to see the design. |
| `README.md` | This document |

---

## Implementation Notes

1. **No charting library used** — all charts are hand-rolled SVG. In a production codebase you may want to replace with Recharts, Nivo, or D3 while matching the visual output.
2. **Accent color is runtime-tweakable** — store in user preferences and apply as a CSS custom property (`--accent`) on `:root`. All charts reference it dynamically.
3. **Color scheme follows `prefers-color-scheme`** — no manual toggle; just CSS media query. The prototype implements both light and dark palettes.
4. **Sample data is seeded randomly** — replace all `generateHeatmap()`, `generateWeeklyVolume()`, etc. functions with real data fetches.
5. **The sidebar collapse state** could be persisted to `localStorage` for a better returning-user experience.
6. **Training Notes search** is client-side filtered — for large datasets (10k+ entries), move to a backend search endpoint.
