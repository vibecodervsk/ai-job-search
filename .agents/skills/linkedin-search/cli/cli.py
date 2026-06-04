#!/usr/bin/env python3
"""LinkedIn job search CLI using the public guest API (no auth required)."""

import re
import sys
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.linkedin.com/jobs/search/",
}

JOB_TYPE_MAP = {
    "fulltime": "F",
    "parttime": "P",
    "contract": "C",
    "internship": "I",
    "temporary": "T",
}

EXPERIENCE_MAP = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid-senior": "4",
    "director": "5",
    "executive": "6",
}

RECENCY_MAP = {
    "day": "r86400",
    "week": "r604800",
    "month": "r2592000",
}

MAX_RETRIES = 3


def write_error(message: str, code: str) -> None:
    sys.stderr.write(json.dumps({"error": message, "code": code}) + "\n")


def http_get(url: str, params: dict = None) -> requests.Response:
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == MAX_RETRIES - 1:
                    resp.raise_for_status()
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
    raise RuntimeError("Request failed after max retries")


def extract_job_id(entity_urn: str) -> str:
    """Extract numeric job ID from LinkedIn entity URN."""
    match = re.search(r":(\d+)$", entity_urn or "")
    return match.group(1) if match else ""


def parse_job_cards(html: str) -> list:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.find_all("div", attrs={"data-entity-urn": True}):
        urn = card.get("data-entity-urn", "")
        job_id = extract_job_id(urn)
        if not job_id:
            continue

        title_el = card.select_one(".base-search-card__title")
        company_el = card.select_one(".base-search-card__subtitle")
        location_el = card.select_one(".job-search-card__location")
        date_el = card.select_one("time")
        link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")

        url = ""
        if link_el:
            href = link_el.get("href", "")
            url = href.split("?")[0] if href else ""

        jobs.append({
            "id": job_id,
            "title": title_el.get_text(strip=True) if title_el else "",
            "company": company_el.get_text(strip=True) if company_el else None,
            "location": location_el.get_text(strip=True) if location_el else None,
            "date": date_el.get("datetime") if date_el else None,
            "url": url or f"https://www.linkedin.com/jobs/view/{job_id}/",
        })

    return jobs


def search_jobs(
    query: str,
    location: str = "India",
    job_type: str = None,
    experience: str = None,
    recency: str = None,
    start: int = 0,
    limit: int = None,
) -> dict:
    params = {
        "keywords": query,
        "location": location,
        "start": str(start),
        "count": "25",
    }
    if job_type and job_type in JOB_TYPE_MAP:
        params["f_JT"] = JOB_TYPE_MAP[job_type]
    if experience and experience in EXPERIENCE_MAP:
        params["f_E"] = EXPERIENCE_MAP[experience]
    if recency and recency in RECENCY_MAP:
        params["f_TPR"] = RECENCY_MAP[recency]

    resp = http_get(SEARCH_URL, params=params)
    jobs = parse_job_cards(resp.text)

    if limit:
        jobs = jobs[:limit]

    return {
        "meta": {"query": query, "location": location, "start": start, "returned": len(jobs)},
        "jobs": jobs,
    }


def fetch_detail(job_id: str) -> dict:
    # Accept either a numeric ID or a full LinkedIn URL
    if job_id.startswith("http"):
        match = re.search(r"/jobs/view/(?:[^/]+-)?(\d+)", job_id)
        if match:
            job_id = match.group(1)

    resp = http_get(DETAIL_URL.format(job_id=job_id))
    soup = BeautifulSoup(resp.text, "lxml")

    title_el = soup.select_one("h2.top-card-layout__title, h1.topcard__title")
    company_el = soup.select_one("a.topcard__org-name-link, span.topcard__flavor")
    location_el = soup.select_one("span.topcard__flavor--bullet")
    criteria = soup.select("li.description__job-criteria-item")
    desc_el = soup.select_one(
        "div.show-more-less-html__markup, div.description__text"
    )

    criteria_map: dict = {}
    for item in criteria:
        label_el = item.select_one("h3")
        value_el = item.select_one("span")
        if label_el and value_el:
            criteria_map[label_el.get_text(strip=True)] = value_el.get_text(strip=True)

    description = ""
    if desc_el:
        description = desc_el.get_text(separator="\n", strip=True)

    return {
        "id": job_id,
        "title": title_el.get_text(strip=True) if title_el else "",
        "company": company_el.get_text(strip=True) if company_el else None,
        "location": location_el.get_text(strip=True) if location_el else None,
        "seniority": criteria_map.get("Seniority level"),
        "employment_type": criteria_map.get("Employment type"),
        "job_function": criteria_map.get("Job function"),
        "industries": criteria_map.get("Industries"),
        "description": description,
        "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
        "apply_url": f"https://www.linkedin.com/jobs/view/{job_id}/",
    }


def format_table(jobs: list) -> str:
    if not jobs:
        return "No jobs found."
    col_title = 45
    col_company = 30
    col_location = 22
    col_date = 12
    header = (
        f"{'#':<3} {'Title':<{col_title}} {'Company':<{col_company}} "
        f"{'Location':<{col_location}} {'Date':<{col_date}}"
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
            location=args.location or "India",
            job_type=args.job_type,
            experience=args.experience,
            recency=args.recency,
            start=args.start,
            limit=args.limit,
        )
        if args.format == "table":
            meta = result["meta"]
            print(f"Query: \"{meta['query']}\"  Location: {meta['location']}  "
                  f"Showing: {meta['returned']} results\n")
            print(format_table(result["jobs"]))
        elif args.format == "plain":
            for job in result["jobs"]:
                print(f"{job['title']}  —  {job.get('company', 'Unknown')}")
                if job.get("location"):
                    print(f"  Location : {job['location']}")
                if job.get("date"):
                    print(f"  Date     : {job['date']}")
                print(f"  ID       : {job['id']}")
                print(f"  URL      : {job['url']}")
                print()
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_error(str(exc), "SEARCH_FAILED")
        sys.exit(1)


def cmd_detail(args: argparse.Namespace) -> None:
    try:
        detail = fetch_detail(args.id)
        if args.format == "plain":
            print(detail["title"])
            if detail.get("company"):
                print(f"Company         : {detail['company']}")
            if detail.get("location"):
                print(f"Location        : {detail['location']}")
            if detail.get("seniority"):
                print(f"Seniority       : {detail['seniority']}")
            if detail.get("employment_type"):
                print(f"Employment type : {detail['employment_type']}")
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
        description="LinkedIn job search CLI (India)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="Search LinkedIn job listings")
    search_p.add_argument("-q", "--query", required=True, help="Search keywords (job title, skill, company)")
    search_p.add_argument("-l", "--location", default="India",
                          help="Location filter (default: India)")
    search_p.add_argument(
        "--job-type",
        choices=list(JOB_TYPE_MAP.keys()),
        help="Employment type",
    )
    search_p.add_argument(
        "--experience",
        choices=list(EXPERIENCE_MAP.keys()),
        help="Experience level",
    )
    search_p.add_argument(
        "--recency",
        choices=list(RECENCY_MAP.keys()),
        help="Posting recency filter",
    )
    search_p.add_argument("--start", type=int, default=0,
                          help="Pagination offset (0, 25, 50, ...)")
    search_p.add_argument("--limit", type=int, help="Max results to display")
    search_p.add_argument(
        "--format", choices=["json", "table", "plain"], default="json",
    )
    search_p.set_defaults(func=cmd_search)

    detail_p = sub.add_parser("detail", help="Get full details for a LinkedIn job")
    detail_p.add_argument("id", help="LinkedIn job ID (numeric) or full job URL")
    detail_p.add_argument("--format", choices=["json", "plain"], default="json")
    detail_p.set_defaults(func=cmd_detail)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
