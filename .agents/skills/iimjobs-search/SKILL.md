---
name: iimjobs-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search IIM Jobs for senior, management,
  or MBA-level job listings in India — even without mentioning iimjobs.com explicitly.
  Invoke for: iimjobs, iimjobs.com, management jobs india, MBA jobs india, senior
  jobs india, leadership jobs india, CXO jobs india, VP jobs india, director jobs
  india, strategy jobs india, consulting jobs india, finance jobs india, operations
  jobs india, general management jobs india, business development jobs india,
  product director india, head of product india, senior manager india, high salary
  jobs india, experienced professional jobs india, B-school jobs india.
context: fork
allowed-tools: Bash(python3 skills/iimjobs-search/cli/cli.py *)
---

# IIM Jobs Search Skill

Search job listings from IIM Jobs (iimjobs.com) — India's premium portal for management,
MBA, and senior professional roles. Covers CXO, VP, Director, and Manager-level positions
across sectors like consulting, BFSI, tech, FMCG, and healthcare.

## When to use this skill

Invoke this skill when the user wants to:

- Find senior or management-level jobs in India (5+ years experience)
- Search for MBA or B-school targeted roles
- Find CXO, VP, Director, or Head-level positions
- Filter by experience bracket, sector, or location
- Get full job description and application details

## Setup

Install dependencies once:

```bash
pip install -r skills/iimjobs-search/cli/requirements.txt
```

## Commands

### Search job listings

```bash
python3 skills/iimjobs-search/cli/cli.py search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keyword search (role title, function, sector). **Required.**
- `--location <city>` / `-l <city>` — city name (e.g. `Bangalore`, `Mumbai`, `Delhi`)
- `--experience <years>` / `-e <years>` — minimum experience in years (e.g. `5`, `10`)
- `--limit <n>` — cap total results shown
- `--format json|table|plain`

### Fetch full job detail

```bash
python3 skills/iimjobs-search/cli/cli.py detail <url> [--format json|plain]
```

Pass the full IIM Jobs URL from search results.

---

## Usage examples

### Product management roles in Bangalore

```bash
python3 skills/iimjobs-search/cli/cli.py search \
  --query "product manager" \
  --location Bangalore \
  --format table
```

### Senior finance jobs (10+ years)

```bash
python3 skills/iimjobs-search/cli/cli.py search \
  --query "finance" \
  --location Mumbai \
  --experience 10 \
  --format table
```

### Strategy consulting roles

```bash
python3 skills/iimjobs-search/cli/cli.py search \
  --query "strategy consulting" \
  --format table
```

### Full details for a job

```bash
python3 skills/iimjobs-search/cli/cli.py detail \
  "https://www.iimjobs.com/j/..." \
  --format plain
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

- IIM Jobs focuses on mid-to-senior roles (typically 3–20+ years experience).
- Results are India-wide unless a location filter is provided.
- Some postings are confidential (company name hidden) — shown as "Confidential".
