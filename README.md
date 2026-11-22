# Out of Focus Daily

A daily art puzzle: name the masterpiece before it comes into focus.

Static site: `index.html`, `og.png` (link preview) and `images/`. No build step — Netlify publishes the repository root.

## Today's five

Each painting has an `added` date (YYYY-MM-DD). It joins the daily rotation two days after that date, so
adding paintings never changes a puzzle that people may already be playing. When adding paintings, set
`added` to the day they're added. Each day's five skips anything used in the previous 30 days.
