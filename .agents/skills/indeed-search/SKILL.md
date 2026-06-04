---
name: indeed-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search Indeed India for jobs, find
  job listings on indeed.co.in or indeed.com in India, or look up specific job
  postings on Indeed — even without mentioning Indeed explicitly. Invoke for:
  indeed india, indeed jobs india, jobs on indeed india, software jobs indeed,
  IT jobs indeed india, fresher jobs indeed, indeed job search india, jobs in
  bangalore indeed, jobs in mumbai indeed, jobs in delhi ncr indeed, remote jobs
  india indeed, walk-in jobs india, urgent hiring india, jobs with salary india.
context: fork
allowed-tools: Bash(python3 skills/indeed-search/cli/cli.py *)
---

# Indeed Search Skill

Search live job listings from Indeed India (in.indeed.com). No authentication needed.
Indeed India aggregates jobs from thousands of company sites and recruiters.

## When to use this skill

Invoke this skill when the user wants to:

- Search for job openings across all sectors in India
- Find jobs by keyword, company, or salary range
- Filter by location, job type, or recency
- Get the full description of a specific Indeed job posting

## Setup

Install dependencies once:

```bash
pip install -r skills/indeed-search/cli/requirements.txt
```

## Commands

### Search job listings

```bash
python3 skills/indeed-search/cli/cli.py search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keyword search (job title, skill, company). **Required.**
- `--location <place>` / `-l <place>` — city or region (e.g. `Bangalore`, `Mumbai`, `Delhi NCR`, `Remote`)
- `--job-type <type>` — `fulltime`, `parttime`, `contract`, `internship`, `temporary`
- `--recency <days>` — `1`, `3`, `7`, `14` (days since posting)
- `--start <n>` — pagination offset (multiples of 10)
- `--limit <n>` — cap total results shown
- `--format json|table|plain`

### Fetch full job detail

```bash
python3 skills/indeed-search/cli/cli.py detail <job_key> [--format json|plain]
```

`job_key` is the `jk` hash from search results. Returns the full job description and apply link.

---

## Usage examples

### Python developer jobs in Bangalore

```bash
python3 skills/indeed-search/cli/cli.py search \
  --query "python developer" \
  --location Bangalore \
  --format table
```

### Fresher software jobs posted in the last 3 days

```bash
python3 skills/indeed-search/cli/cli.py search \
  --query "software engineer fresher" \
  --location India \
  --recency 3 \
  --format table
```

### Remote data analyst roles

```bash
python3 skills/indeed-search/cli/cli.py search \
  --query "data analyst" \
  --location Remote \
  --job-type fulltime \
  --format table
```

### Full details for a specific job

```bash
python3 skills/indeed-search/cli/cli.py detail abc1234xyz --format plain
```

---

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, data processing |
| `table` | Quick human-readable overview and scanning |
| `plain` | Reading a single job's full detail |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- Uses Indeed India (in.indeed.com) — results are India-specific.
- Indeed has anti-bot measures; realistic headers are used automatically.
- Pagination: use `--start 10` for page 2, `--start 20` for page 3, etc.
