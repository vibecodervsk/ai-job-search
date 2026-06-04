#!/usr/bin/env python3
"""Naukri.com job search CLI for the Indian job market."""

import sys
import json
import argparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.naukri.com"
API_URL = f"{BASE_URL}/jobapi/v3/search"

HEADERS = {
    "appid": "109",
    "systemid": "109",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json",
}

MAX_RETRIES = 3


def write_error(message: str, code: str) -> None:
    sys.stderr.write(json.dumps({"error": message, "code": code}) + "\n")


def api_get(url: str, params: dict = None, extra_headers: dict = None) -> requests.Response:
    headers = {**HEADERS, **(extra_headers or {})}
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == MAX_RETRIES - 1:
                    resp.raise_for_status()
                import time
                time.sleep(delay)
                delay = min(delay * 2, 8.0)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise
    raise RuntimeError("Request failed after max retries")


def search_jobs(
    query: str = "",
    location: str = "",
    experience: str = "",
    job_age: int = None,
    page: int = 1,
    limit: int = None,
) -> dict:
    params = {
        "noOfResults": "20",
        "urlType": "search_by_keyword",
        "searchType": "adv",
        "pageNo": str(page),
        "src": "jobsearchDesk",
        "latLong": "",
    }
    if query:
        params["keyword"] = query
    if location:
        params["location"] = location
    if experience:
        params["experience"] = experience
    if job_age:
        params["jobAge"] = str(job_age)

    resp = api_get(API_URL, params=params)
    data = resp.json()

    jobs = []
    for item in data.get("jobDetails", []):
        placeholders = {
            p.get("placeholderKey", ""): p.get("placeholderValue", "")
            for p in item.get("placeholders", [])
        }
        jobs.append({
            "id": item.get("jobId", ""),
            "title": item.get("title", ""),
            "company": item.get("companyName") or None,
            "location": placeholders.get("location") or None,
            "experience": placeholders.get("experience") or None,
            "salary": placeholders.get("salary") or None,
            "skills": item.get("tagsAndSkills") or None,
            "date": item.get("date") or None,
            "url": item.get("jdURL", ""),
            "description": (item.get("jobDescription", "") or "")[:300] or None,
        })

    if limit:
        jobs = jobs[:limit]

    return {
        "meta": {"total": data.get("noOfJobs", 0), "page": page},
        "jobs": jobs,
    }


def fetch_detail(url: str) -> dict:
    resp = api_get(url, extra_headers={"Accept": "text/html,application/xhtml+xml"})
    soup = BeautifulSoup(resp.text, "lxml")

    # Try JSON-LD structured data first (most reliable)
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                desc_html = data.get("description", "")
                desc_text = BeautifulSoup(desc_html, "lxml").get_text(separator="\n").strip()
                loc = data.get("jobLocation", {})
                if isinstance(loc, list):
                    loc = loc[0] if loc else {}
                return {
                    "title": data.get("title", ""),
                    "company": data.get("hiringOrganization", {}).get("name") or None,
                    "location": loc.get("address", {}).get("addressLocality") or None,
                    "date": data.get("datePosted") or None,
                    "description": desc_text,
                    "salary": None,
                    "url": url,
                    "apply_url": data.get("url") or url,
                }
        except (json.JSONDecodeError, AttributeError):
            continue

    # Fallback: parse page HTML
    title_el = soup.select_one("h1.jd-header-title, h1[class*='title']")
    company_el = soup.select_one("a.jd-header-comp-name, a[class*='comp-name']")
    desc_el = soup.select_one("section.job-desc, div[class*='job-desc'], div[class*='dang-inner-html']")

    return {
        "title": title_el.get_text(strip=True) if title_el else "",
        "company": company_el.get_text(strip=True) if company_el else None,
        "location": None,
        "date": None,
        "description": desc_el.get_text(separator="\n", strip=True) if desc_el else "",
        "salary": None,
        "url": url,
        "apply_url": url,
    }


def format_table(jobs: list) -> str:
    if not jobs:
        return "No jobs found."
    col_title = 45
    col_company = 28
    col_location = 20
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
            query=args.query or "",
            location=args.location or "",
            experience=args.experience or "",
            job_age=args.job_age,
            page=args.page,
            limit=args.limit,
        )
        if args.format == "table":
            print(f"Found {result['meta']['total']:,} jobs  (page {result['meta']['page']})\n")
            print(format_table(result["jobs"]))
        elif args.format == "plain":
            for job in result["jobs"]:
                print(f"{job['title']}  —  {job.get('company', 'Unknown')}")
                if job.get("location"):
                    print(f"  Location : {job['location']}")
                if job.get("experience"):
                    print(f"  Exp      : {job['experience']}")
                if job.get("salary"):
                    print(f"  Salary   : {job['salary']}")
                if job.get("skills"):
                    print(f"  Skills   : {job['skills']}")
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
            if detail.get("location"):
                print(f"Location : {detail['location']}")
            if detail.get("date"):
                print(f"Posted   : {detail['date']}")
            print(f"\n{detail.get('description', '')}")
            if detail.get("apply_url"):
                print(f"\nApply: {detail['apply_url']}")
        else:
            print(json.dumps(detail, indent=2, ensure_ascii=False))
    except Exception as exc:
        write_error(str(exc), "DETAIL_FAILED")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Naukri.com job search CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search_p = sub.add_parser("search", help="Search for jobs on Naukri.com")
    search_p.add_argument("-q", "--query", help="Search keyword (job title, skill, technology)")
    search_p.add_argument("-l", "--location", help="City (e.g. bangalore, mumbai, delhi, hyderabad)")
    search_p.add_argument("-e", "--experience", help="Min experience in years (e.g. 2, 5)")
    search_p.add_argument(
        "--job-age", type=int, choices=[1, 7, 14, 30],
        help="Only jobs posted within N days",
    )
    search_p.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    search_p.add_argument("--limit", type=int, help="Max results to display")
    search_p.add_argument(
        "--format", choices=["json", "table", "plain"], default="json",
        help="Output format (default: json)",
    )
    search_p.set_defaults(func=cmd_search)

    detail_p = sub.add_parser("detail", help="Get full job details from a Naukri URL")
    detail_p.add_argument("url", help="Full Naukri.com job URL")
    detail_p.add_argument(
        "--format", choices=["json", "plain"], default="json",
        help="Output format (default: json)",
    )
    detail_p.set_defaults(func=cmd_detail)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
