---
name: naukri-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search for jobs in India on Naukri.com,
  find Indian job listings, look up specific job postings, or asks about the Indian
  job market — even if they don't mention naukri.com explicitly. Invoke for questions
  about open positions, job vacancies, hiring in India, jobs in Indian cities or
  sectors, or when the user wants to find work in India. Also trigger for phrases
  like "find me a job", "are there any jobs for X in Bangalore", or "what jobs are
  available in Mumbai". Trigger phrases include: naukri, naukri.com, jobs in india,
  indian jobs, jobs in bangalore, jobs in mumbai, jobs in delhi, jobs in hyderabad,
  jobs in pune, jobs in chennai, software jobs india, IT jobs india, data scientist
  jobs india, python jobs india, java jobs india, product manager jobs india,
  fresher jobs india, experienced jobs india, naukri job search, find job india.
context: fork
allowed-tools: Bash(python3 skills/naukri-search/cli/cli.py *)
---

# Naukri Search Skill

Search live job listings from Naukri.com — India's largest job portal. No authentication needed.
Covers millions of job postings across all sectors and experience levels, updated in real time.

## When to use this skill

Invoke this skill when the user wants to:

- Search for job openings in India by keyword, job title, skill, or company
- Find jobs in a specific Indian city (Bangalore, Mumbai, Delhi, Hyderabad, Pune, Chennai, etc.)
- Filter jobs by experience level or recency
- Get the full description of a specific job listing
- Explore the Indian job market for a given profession or skill set

## Setup

Install dependencies once:

```bash
pip install -r skills/naukri-search/cli/requirements.txt
```

## Commands

### Search job listings

```bash
python3 skills/naukri-search/cli/cli.py search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keyword search (job title, skill, technology). **Required** for meaningful results.
- `--location <city>` / `-l <city>` — city name (e.g. `bangalore`, `mumbai`, `delhi`, `hyderabad`)
- `--experience <years>` / `-e <years>` — minimum experience in years (e.g. `2`, `5`)
- `--job-age <days>` — filter by posting age: `1`, `7`, `14`, `30`
- `--page <n>` — page number (1-indexed, 20 results per page)
- `--limit <n>` — cap total results shown
- `--format json|table|plain`

### Fetch full job detail

```bash
python3 skills/naukri-search/cli/cli.py detail <url> [--format json|plain]
```

Pass the full Naukri job URL from search results. Returns the full job description, requirements, and apply link.

---

## How to use effectively

**Always start with `search`.** Pass the job title, skill, or technology as `--query`. Combine with `--location` for city-specific results.

**Use `--job-age 7` or `--job-age 1` for fresh listings.** Without it, results include all postings.

**Natural workflow: `search` → `detail`.**
1. Use `search` to find matching jobs and their URLs.
2. Call `detail <url>` to get the full description and apply link.

**Use `--format table` for quick scanning**, `--format json` for data processing.

---

## Usage examples

### Python developer jobs in Bangalore

```bash
python3 skills/naukri-search/cli/cli.py search \
  --query "python developer" \
  --location bangalore \
  --format table
```

### Data scientist jobs posted in the last 7 days

```bash
python3 skills/naukri-search/cli/cli.py search \
  --query "data scientist" \
  --job-age 7 \
  --format table
```

### Product manager jobs, 5+ years experience

```bash
python3 skills/naukri-search/cli/cli.py search \
  --query "product manager" \
  --location mumbai \
  --experience 5 \
  --format table
```

### Full details for a specific job

```bash
python3 skills/naukri-search/cli/cli.py detail \
  "https://www.naukri.com/job-listings-..." \
  --format plain
```

---

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, data processing |
| `table` | Quick human-readable overview and scanning |
| `plain` | Reading a single job's full details |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.
