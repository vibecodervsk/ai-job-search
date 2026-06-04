# Search Queries for Job Scraper

<!-- SETUP: Customize these queries based on your skills, target roles, and location -->

## Search Sites

Primary (Indian job market):
- **naukri.com** — largest Indian job board, all sectors
- **linkedin.com/jobs** — LinkedIn job listings (filter: India / your city)
- **wellfound.com** — startup and funded company roles
- **in.indeed.com** — Indeed India, aggregates from company sites and recruiters
- **iimjobs.com** — senior, management, and MBA-level roles

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies

## Query Categories

Queries are grouped by priority. Each query should be combined with your location terms
(e.g. "Bangalore", "Mumbai", "Delhi NCR", "Hyderabad") where the site supports it.

### Priority 1: [YOUR_PRIMARY_ROLE_TYPE]

These match your strongest and most desired career direction.

```
site:naukri.com "[YOUR_PRIMARY_JOB_TITLE]" [YOUR_CITY]
site:naukri.com "[YOUR_KEY_SKILL]" [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_PRIMARY_JOB_TITLE]" India
site:wellfound.com "[YOUR_PRIMARY_JOB_TITLE]" India
```

### Priority 2: [YOUR_DOMAIN_EXPERTISE]

These match your domain expertise.

```
site:naukri.com [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY]
site:naukri.com [YOUR_DOMAIN_KEYWORD_2] India
site:in.indeed.com [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY]
site:linkedin.com/jobs [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY] India
```

### Priority 3: [YOUR_ADJACENT_ROLE_TYPE]

Adjacent roles you could pivot into.

```
site:naukri.com "[YOUR_ADJACENT_TITLE_1]" [YOUR_KEY_SKILL] [YOUR_CITY]
site:iimjobs.com "[YOUR_ADJACENT_TITLE_2]" [YOUR_CITY]
site:wellfound.com "[YOUR_ADJACENT_TITLE_1]" India
```

### Priority 4: Broader Technical / Consulting

Wider net for general technical roles.

```
site:naukri.com [YOUR_KEY_SKILL] developer [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_KEY_SKILL] developer" India
site:naukri.com "technical consultant" [YOUR_DOMAIN] [YOUR_CITY]
site:iimjobs.com [YOUR_DOMAIN] consultant [YOUR_CITY]
```

## Location Filter

When evaluating results, verify the job location is within reasonable commute distance
from your home city. Define acceptable areas:

- [YOUR_CITY] and surrounding areas (primary)
- [ACCEPTABLE_CITY_1] (willing to relocate)
- [ACCEPTABLE_CITY_2] (willing to relocate)
- Remote (anywhere in India)
- [TOO_FAR_AREA] (not willing — skip these)

Common Indian cities to configure: Bangalore, Mumbai, Delhi/NCR, Hyderabad, Pune, Chennai,
Kolkata, Ahmedabad, Gurgaon, Noida.

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that
has not yet passed. If a posting date cannot be determined, include it but flag as
"date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also
generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" → relevant category queries + custom focus-specific queries

## Portal-Specific Tips

- **Naukri**: Best for volume — use `--job-age 7` to filter fresh listings
- **LinkedIn**: Best for MNC and product companies — use `--recency week`
- **Wellfound**: Best for funded startups and equity roles
- **Indeed India**: Good for SME and walk-in roles, use `--recency 3` or `7`
- **IIM Jobs**: Best for senior roles (5+ years); use `--experience 5`
