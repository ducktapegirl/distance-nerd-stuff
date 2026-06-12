
## General concerns

1. Don't want dark mode only. Add a toggle for dark/light/use system theme.
2. Title (where College Running Log text) should be much larger. At least with larger text than the Overview title.
3. The grey text in dark mode is hard to see (primarily used on axes labels)
4. Feedback for Claude Design: it showed me light mode even though it exported default dark mode.
5. Don't include hover-highlight behavior on non-clickable sections.
6. Change the Strava button text to say "My Strava Dashboard"
7. Pace representation accuracy. Some entries show 0:08 / mile, 0:09 / mile, or similar for pace. Look at the following entries, determine what the issue is, and then correct it globally:
	1. Saturday, March 4, 2006
	2. Sunday, August 6, 2006
	3. Wednesday, July 14, 2004
	4. Sunday, October 12, 2003

There are also 6 navigation sections. Listing my issues and concerns with each.

### Overview

1. Format the Training Notes items so that the labels, dates, mileage, and comments are each left-justified. (As if they have a table, rather than a continuous string of text.)
2. Switch the default view of the training calendar to Miles intensity (heatmap).
3. Increase the contrast between the lowest miles intensity color and the highest. 
4. Put the color legend for the Training Calendar / Mile Intensity at the top.
5. Start week on Sunday.
6. Add capability: If I click an entry in the Training Notes, highlight the date in the calendar.

### Volume

1. Fix the width of the per/season mileage totals. The total width of all 4 charts should match the width of the primary weekly mileage chart.
2. What are those sparklines plotting?
3. Remove the spacing between bars on the weekly mileage chart (unless there is a week with 0 miles). Make all the bars the same width.
### Workout Mix

1. Fix the width of the charts so that Easy Run Pace Over Time fits on the page. (Put it below all of the workout distribution information.)
2. Add counts for Race and Workouts. Ensure all 5 cards fit on the screen.
### Performance

1. Put the Race Pace Over Time chart before the PR progression chart.
2. Use stars are markers to indicate PRs on the Race Pace Over Time chart.
3. There should be 5 PR progression chart should include the following distances:
	1. 800m
	2. Mile
	3. 3k steeple
	4. 5k track
	5. 5k cross country
4. Double-check the rules I settled on for the pre-rewrite version of the PR progression charts. The current lines look like they connect race-to-race instead of some kind of weighted average.
5. Do NOT separate the PRs by cross country/indoor/outdoor
6. Remove the zoom sliders from these charts.
### Races

1. Add a search feature
2. Make them sort and filterable by time, date, distance, and PR. 
### Patterns

1. The two charts exceed the width of the page.

