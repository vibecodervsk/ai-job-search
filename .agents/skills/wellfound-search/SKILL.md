---
name: wellfound-search
version: 1.0.0
description: >
  Use this skill whenever the user wants to search Wellfound (formerly AngelList
  Talent) for startup jobs in India, find tech startup job listings, or look for
  early-stage company roles — even without mentioning Wellfound explicitly.
  Invoke for: wellfound jobs india, angellist jobs india, startup jobs india,
  tech startup jobs india, early stage startup jobs, seed stage jobs india,
  series a jobs india, equity jobs india, startup engineer india, founding engineer
  india, wellfound india, startup product manager india, startup data scientist india,
  startup jobs bangalore, startup jobs mumbai, startup jobs delhi, high growth
  startup jobs india, funded startup jobs india.
context: fork
allowed-tools: Bash(python3 skills/wellfound-search/cli/cli.py *)
---

# Wellfound Search Skill

Search startup and early-stage company job listings from Wellfound (formerly AngelList Talent).
Covers thousands of funded startups across India — ideal for candidates seeking equity,
fast growth, and early-stage roles.

## When to use this skill

Invoke this skill when the user wants to:

- Find jobs at Indian startups (seed, Series A/B/C, growth stage)
- Search for roles at specific funded companies
- Filter by role type, location, or remote options
- Get the full description of a Wellfound job posting

## Setup

Install dependencies once:

```bash
pip install -r skills/wellfound-search/cli/requirements.txt
```

## Commands

### Search job listings

```bash
python3 skills/wellfound-search/cli/cli.py search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — role or skill keyword (e.g. `"software engineer"`, `"product manager"`)
- `--location <place>` / `-l <place>` — city or `remote` (default: `India`)
- `--limit <n>` — cap total results shown
- `--format json|table|plain`

### Fetch full job detail

```bash
python3 skills/wellfound-search/cli/cli.py detail <url> [--format json|plain]
```

Pass the full Wellfound job URL from search results.

---

## Usage examples

### Software engineer jobs at Indian startups

```bash
python3 skills/wellfound-search/cli/cli.py search \
  --query "software engineer" \
  --location India \
  --format table
```

### Remote product roles

```bash
python3 skills/wellfound-search/cli/cli.py search \
  --query "product manager" \
  --location remote \
  --format table
```

### Full details for a job

```bash
python3 skills/wellfound-search/cli/cli.py detail \
  "https://wellfound.com/jobs/..." \
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

- Wellfound uses server-side rendering (Next.js). This skill parses the embedded page data.
- Some roles may require a Wellfound account to apply — links are provided for direct access.
- If results seem sparse, try broader query terms or omit `--location`.
