#!/usr/bin/env python3
"""Indeed India job search CLI (in.indeed.com)."""

import re
import sys
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://in.indeed.com"
SEARCH_URL = f"{BASE_URL}/jobs"
DETAIL_URL = f"{BASE_URL}/viewjob"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://in.indeed.com/",
}

JOB_TYPE_MAP = {
    "fulltime": "fulltime",
    "parttime": "parttime",
    "contract": "contract",
    "internship": "internship",
    "temporary": "temporary",
}

MAX_RETRIES = 3


def write_error(message: str, code: str) -> None:
    sys.stderr.write(json.dumps({"error": message, "code": code}) + "\n")


def http_get(url: str, params: dict = None) -> requests.Response:
    session = requests.Session()
    session.headers.update(HEADERS)
    delay = 1.5
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=15, allow_redirects=True)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == MAX_RETRIES - 1:
                    resp.raise_for_status()
                time.sleep(delay)
                delay = min(delay * 2, 10.0)
                continue
            if resp.status_code == 403:
                raise RuntimeError(
                    "Indeed blocked the request (403). "
                    "Try again in a moment or use a different search."
                )
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
    raise RuntimeError("Request failed after max retries")


def parse_job_cards(soup: BeautifulSoup) -> list:
    jobs = []

    for card in soup.find_all("div", class_="job_seen_beacon"):
        # Job key from the title link
        title_el = card.select_one("h2.jobTitle a[data-jk], h2.jobTitle a[id]")
        if not title_el:
            title_el = card.select_one("h2.jobTitle a")
        if not title_el:
            continue

        job_key = title_el.get("data-jk") or ""
        if not job_key:
            # Try extracting from id attribute: "jobTitle-<key>"
            id_attr = title_el.get("id", "")
            job_key = id_attr.replace("jobTitle-", "") if id_attr else ""

        title = title_el.get_text(strip=True)
        if not title:
            span = title_el.find("span")
            title = span.get_text(strip=True) if span else ""

        company_el = card.select_one("[data-testid='company-name']")
        location_el = card.select_one("[data-testid='text-location']")
        salary_el = card.select_one(
            "[data-testid='attribute_snippet_testid'], "
            ".salary-snippet-container .salary-snippet"
        )
        date_el = card.select_one("span.date, .jobMetaDataGroup span.date")
        snippet_el = card.select_one(".job-snippet, div.css-9446fg")

        url = f"{BASE_URL}/viewjob?jk={job_key}" if job_key else ""

        jobs.append({
            "id": job_key,
            "title": title,
            "company": company_el.get_text(strip=True) if company_el else None,
            "location": location_el.get_text(strip=True) if location_el else None,
            "salary": salary_el.get_text(strip=True) if salary_el else None,
            "date": date_el.get_text(strip=True) if date_el else None,
            "description": snippet_el.get_text(separator=" ", strip=True) if snippet_el else None,
            "url": url,
        })

    return jobs


def search_jobs(
    query: str,
    location: str = "",
    job_type: str = None,
    recency: int = None,
    start: int = 0,
    limit: int = None,
) -> dict:
    params: dict = {
        "q": query,
        "start": str(start),
    }
    if location:
        params["l"] = location
    if job_type and job_type in JOB_TYPE_MAP:
        params["jt"] = JOB_TYPE_MAP[job_type]
    if recency:
        params["fromage"] = str(recency)  # max days since posting

    resp = http_get(SEARCH_URL, params=params)
    soup = BeautifulSoup(resp.text, "lxml")

    jobs = parse_job_cards(soup)

    # Try to extract total count
    total = 0
    count_el = soup.select_one("div#searchCountPages, [data-testid='jobsearch-JobCountAndSortPane-jobCount']")
    if count_el:
        text = count_el.get_text()
        nums = re.findall(r"[\d,]+", text)
        if nums:
            try:
                total = int(nums[-1].replace(",", ""))
            except ValueError:
                pass

    if limit:
        jobs = jobs[:limit]

    return {
        "meta": {"query": query, "location": location or "India", "start": start, "total": total},
        "jobs": jobs,
    }


def fetch_detail(job_key: str) -> dict:
    # Accept full URL or bare job key
    if job_key.startswith("http"):
        match = re.search(r"jk=([a-z0-9]+)", job_key)
        if match:
            job_key = match.group(1)

    resp = http_get(DETAIL_URL, params={"jk": job_key})
    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one("h1.jobsearch-JobInfoHeader-title, h1[data-testid='jobsearch-JobInfoHeader-title']")
    company_el = soup.select_one(
        "div[data-testid='inlineHeader-companyName'] a, "
        "div[data-company-name='true']"
    )
    location_el = soup.select_one("div[data-testid='inlineHeader-companyLocation']")
    salary_el = soup.select_one("#salaryInfoAndJobType span, div[id*='salary']")
    desc_el = soup.select_one(
        "div#jobDescriptionText, div.jobsearch-JobComponent-description"
    )

    # Try to find apply link
    apply_el = soup.select_one("a#applyButton, a[data-jk][href*='apply']")
    apply_url = apply_el.get("href", "") if apply_el else f"{BASE_URL}/viewjob?jk={job_key}"
    if apply_url and not apply_url.startswith("http"):
        apply_url = BASE_URL + apply_url

    return {
        "id": job_key,
        "title": title_el.get_text(strip=True) if title_el else "",
        "company": company_el.get_text(strip=True) if company_el else None,
        "location": location_el.get_text(strip=True) if location_el else None,
        "salary": salary_el.get_text(strip=True) if salary_el else None,
        "description": desc_el.get_text(separator="\n", strip=True) if desc_el else "",
        "url": f"{BASE_URL}/viewjob?jk={job_key}",
        "apply_url": apply_url,
    }


def format_table(jobs: list) -> str:
    if not jobs:
        return "No jobs found."
    col_title = 42
    col_company = 28
    col_location = 22
    col_date = 14
    header = (
        f"{'#':<3} {'Title':<{col_title}} {'Company':<{col_company}} "
        f"{'Location':<{col_location}} {'Posted':<{col_date}}"
    )
    sep = "-" * (3 + 1 + col_title + 1 + col_company + 1 + col_location + 1 + col_date)
    lines = [header, sep]
    for i, job in enumerate(jobs, 1):
        title = (job.get("title") or "")[:col_title - 1]
        company = (job.get("company") or "")[:col_company - 1]
        location = (job.get("location") or "")[:col_location - 1]
        date = (job.get("date") or "")[:col_date - 1]
        lines.append(
            f"{i:<3} {title:<{col_title}} {company:<{col_company}} "
            f"{location:<{col_location}} {date:<{col_date}}"
        )
    return "\n".join(lines)


def cmd_search(args: argparse.Namespace) -> None:
    try:
        result = search_jobs(
            query=args.query,
            location=args.location or "",
            job_type=args.job_type,
            recency=args.recency,
            start=args.start,
            limit=args.limit,
        )
        if args.format == "table":
            meta = result["meta"]
            total_str = f"{meta['total']:,}" if meta["total"] else "?"
            print(f"Query: \"{meta['query']}\"  Location: {meta['location']}  "
                  f"Total: {total_str}  Showing offset: {meta['start']}\n")
            print(format_table(result["jobs"]))
        elif args.format == "plain":
            for job in result["jobs"]:
                print(f"{job['title']}  —  {job.get('company', 'Unknown')}")
                if job.get("location"):
                    print(f"  Location : {job['location']}")
                if job.get("salary"):
                    print(f"  Salary   : {job['salary']}")
                if job.get("date"):
                    print(f"  Posted   : {job['date']}")
                print(f"  URL      : {job['url']}")
                print()
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_error(str(exc), "SEARCH_FAILED")
        sys.exit(1)


def cmd_detail(args: argparse.Namespace) -> None:
    try:
        detail = fetch_detail(args.key)
        if args.format == "plain":
            print(detail["title"])
            if detail.get("company"):
                print(f"Company  : {detail['company']}")
            if detail.get("location"):
                print(f"Location : {detail['location']}")
            if detail.get("salary"):
                print(f"Salary   : {detail['salary']}")
            print(f"\n{detail.get('description', '')}")
            print(f"\nApply: {detail['apply_url']}")
        else:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_error(str(exc), "DETAIL_FAILED")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Indeed India job search CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="Search job listings on Indeed India")
    search_p.add_argument("-q", "--query", required=True, help="Search keywords")
    search_p.add_argument("-l", "--location", help="City or region (e.g. Bangalore, Mumbai, Remote)")
    search_p.add_argument(
        "--job-type", choices=list(JOB_TYPE_MAP.keys()),
        help="Employment type filter",
    )
    search_p.add_argument(
        "--recency", type=int, choices=[1, 3, 7, 14],
        help="Only jobs posted within N days",
    )
    search_p.add_argument("--start", type=int, default=0, help="Pagination offset (0, 10, 20, ...)")
    search_p.add_argument("--limit", type=int, help="Max results to display")
    search_p.add_argument("--format", choices=["json", "table", "plain"], default="json")
    search_p.set_defaults(func=cmd_search)

    detail_p = sub.add_parser("detail", help="Get full job details from Indeed")
    detail_p.add_argument("key", help="Job key (jk hash) or full Indeed job URL")
    detail_p.add_argument("--format", choices=["json", "plain"], default="json")
    detail_p.set_defaults(func=cmd_detail)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
