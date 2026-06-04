---
name: linkedin-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search LinkedIn for jobs in India,
  find LinkedIn job listings, or look up specific LinkedIn job postings — even if
  they don't mention linkedin.com explicitly. Invoke for: linkedin jobs india,
  jobs on linkedin, software engineer jobs linkedin india, linkedin job search,
  find jobs linkedin, tech jobs india linkedin, startup jobs india, MNC jobs india,
  remote jobs india, jobs in bangalore linkedin, jobs in mumbai linkedin, full time
  jobs india, contract jobs india, entry level jobs india, senior jobs india.
context: fork
allowed-tools: Bash(python3 skills/linkedin-search/cli/cli.py *)
---

# LinkedIn Search Skill

Search live job listings from LinkedIn's public jobs API — no authentication required.
Covers all sectors and experience levels across India, updated in real time.

## When to use this skill

Invoke this skill when the user wants to:

- Search LinkedIn for job openings in India by keyword, title, or company
- Filter by job type (full-time, part-time, contract, internship)
- Filter by experience level (internship, entry, associate, mid-senior, director)
- Filter by recency (last day, last week, last month)
- Get the full description of a specific LinkedIn job posting

## Setup

Install dependencies once:

```bash
pip install -r skills/linkedin-search/cli/requirements.txt
```

## Commands

### Search job listings

```bash
python3 skills/linkedin-search/cli/cli.py search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keyword search (job title, skill, company). **Required.**
- `--location <place>` / `-l <place>` — location (default: `India`). E.g. `Bangalore`, `Mumbai`, `Remote`
- `--job-type <type>` — `fulltime`, `parttime`, `contract`, `internship`, `temporary`
- `--experience <level>` — `internship`, `entry`, `associate`, `mid-senior`, `director`, `executive`
- `--recency <filter>` — `day` (last 24h), `week` (last 7 days), `month` (last 30 days)
- `--start <n>` — result offset (multiples of 25, for pagination)
- `--limit <n>` — cap total results shown
- `--format json|table|plain`

### Fetch full job detail

```bash
python3 skills/linkedin-search/cli/cli.py detail <job_id> [--format json|plain]
```

`job_id` is the numeric LinkedIn job ID from search results. Returns the full job description and apply link.

---

## How to use effectively

**Natural workflow: `search` → `detail`.**
1. Use `search` to find matching jobs and their `id` values.
2. Call `detail <id>` to get the full description and direct apply link.

**Use `--recency week` for fresh listings.** Without it, all results are returned regardless of age.

**Use `--format table` for quick scanning**, `--format json` for data processing.

---

## Usage examples

### Software engineer jobs in Bangalore

```bash
python3 skills/linkedin-search/cli/cli.py search \
  --query "software engineer" \
  --location Bangalore \
  --format table
```

### Data science jobs posted this week

```bash
python3 skills/linkedin-search/cli/cli.py search \
  --query "data scientist" \
  --location India \
  --recency week \
  --format table
```

### Senior product manager roles (full-time)

```bash
python3 skills/linkedin-search/cli/cli.py search \
  --query "product manager" \
  --location India \
  --job-type fulltime \
  --experience mid-senior \
  --format table
```

### Internships in Hyderabad

```bash
python3 skills/linkedin-search/cli/cli.py search \
  --query "software intern" \
  --location Hyderabad \
  --job-type internship \
  --format table
```

### Full details for a specific job

```bash
python3 skills/linkedin-search/cli/cli.py detail 4052934718 --format plain
```

---

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, data processing, passing IDs to `detail` |
| `table` | Quick human-readable overview and scanning |
| `plain` | Reading a single job's full detail (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- Uses LinkedIn's public guest API — no login or API key required.
- LinkedIn may throttle requests. If you receive errors, wait a moment and retry.
- Pagination: use `--start 25` for page 2, `--start 50` for page 3, etc.
