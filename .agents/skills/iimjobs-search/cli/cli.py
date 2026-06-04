#!/usr/bin/env python3
"""IIM Jobs search CLI — senior and management roles in India."""

import re
import sys
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.iimjobs.com"
SEARCH_URL = f"{BASE_URL}/j/search-jobs.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.iimjobs.com/",
}

# IIM Jobs location IDs (from their filter dropdowns)
LOCATION_IDS = {
    "bangalore": "1",
    "bengaluru": "1",
    "mumbai": "2",
    "delhi": "3",
    "ncr": "3",
    "hyderabad": "4",
    "chennai": "5",
    "pune": "6",
    "kolkata": "7",
    "ahmedabad": "8",
    "gurgaon": "9",
    "noida": "10",
}

MAX_RETRIES = 3


def write_error(message: str, code: str) -> None:
    sys.stderr.write(json.dumps({"error": message, "code": code}) + "\n")


def http_get(url: str, params: dict = None) -> requests.Response:
    delay = 1.5
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == MAX_RETRIES - 1:
                    resp.raise_for_status()
                time.sleep(delay)
                delay = min(delay * 2, 10.0)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
    raise RuntimeError("Request failed after max retries")


def parse_job_listings(soup: BeautifulSoup) -> list:
    jobs = []

    # IIM Jobs listings are in <div class="list-item"> or similar containers
    # Try multiple selector patterns to be robust across site updates
    cards = (
        soup.select("div.list-item")
        or soup.select("div[class*='jobCard']")
        or soup.select("article[class*='job']")
        or soup.select("div.job-container")
    )

    # Fallback: look for any div with an anchor to a job URL
    if not cards:
        cards = [
            a.find_parent("div")
            for a in soup.find_all("a", href=re.compile(r"/j/[a-z0-9-]+-\d+"))
            if a.find_parent("div")
        ]
        # Deduplicate
        seen = set()
        unique_cards = []
        for c in cards:
            cid = id(c)
            if cid not in seen:
                seen.add(cid)
                unique_cards.append(c)
        cards = unique_cards

    for card in cards:
        # Title + URL
        link = (
            card.select_one("h2 a, h3 a, a[class*='title'], a[href*='/j/']")
        )
        if not link:
            continue
        title = link.get_text(strip=True)
        href = link.get("href", "")
        url = href if href.startswith("http") else BASE_URL + href

        # Extract job ID from URL
        id_match = re.search(r"-(\d+)(?:/|$)", href)
        job_id = id_match.group(1) if id_match else ""

        # Company name
        company_el = card.select_one(
            "span.company, div.company, span[class*='company'], "
            "div[class*='company'], a[class*='company']"
        )
        company = company_el.get_text(strip=True) if company_el else None
        if not company or company.lower() in ("", "confidential"):
            company = "Confidential"

        # Location
        location_el = card.select_one(
            "span.location, span[class*='location'], div[class*='location']"
        )
        location = location_el.get_text(strip=True) if location_el else None

        # Experience
        exp_el = card.select_one(
            "span.experience, span[class*='exp'], div[class*='experience']"
        )
        experience = exp_el.get_text(strip=True) if exp_el else None

        # Date
        date_el = card.select_one(
            "span.date, span[class*='date'], time, div[class*='posted']"
        )
        date = date_el.get_text(strip=True) if date_el else None

        # Short description / snippet
        desc_el = card.select_one("p, div[class*='desc'], div[class*='snippet']")
        description = desc_el.get_text(strip=True)[:300] if desc_el else None

        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "experience": experience,
            "date": date,
            "description": description,
            "url": url,
        })

    return jobs


def search_jobs(
    query: str,
    location: str = "",
    experience: str = "",
    limit: int = None,
) -> dict:
    params: dict = {"q": query}

    loc_lower = location.lower().strip()
    if loc_lower and loc_lower in LOCATION_IDS:
        params["loc"] = LOCATION_IDS[loc_lower]
    elif loc_lower:
        # IIM Jobs also accepts location as text in some URL patterns
        params["loc"] = loc_lower

    if experience:
        try:
            params["exp"] = str(int(experience))
        except ValueError:
            pass

    resp = http_get(SEARCH_URL, params=params)
    soup = BeautifulSoup(resp.text, "lxml")
    jobs = parse_job_listings(soup)

    # Try to get total count
    total = 0
    count_el = soup.select_one(
        "span.total-jobs, div[class*='result-count'], span[class*='count']"
    )
    if count_el:
        nums = re.findall(r"[\d,]+", count_el.get_text())
        if nums:
            try:
                total = int(nums[0].replace(",", ""))
            except ValueError:
                pass

    if limit:
        jobs = jobs[:limit]

    return {
        "meta": {
            "query": query,
            "location": location or "All India",
            "experience": experience or "Any",
            "total": total,
        },
        "jobs": jobs,
    }


def fetch_detail(url: str) -> dict:
    if not url.startswith("http"):
        url = BASE_URL + url

    resp = http_get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one("h1, div[class*='job-title'] h1, h1[class*='title']")
    company_el = soup.select_one(
        "div[class*='company-name'], span[class*='company'], a[class*='company']"
    )
    location_el = soup.select_one("span[class*='location'], div[class*='location']")
    exp_el = soup.select_one("span[class*='experience'], div[class*='exp']")
    salary_el = soup.select_one("span[class*='salary'], div[class*='salary'], span[class*='ctc']")
    date_el = soup.select_one("span[class*='date'], time, div[class*='posted']")
    desc_el = soup.select_one(
        "div[class*='job-desc'], div#jobDescription, "
        "div[class*='description'], section[class*='desc']"
    )

    # Try JSON-LD
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                desc_html = data.get("description", "")
                desc_text = BeautifulSoup(desc_html, "lxml").get_text(separator="\n", strip=True)
                loc = data.get("jobLocation", {})
                if isinstance(loc, list):
                    loc = loc[0] if loc else {}
                return {
                    "title": data.get("title", ""),
                    "company": data.get("hiringOrganization", {}).get("name") or "Confidential",
                    "location": loc.get("address", {}).get("addressLocality") or None,
                    "experience": None,
                    "salary": None,
                    "date": data.get("datePosted") or None,
                    "description": desc_text,
                    "url": url,
                    "apply_url": data.get("url") or url,
                }
        except (json.JSONDecodeError, AttributeError):
            continue

    return {
        "title": title_el.get_text(strip=True) if title_el else "",
        "company": (company_el.get_text(strip=True) if company_el else None) or "Confidential",
        "location": location_el.get_text(strip=True) if location_el else None,
        "experience": exp_el.get_text(strip=True) if exp_el else None,
        "salary": salary_el.get_text(strip=True) if salary_el else None,
        "date": date_el.get_text(strip=True) if date_el else None,
        "description": desc_el.get_text(separator="\n", strip=True) if desc_el else "",
        "url": url,
        "apply_url": url,
    }


def format_table(jobs: list) -> str:
    if not jobs:
        return "No jobs found."
    col_title = 42
    col_company = 26
    col_location = 20
    col_exp = 12
    header = (
        f"{'#':<3} {'Title':<{col_title}} {'Company':<{col_company}} "
        f"{'Location':<{col_location}} {'Exp':<{col_exp}}"
    )
    sep = "-" * (3 + 1 + col_title + 1 + col_company + 1 + col_location + 1 + col_exp)
    lines = [header, sep]
    for i, job in enumerate(jobs, 1):
        title = (job.get("title") or "")[:col_title - 1]
        company = (job.get("company") or "")[:col_company - 1]
        location = (job.get("location") or "")[:col_location - 1]
        exp = (job.get("experience") or "")[:col_exp - 1]
        lines.append(
            f"{i:<3} {title:<{col_title}} {company:<{col_company}} "
            f"{location:<{col_location}} {exp:<{col_exp}}"
        )
    return "\n".join(lines)


def cmd_search(args: argparse.Namespace) -> None:
    try:
        result = search_jobs(
            query=args.query,
            location=args.location or "",
            experience=args.experience or "",
            limit=args.limit,
        )
        if args.format == "table":
            meta = result["meta"]
            total_str = f"{meta['total']:,}" if meta["total"] else "?"
            print(
                f"Query: \"{meta['query']}\"  Location: {meta['location']}  "
                f"Experience: {meta['experience']}  Total: {total_str}\n"
            )
            print(format_table(result["jobs"]))
        elif args.format == "plain":
            for job in result["jobs"]:
                print(f"{job['title']}  —  {job.get('company', 'Confidential')}")
                if job.get("location"):
                    print(f"  Location   : {job['location']}")
                if job.get("experience"):
                    print(f"  Experience : {job['experience']}")
                if job.get("date"):
                    print(f"  Posted     : {job['date']}")
                print(f"  URL        : {job['url']}")
                print()
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_error(str(exc), "SEARCH_FAILED")
        sys.exit(1)


def cmd_detail(args: argparse.Namespace) -> None:
    try:
        detail = fetch_detail(args.url)
        if args.format == "plain":
            print(detail["title"])
            print(f"Company    : {detail.get('company', 'Confidential')}")
            if detail.get("location"):
                print(f"Location   : {detail['location']}")
            if detail.get("experience"):
                print(f"Experience : {detail['experience']}")
            if detail.get("salary"):
                print(f"Salary     : {detail['salary']}")
            if detail.get("date"):
                print(f"Posted     : {detail['date']}")
            print(f"\n{detail.get('description', '')}")
            print(f"\nApply: {detail.get('apply_url', detail['url'])}")
        else:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_error(str(exc), "DETAIL_FAILED")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="IIM Jobs search CLI — management and senior roles in India",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="Search IIM Jobs listings")
    search_p.add_argument("-q", "--query", required=True, help="Role, function, or sector keyword")
    search_p.add_argument(
        "-l", "--location",
        help="City filter (e.g. Bangalore, Mumbai, Delhi, Hyderabad, Pune, Chennai)",
    )
    search_p.add_argument(
        "-e", "--experience",
        help="Minimum experience in years (e.g. 5, 10)",
    )
    search_p.add_argument("--limit", type=int, help="Max results to display")
    search_p.add_argument("--format", choices=["json", "table", "plain"], default="json")
    search_p.set_defaults(func=cmd_search)

    detail_p = sub.add_parser("detail", help="Get full job details from an IIM Jobs URL")
    detail_p.add_argument("url", help="Full IIM Jobs URL")
    detail_p.add_argument("--format", choices=["json", "plain"], default="json")
    detail_p.set_defaults(func=cmd_detail)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
