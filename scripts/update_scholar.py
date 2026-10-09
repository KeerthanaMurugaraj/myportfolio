#!/usr/bin/env python3
"""Refresh scholar.json from the public Google Scholar profile.

Usage:
    python3 scripts/update_scholar.py              # fetch the live profile
    python3 scripts/update_scholar.py saved.html   # parse a saved copy of the profile page

Google Scholar has no API and often blocks automated requests. When the page
cannot be fetched or parsed, the script exits with an error and leaves
scholar.json untouched, so a blocked run never wipes the existing numbers.
"""
import datetime
import html
import json
import pathlib
import re
import sys
import urllib.request

USER = "np0jog4AAAAJ"
URL = f"https://scholar.google.com/citations?hl=en&user={USER}&cstart=0&pagesize=100&sortby=pubdate"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
OUT = pathlib.Path(__file__).resolve().parent.parent / "scholar.json"


def text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xa0", " ").strip()


def fetch():
    request = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse(page):
    if 'id="gsc_prf_in"' not in page:
        raise ValueError("no profile found in the page (Google Scholar probably blocked the request)")
    stats = [text(s) for s in re.findall(r'class="gsc_rsb_std">(.*?)</td>', page)]
    if len(stats) < 3:
        raise ValueError("citation statistics not found")

    papers = []
    for row in re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', page, re.S):
        link = re.search(r'<a href="([^"]+)" class="gsc_a_at">(.*?)</a>', row, re.S)
        if not link:
            continue
        paper_id = re.search(r"citation_for_view=[\w-]+:([\w-]+)", html.unescape(link.group(1)))
        gray = [text(g) for g in re.findall(r'<div class="gs_gray">(.*?)</div>', row, re.S)]
        cites = re.search(r'class="gsc_a_ac[^"]*">(\d*)</a>', row)
        year = re.search(r'class="gsc_a_h gsc_a_hc gs_ibl">(\d{4})<', row)
        if not paper_id or not year:
            continue
        venue = gray[1] if len(gray) > 1 else ""
        papers.append({
            "scholar": paper_id.group(1),
            "title": text(link.group(2)),
            "authors": gray[0] if gray else "",
            # The venue line ends with the year, which is stored separately.
            "venue": re.sub(r",?\s*\d{4}$", "", venue),
            "year": int(year.group(1)),
            "cites": int(cites.group(1)) if cites and cites.group(1) else 0,
        })
    if not papers:
        raise ValueError("no publications found")

    today = datetime.date.today()
    return {
        "as_of": f"{today.day} {today:%B %Y}",
        "citations": int(stats[0]),
        "h_index": int(stats[2]),
        "papers": papers,
    }


def main():
    try:
        page = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace") if len(sys.argv) > 1 else fetch()
        data = parse(page)
    except Exception as error:  # network errors, HTTP 429, or an unexpected page
        sys.exit(f"Scholar update failed, scholar.json left unchanged: {error}")
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.name}: {len(data['papers'])} papers, {data['citations']} citations, h-index {data['h_index']}")


if __name__ == "__main__":
    main()
