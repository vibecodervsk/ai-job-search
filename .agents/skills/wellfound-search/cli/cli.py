#!/usr/bin/env python3
"""
Wellfound (formerly AngelList Talent) job search CLI.
Parses job listings from Wellfound's server-rendered pages and embedded JSON data.
"""

import re
import sys
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://wellfound.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://wellfound.com/",
}

MAX_RETRIES = 3


def write_error(message: str, code: str) -> None:
    sys.stderr.write(json.dumps({"error": message, "code": code}) + "\n")


def http_get(url: str, params: dict = None) -> requests.Response:
    delay = 1.5
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
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


def extract_next_data(html: str) -> dict:
    """Extract __NEXT_DATA__ JSON embedded in Next.js page."""
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def find_jobs_in_next_data(data: dict) -> list:
    """
    Walk the __NEXT_DATA__ tree to find job listing objects.
    Wellfound's data structure nests jobs inside Apollo cache or page props.
    """
    jobs = []

    def walk(node, depth=0):
        if depth > 10:
            return
        if isinstance(node, dict):
            # Detect a job posting object by looking for key fields
            if (
                node.get("title")
                and node.get("id")
                and (node.get("slug") or node.get("jobType") or node.get("remote") is not None)
            ):
                startup = node.get("startup") or {}
                jobs.append({
                    "id": str(node.get("id", "")),
                    "title": node.get("title", ""),
                    "company": startup.get("name") or node.get("companyName") or None,
                    "location": _extract_location(node),
                    "remote": node.get("remote"),
                    "salary": _extract_salary(node),
                    "equity": node.get("equityMin") and node.get("equityMax") and (
                        f"{node.get('equityMin')}% – {node.get('equityMax')}%"
                    ),
                    "url": _build_url(node, startup),
                    "description": (node.get("description") or "")[:300] or None,
                })
            for v in node.values():
                walk(v, depth + 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, depth + 1)

    walk(data)
    # Deduplicate by id
    seen = set()
    unique = []
    for job in jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            unique.append(job)
    return unique


def _extract_location(node: dict) -> str | None:
    locs = node.get("locations") or []
    if locs and isinstance(locs, list):
        names = [loc.get("displayName") or loc.get("name") for loc in locs if isinstance(loc, dict)]
        names = [n for n in names if n]
        if names:
            return ", ".join(names)
    return node.get("locationNames") or None


def _extract_salary(node: dict) -> str | None:
    lo = node.get("salaryMin")
    hi = node.get("salaryMax")
    if lo and hi:
        return f"${lo:,} – ${hi:,}"
    if lo:
        return f"${lo:,}+"
    return None


def _build_url(node: dict, startup: dict) -> str:
    slug = node.get("slug")
    startup_slug = startup.get("slug") or startup.get("name", "").lower().replace(" ", "-")
    if slug and startup_slug:
        return f"{BASE_URL}/jobs/{startup_slug}/{slug}"
    job_id = node.get("id", "")
    return f"{BASE_URL}/jobs/{job_id}"


def parse_jobs_from_html(soup: BeautifulSoup) -> list:
    """Fallback: parse job cards directly from rendered HTML."""
    jobs = []
    # Wellfound job cards typically have data-test attributes
    for card in soup.select("[data-test='JobListingCard'], div[class*='JobListing']"):
        title_el = card.select_one("a[data-test='JobListingTitle'], h2 a, h3 a")
        company_el = card.select_one("[data-test='StartupResult'] a, a[class*='startup']")
        location_el = card.select_one("[data-test='location'], span[class*='location']")

        if not title_el:
            continue

        url = title_el.get("href", "")
        if url and not url.startswith("http"):
            url = BASE_URL + url

        jobs.append({
            "id": re.search(r"/(\d+)/?$", url or "").group(1) if re.search(r"/(\d+)/?$", url or "") else "",
            "title": title_el.get_text(strip=True),
            "company": company_el.get_text(strip=True) if company_el else None,
            "location": location_el.get_text(strip=True) if location_el else None,
            "remote": None,
            "salary": None,
            "equity": None,
            "url": url,
            "description": None,
        })
    return jobs


def search_jobs(
    query: str = "",
    location: str = "India",
    limit: int = None,
) -> dict:
    params: dict = {}
    if query:
        params["q"] = query
    if location:
        params["l"] = location.lower()

    resp = http_get(f"{BASE_URL}/jobs", params=params)
    soup = BeautifulSoup(resp.text, "lxml")

    # Try __NEXT_DATA__ first
    next_data = extract_next_data(resp.text)
    jobs = find_jobs_in_next_data(next_data) if next_data else []

    # Fallback to HTML parsing if no jobs found
    if not jobs:
        jobs = parse_jobs_from_html(soup)

    if limit:
        jobs = jobs[:limit]

    return {
        "meta": {"query": query, "location": location, "returned": len(jobs)},
        "jobs": jobs,
    }


def fetch_detail(url: str) -> dict:
    if not url.startswith("http"):
        url = BASE_URL + url

    resp = http_get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    next_data = extract_next_data(resp.text)
    jobs = find_jobs_in_next_data(next_data)

    if jobs:
        job = jobs[0]
        # Try to get full description from __NEXT_DATA__
        desc = job.get("description") or ""
        if len(desc) < 100:
            # Look for a longer description in page props
            try:
                props = next_data.get("props", {}).get("pageProps", {})
                for v in props.values():
                    if isinstance(v, dict) and v.get("description"):
                        full_desc = v["description"]
                        if len(full_desc) > len(desc):
                            desc = full_desc
                            break
            except (AttributeError, TypeError):
                pass
        job["description"] = BeautifulSoup(desc, "lxml").get_text(separator="\n", strip=True)
        job["url"] = url
        return job

    # HTML fallback
    title_el = soup.select_one("h1, [data-test='JobTitle']")
    company_el = soup.select_one("[data-test='StartupName'], h2 a")
    location_el = soup.select_one("[data-test='JobLocation']")
    desc_el = soup.select_one(
        "[data-test='JobDescription'], div[class*='description'], div[class*='Description']"
    )

    return {
        "id": "",
        "title": title_el.get_text(strip=True) if title_el else "",
        "company": company_el.get_text(strip=True) if company_el else None,
        "location": location_el.get_text(strip=True) if location_el else None,
        "remote": None,
        "salary": None,
        "equity": None,
        "description": desc_el.get_text(separator="\n", strip=True) if desc_el else "",
        "url": url,
    }


def format_table(jobs: list) -> str:
    if not jobs:
        return "No jobs found."
    col_title = 40
    col_company = 28
    col_location = 25
    col_salary = 18
    header = (
        f"{'#':<3} {'Title':<{col_title}} {'Company':<{col_company}} "
        f"{'Location':<{col_location}} {'Salary':<{col_salary}}"
    )
    sep = "-" * (3 + 1 + col_title + 1 + col_company + 1 + col_location + 1 + col_salary)
    lines = [header, sep]
    for i, job in enumerate(jobs, 1):
        title = (job.get("title") or "")[:col_title - 1]
        company = (job.get("company") or "")[:col_company - 1]
        loc = (job.get("location") or ("Remote" if job.get("remote") else ""))[:col_location - 1]
        salary = (job.get("salary") or job.get("equity") or "")[:col_salary - 1]
        lines.append(
            f"{i:<3} {title:<{col_title}} {company:<{col_company}} "
            f"{loc:<{col_location}} {salary:<{col_salary}}"
        )
    return "\n".join(lines)


def cmd_search(args: argparse.Namespace) -> None:
    try:
        result = search_jobs(
            query=args.query or "",
            location=args.location or "India",
            limit=args.limit,
        )
        if args.format == "table":
            meta = result["meta"]
            print(f"Query: \"{meta['query']}\"  Location: {meta['location']}  "
                  f"Returned: {meta['returned']}\n")
            print(format_table(result["jobs"]))
        elif args.format == "plain":
            for job in result["jobs"]:
                print(f"{job['title']}  —  {job.get('company', 'Unknown')}")
                loc = job.get("location") or ("Remote" if job.get("remote") else "")
                if loc:
                    print(f"  Location : {loc}")
                if job.get("salary"):
                    print(f"  Salary   : {job['salary']}")
                if job.get("equity"):
                    print(f"  Equity   : {job['equity']}")
                print(f"  URL      : {job['url']}")
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
            if detail.get("company"):
                print(f"Company  : {detail['company']}")
            loc = detail.get("location") or ("Remote" if detail.get("remote") else "")
            if loc:
                print(f"Location : {loc}")
            if detail.get("salary"):
                print(f"Salary   : {detail['salary']}")
            if detail.get("equity"):
                print(f"Equity   : {detail['equity']}")
            print(f"\n{detail.get('description', '')}")
            print(f"\nURL: {detail['url']}")
        else:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_error(str(exc), "DETAIL_FAILED")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Wellfound (AngelList Talent) job search CLI — Indian startups",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="Search Wellfound job listings")
    search_p.add_argument("-q", "--query", help="Role or skill keyword")
    search_p.add_argument(
        "-l", "--location", default="India",
        help="Location filter, e.g. India, Bangalore, remote (default: India)",
    )
    search_p.add_argument("--limit", type=int, help="Max results to display")
    search_p.add_argument("--format", choices=["json", "table", "plain"], default="json")
    search_p.set_defaults(func=cmd_search)

    detail_p = sub.add_parser("detail", help="Get full job details from a Wellfound URL")
    detail_p.add_argument("url", help="Full Wellfound job URL")
    detail_p.add_argument("--format", choices=["json", "plain"], default="json")
    detail_p.set_defaults(func=cmd_detail)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
