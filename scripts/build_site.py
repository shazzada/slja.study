#!/usr/bin/env python3
"""Build a static replica of the SLJA home page and journal archive."""

import json
import os
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import escape, unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.account.sljo-j-slja.ubiquityjournal.website/api/journal/1"
LIVE = "https://slja.sljol.info"
CACHE = os.path.join(ROOT, "data", "cache")
IMG = os.path.join(ROOT, "assets", "img")
HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context()

LATEST_IDS = [9662, 9946, 9727, 9652, 9638]
POPULAR_TITLES = [
    "Scope of Cardio-Pulmonary Exercise Testing",
    "Haemostatic Effects and Systemic Implications of Intra-Myometrial Vasopressin",
    "Revolutionizing Postoperative Pain Relief",
    "Mind-Body Interaction in Pain",
    "Translation, Cultural Adaptation, and Validation of the Sinhala Version of the Roland-Morris",
]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60, context=CTX) as response:
        return json.load(response)


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url.split("?")[0], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as response:
        data = response.read()
    # Never store article PDFs.
    if dest.lower().endswith(".pdf") or data[:4] == b"%PDF":
        raise RuntimeError("refusing to save a PDF")
    with open(dest, "wb") as handle:
        handle.write(data)
    return dest


def clean_html(value):
    if not value:
        return ""
    text = str(value)
    text = re.sub(r"(?is)<script[\s\S]*?</script>", "", text)
    text = re.sub(r"(?is)<style[\s\S]*?</style>", "", text)
    text = re.sub(r"(?is)<iframe[\s\S]*?</iframe>", "", text)
    text = re.sub(r"\son\w+\s*=\s*(['\"]).*?\1", "", text)
    text = text.replace('href="/', f'href="{LIVE}/')
    return text


def fmt_date(value):
    if not value:
        return ""
    day = str(value)[:10]
    try:
        year, month, date = day.split("-")
        return f"{MONTHS[int(month) - 1]} {int(date)}, {year}"
    except (ValueError, IndexError):
        return escape(str(value))


def text(value):
    return escape(unescape(str(value or "")))


def full_name(author):
    return unescape(f"{author.get('first_name', '').strip()} {author.get('last_name', '').strip()}".strip())


def author_line(authors):
    names = [full_name(author) for author in authors if full_name(author)]
    return ", ".join(names)


def short_authors(authors):
    lasts = [author.get("last_name", "").strip() for author in authors]
    lasts = [name for name in lasts if name]
    if not lasts:
        return ""
    if len(lasts) == 1:
        return lasts[0]
    if len(lasts) == 2:
        return f"{lasts[0]} & {lasts[1]}"
    return f"{lasts[0]} et al."


def issue_label(issue):
    return f"Volume {issue['volume']} - Issue {issue['number']} - {issue['year']}"


def issue_path(issue):
    return f"{issue['id']}/volume/{issue['volume']}/issue/{issue['number']}/index.html"


def article_path(article):
    key = article.get("doi") or str(article["id"])
    return f"articles/{key}/index.html"


def href(from_page, to_page):
    start = os.path.dirname(from_page) or "."
    return os.path.relpath(to_page, start).replace(os.sep, "/")


def official_file(article_id, galley):
    link = galley.get("link") or ""
    filename = link.rstrip("/").split("/")[-1]
    if not filename or "." not in filename:
        return f"{LIVE}/articles/{article_id}"
    return f"{LIVE}/articles/{article_id}/files/{filename}"


def write(path, html):
    dest = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as handle:
        handle.write(html)


def asset(page, name):
    return href(page, f"assets/{name}")


def chrome(page, title):
    home = href(page, "index.html")
    archive = href(page, "issue/archive/index.html")
    css = asset(page, "css/site.css")
    js = asset(page, "js/site.js")
    favicon = asset(page, "img/favicon.png")
    badge = asset(page, "img/jpps.png")
    logo = asset(page, "img/sljol.png")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<link rel="icon" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&amp;display=swap">
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip" href="#main-content">Skip to main content</a>
<header class="topbar">
  <div class="topbar-inner">
    <nav aria-label="Main navigation">
      <ul class="nav">
        <li><a href="{home}">Home</a></li>
        <li class="has-sub">
          <a class="nav-label" href="{LIVE}/about">About <span class="caret">▼</span></a>
          <ul class="submenu">
            <li><a href="{LIVE}/about">About the Journal</a></li>
            <li><a href="{LIVE}/about/editorialteam">Editorial Board</a></li>
            <li><a href="{LIVE}/about/editorialpolicies">Editorial Policies</a></li>
            <li><a href="{LIVE}/about/submissions">Submissions</a></li>
          </ul>
        </li>
        <li><a href="{LIVE}/contact">Contact</a></li>
        <li class="has-sub">
          <a class="nav-label" href="{archive}">Content <span class="caret">▼</span></a>
          <ul class="submenu">
            <li><a href="{LIVE}/articles">Articles</a></li>
            <li><a href="{archive}">Issue Archive</a></li>
          </ul>
        </li>
      </ul>
    </nav>
    <div class="tools-right">
      <form class="search" action="{LIVE}/search" method="get" role="search">
        <input type="search" name="query" aria-label="Search" placeholder="Search…">
        <button type="submit" aria-label="Submit"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="10" cy="10" r="6" fill="none" stroke="#fff" stroke-width="2"/><path d="M14.5 14.5 L20 20" stroke="#fff" stroke-width="2"/></svg></button>
      </form>
      <a class="account" href="{LIVE}/login">Account</a>
    </div>
  </div>
</header>
<div class="brand">
  <div class="brand-inner">
    <h1><a href="{home}">Sri Lankan Journal of Anaesthesiology</a></h1>
    <a href="https://www.journalquality.info/en/jpps-criteria/two-stars"><img class="badge" src="{badge}" alt="Journal Publishing Practices and Standards, two stars"></a>
    <a class="btn" href="{LIVE}/about/submissions">Start Submission</a>
    <a class="btn" href="https://account.slja.sljol.info/index.php/sljo-j-slja/user/profile?intent=reviewer#roles">Become a Reviewer</a>
    <a href="https://sljol.info"><img class="sljol" src="{logo}" alt="SLJOL"></a>
  </div>
</div>
""", css, js


FOOTER = f"""
<footer class="footer">
  <div class="footer-inner">
    <ul>
      <li>E-ISSN: 2279-1965</li>
      <li>Print ISSN: 1391-8834</li>
      <li>Published by <a href="https://anaesthesia.lk/">College of Anaesthesiologists of Sri Lanka</a></li>
      <li><a href="{LIVE}/about/tandc">Terms and Conditions</a></li>
      <li><a href="{LIVE}/about/privacypolicy">Privacy Policy</a></li>
      <li><a href="{LIVE}/about/accessibility">Accessibility</a></li>
    </ul>
    <p class="powered"><a href="https://www.ubiquitypress.com/">Powered by Ubiquity</a></p>
  </div>
</footer>
"""


def end(js):
    return f'{FOOTER}<script src="{js}"></script></body></html>\n'


def side_issue_list(page, issues, current_id=None):
    items = []
    for issue in issues:
        path = href(page, issue_path(issue))
        klass = "current" if issue["id"] == current_id else ""
        items.append(f'<li><a class="{klass}" href="{path}">{escape(issue_label(issue))}</a></li>')
    return f'<aside class="side"><h2>Articles</h2><ul class="issue-list">{"".join(items)}</ul></aside>'


def article_rows(page, articles, thumb, detailed=False):
    rows = []
    for article in articles:
        link = href(page, article_path(article))
        date = fmt_date(article.get("date_published"))
        authors = escape(author_line(article.get("authors") or []))
        title = text(article.get("title") or "")
        extra = ""
        if detailed:
            pages = escape(article.get("pages") or "")
            vol = escape(str(article.get("volume") or ""))
            num = escape(str(article.get("number") or ""))
            galley = ""
            if article.get("files"):
                galley = f'<a class="dl" href="{escape(article["files"][0]["url"])}" title="Download">↓</a><br>'
            extra = f'<div class="meta-col">{galley}{date}<br><a href="{link}">{vol}({num}): {pages}</a></div>'
            grid = "article-row"
        else:
            extra = f'<div class="meta-col">{date}</div>'
            grid = "article-row home-row"
        rows.append(
            f'<li class="{grid}"><a href="{link}"><img class="thumb" src="{thumb}" alt=""></a>'
            f'<div><h4><a href="{link}">{title}</a></h4><p class="authors">{authors}</p></div>{extra}</li>'
        )
    return "".join(rows)


def side_cards(page, articles, thumb):
    cards = []
    for article in articles:
        link = href(page, article_path(article))
        cards.append(
            "<article class=\"side-item\">"
            f'<a href="{link}"><img src="{thumb}" alt=""></a><div>'
            f'<h3><a href="{link}">{text(article.get("title") or "")}</a></h3>'
            f'<div class="side-meta"><span>{escape(short_authors(article.get("authors") or []))}</span>'
            f"<span>{fmt_date(article.get('date_published'))}</span></div></div></article>"
        )
    return "".join(cards)


def normalize_issue_article(raw, issue):
    files = []
    for galley in raw.get("galleys") or []:
        files.append({
            "label": galley.get("label") or "PDF",
            "language": galley.get("language") or "",
            "url": official_file(raw["submission_id"], galley),
        })
    return {
        "id": raw["submission_id"],
        "doi": raw.get("doi") or "",
        "title": raw.get("title") or "",
        "authors": [{"first_name": a.get("first_name") or "", "last_name": a.get("last_name") or ""} for a in raw.get("authors") or []],
        "date_published": raw.get("date_published") or "",
        "pages": raw.get("pages") or "",
        "files": files,
        "volume": issue["volume"],
        "number": issue["number"],
        "year": issue["year"],
        "issue_id": issue["id"],
        "section": "",
    }


def fetch_article(article_id):
    cached = os.path.join(CACHE, f"{article_id}.json")
    if os.path.exists(cached):
        with open(cached, encoding="utf-8") as handle:
            return json.load(handle)
    raw = get_json(f"{API}/article/{article_id}")
    files = []
    for galley in raw.get("galleys") or []:
        files.append({
            "label": galley.get("label") or "File",
            "language": galley.get("language") or "",
            "url": official_file(article_id, galley),
        })
    authors = []
    for author in raw.get("authors") or []:
        social = author.get("social") or {}
        authors.append({
            "first_name": author.get("first_name") or "",
            "last_name": author.get("last_name") or "",
            "institution": author.get("institution") or "",
            "country": author.get("country") or "",
            "email": author.get("email") or "",
            "orcid": social.get("orcid") or "",
        })
    issue = raw.get("issue") or {}
    record = {
        "id": raw.get("submission_id") or article_id,
        "doi": raw.get("doi") or "",
        "title": raw.get("title") or "",
        "abstract": clean_html(raw.get("abstract") or ""),
        "keywords": raw.get("keywords") or [],
        "authors": authors,
        "section": raw.get("section") or "",
        "pages": raw.get("pages") or "",
        "date_published": raw.get("date_published") or "",
        "date_submitted": raw.get("date_submitted") or "",
        "license_name": (raw.get("license") or {}).get("name") or "",
        "license_link": (raw.get("license") or {}).get("link") or "",
        "files": files,
        "references": clean_html(raw.get("references") or ""),
        "volume": (issue.get("volume") or {}).get("value"),
        "number": (issue.get("number") or {}).get("value"),
        "year": (issue.get("year") or {}).get("value"),
        "issue_id": issue.get("issue_id"),
    }
    os.makedirs(CACHE, exist_ok=True)
    with open(cached, "w", encoding="utf-8") as handle:
        json.dump(record, handle)
    return record


def build():
    os.makedirs(IMG, exist_ok=True)
    journal = get_json(API)
    current = get_json(f"{API}/issue/current")
    carousel = get_json(f"{API}/carousel")
    issue_list = get_json(f"{API}/issue")["results"]

    download(journal["favicon"]["link"], os.path.join(IMG, "favicon.png"))
    download(journal["thumbnail"]["link"], os.path.join(IMG, "thumb.jpg"))
    download("https://www.journalquality.info/journalquality/img/2.png", os.path.join(IMG, "jpps.png"))
    download(journal.get("cover", {}).get("link") or issue_list[0]["cover_image"], os.path.join(IMG, "press-cover.png"))
    logo = "https://storage.googleapis.com/jnl-sljo-j-slja-public/journals/1/pressLogoImage_en_US.png"
    download(logo, os.path.join(IMG, "sljol.png"))
    slide = (carousel.get("slides") or [{}])[0].get("img")
    if slide:
        download(slide, os.path.join(IMG, "hero.png"))

    issues = []
    for summary in issue_list:
        detail = get_json(f"{API}/issue/{summary['issue_id']}")
        cover_name = f"cover-{summary['issue_id']}.png"
        if summary.get("cover_image"):
            download(summary["cover_image"], os.path.join(IMG, cover_name))
        issue = {
            "id": summary["issue_id"],
            "volume": summary["volume"]["value"],
            "number": summary["number"]["value"],
            "year": summary["year"]["value"],
            "date_published": summary.get("date_published") or "",
            "cover": f"assets/img/{cover_name}" if summary.get("cover_image") else "",
            "sections": [],
        }
        for section in detail.get("sections") or []:
            articles = []
            for raw in section.get("articles") or []:
                item = normalize_issue_article(raw, issue)
                item["section"] = section.get("name") or ""
                articles.append(item)
            if articles:
                issue["sections"].append({"name": section.get("name") or "", "articles": articles})
        issues.append(issue)
        print(f"issue {issue['id']} {issue_label(issue)}", flush=True)

    ids = []
    for issue in issues:
        for section in issue["sections"]:
            for article in section["articles"]:
                ids.append(article["id"])
    page_no = 1
    catalog = []
    while True:
        payload = get_json(f"{API}/article?count=50&page={page_no}")
        catalog.extend(payload.get("results") or [])
        if page_no >= payload.get("last_page", page_no):
            break
        page_no += 1
    for item in catalog:
        ids.append(item["submission_id"])
    ids = list(dict.fromkeys(ids))
    print(f"fetching {len(ids)} article records", flush=True)

    articles = {}
    failures = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_article, article_id): article_id for article_id in ids}
        done = 0
        for future in as_completed(futures):
            article_id = futures[future]
            done += 1
            try:
                articles[article_id] = future.result()
            except Exception as error:
                failures.append((article_id, str(error)))
            if done % 50 == 0:
                print(f"articles {done}/{len(ids)}", flush=True)

    def merge(stub):
        full = articles.get(stub["id"])
        if not full:
            return stub
        merged = dict(full)
        merged["files"] = full.get("files") or stub.get("files") or []
        merged["pages"] = full.get("pages") or stub.get("pages") or ""
        merged["volume"] = full.get("volume") or stub.get("volume")
        merged["number"] = full.get("number") or stub.get("number")
        merged["year"] = full.get("year") or stub.get("year")
        merged["issue_id"] = full.get("issue_id") or stub.get("issue_id")
        merged["section"] = full.get("section") or stub.get("section") or ""
        if not merged.get("authors"):
            merged["authors"] = stub.get("authors") or []
        return merged

    for issue in issues:
        for section in issue["sections"]:
            section["articles"] = [merge(article) for article in section["articles"]]

    by_title = {article["title"]: article for article in articles.values()}
    popular = []
    for needle in POPULAR_TITLES:
        match = next((article for title, article in by_title.items() if needle in title), None)
        if match:
            popular.append(match)
    latest = [articles[article_id] for article_id in LATEST_IDS if article_id in articles]
    current_issue = next((issue for issue in issues if issue["id"] == current.get("issue_id")), issues[0])

    render(journal, issues, current_issue, articles, latest, popular)
    print(f"built {len(issues)} issues and {len(articles)} articles; failures {len(failures)}", flush=True)
    if failures:
        print(failures[:10], flush=True)


def render(journal, issues, current_issue, articles, latest, popular):
    page = "index.html"
    head, css, js = chrome(page, "Sri Lankan Journal of Anaesthesiology")
    thumb = asset(page, "img/thumb.jpg")
    hero = asset(page, "img/hero.png")
    toc = []
    for section in current_issue["sections"]:
        toc.append(f'<section><h3>{escape(section["name"])}</h3><ul class="toc-section">')
        toc.append(article_rows(page, section["articles"], thumb, detailed=False))
        toc.append("</ul></section>")
    latest_html = side_cards(page, latest, thumb)
    popular_html = side_cards(page, popular or latest, thumb)
    about = clean_html(journal.get("description") or "")
    write(page, head + f"""
<main id="main-content" class="sheet">
  <div>
    <img class="cover-hero" src="{hero}" alt="Sri Lankan Journal of Anaesthesiology, Volume {escape(str(current_issue['volume']))} Number {escape(str(current_issue['number']))} {escape(str(current_issue['year']))}">
    <div class="rss-bar"><a href="https://account.slja.sljol.info/index.php/sljo-j-slja/gateway/plugin/WebFeedGatewayPlugin/atom" title="Follow via RSS" aria-label="Follow via RSS"><svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="6" cy="18" r="2.2" fill="#fff"/><path d="M4 10a10 10 0 0 1 10 10" fill="none" stroke="#fff" stroke-width="2"/><path d="M4 5a15 15 0 0 1 15 15" fill="none" stroke="#fff" stroke-width="2"/></svg></a></div>
    <h2 class="block">Current Issue</h2>
    <a class="issue-link" href="{href(page, issue_path(current_issue))}">{escape(issue_label(current_issue))}</a>
    <h2 class="block">About this journal</h2>
    <div class="about">{about}</div>
    <h2 class="block">Table of contents</h2>
    {''.join(toc)}
  </div>
  <aside class="side" data-tabs>
    <div class="side-tabs">
      <button class="active" type="button" data-tab="latest">Latest Articles</button>
      <button type="button" data-tab="popular">Popular Articles</button>
    </div>
    <div class="side-panel active" data-panel="latest">{latest_html}</div>
    <div class="side-panel" data-panel="popular">{popular_html}</div>
  </aside>
</main>
""" + end(js))

    def archive_page(path, selected_year, subset):
        head, css, js = chrome(path, "Issue Archive | Sri Lankan Journal of Anaesthesiology")
        cards = []
        for issue in subset:
            cover = href(path, issue["cover"]) if issue["cover"] else ""
            cards.append(
                f'<a href="{href(path, issue_path(issue))}"><img src="{cover}" alt="{escape(issue_label(issue))}"></a>'
            )
        years = []
        seen = []
        for issue in issues:
            if issue["year"] not in seen:
                seen.append(issue["year"])
        for year in seen:
            target = "issue/archive/index.html" if selected_year is None and False else f"issue/archive/{year}/index.html"
            if selected_year is None:
                pass
            klass = "active" if year == selected_year else ""
            years.append(f'<li><a class="{klass}" href="{href(path, f"issue/archive/{year}/index.html")}">{year}</a></li>')
        write(path, head + f"""
<main id="main-content" class="sheet">
  <div>
    <h2 class="block">Issue Archive</h2>
    <div class="archive-grid">{''.join(cards)}</div>
  </div>
  <aside class="side">
    <h2>Filter by Year</h2>
    <ul class="years">{''.join(years)}</ul>
  </aside>
</main>
""" + end(js))

    archive_page("issue/archive/index.html", None, issues)
    years = []
    for issue in issues:
        if issue["year"] not in years:
            years.append(issue["year"])
    for year in years:
        archive_page(f"issue/archive/{year}/index.html", year, [issue for issue in issues if issue["year"] == year])

    for issue in issues:
        path = issue_path(issue)
        head, css, js = chrome(path, f"{issue_label(issue)} | Sri Lankan Journal of Anaesthesiology")
        thumb = asset(path, "img/thumb.jpg")
        sections = []
        for section in issue["sections"]:
            sections.append(f'<h2 class="section">{escape(section["name"])}</h2><ul class="toc-section">')
            sections.append(article_rows(path, section["articles"], thumb, detailed=True))
            sections.append("</ul>")
        share = f"{LIVE}/{issue['id']}/volume/{issue['volume']}/issue/{issue['number']}"
        write(path, head + f"""
<main id="main-content" class="sheet">
  <div>
    <div class="issue-head">
      <h2>{escape(issue_label(issue))}</h2>
      <div class="menu" data-menu>
        <button class="share" type="button">↗ Share</button>
        <div class="panel"><a href="{share}">Open the official issue</a></div>
      </div>
    </div>
    {''.join(sections)}
  </div>
  {side_issue_list(path, issues, issue["id"])}
</main>
""" + end(js))

    for article in articles.values():
        path = article_path(article)
        head, css, js = chrome(path, f"{article['title']} | Sri Lankan Journal of Anaesthesiology")
        issue = next((item for item in issues if item["id"] == article.get("issue_id")), None)
        issue_href = href(path, issue_path(issue)) if issue else href(path, "issue/archive/index.html")
        authors = []
        for author in article.get("authors") or []:
            icons = []
            if author.get("orcid"):
                icons.append(f'<a class="icon-btn orcid" href="{escape(author["orcid"])}" title="ORCID">iD</a>')
            if author.get("email"):
                icons.append(f'<a class="icon-btn" href="mailto:{escape(author["email"])}" title="Email">✉</a>')
            more = ""
            bits = [bit for bit in [author.get("institution"), author.get("country")] if bit]
            if bits:
                more = f'<div class="author-more">{escape(" · ".join(bits))}</div>'
            authors.append(
                f'<li><div class="author-line"><span>{escape(full_name(author))}</span>{"".join(icons)}'
                f'<button class="chev" type="button" data-author aria-expanded="false" aria-label="Toggle author information panel">⌄</button></div>{more}</li>'
            )
        keywords = []
        for keyword in article.get("keywords") or []:
            keywords.append(f'<a href="{LIVE}/search?query={escape(keyword)}">{escape(keyword)}</a>')
        files = []
        for galley in article.get("files") or []:
            label = galley["label"]
            if galley.get("language"):
                label = f'{label} ({galley["language"]})'
            files.append(f'<a href="{escape(galley["url"])}">{escape(label)}</a>')
        if not files:
            files.append(f'<a href="{LIVE}/articles/{article["id"]}">View on the official site</a>')
        doi = article.get("doi") or ""
        doi_html = f'<a href="https://doi.org/{escape(doi)}">DOI: {escape(doi)}</a>' if doi else ""
        vol = article.get("volume")
        num = article.get("number")
        vol_html = ""
        if vol:
            vol_html = f'<a href="{issue_href}">Volume: {escape(str(vol))} Issue: {escape(str(num or ""))}</a>'
        license_html = ""
        if article.get("license_name"):
            link = article.get("license_link") or f"{LIVE}/articles/{article['id']}"
            license_html = f'<p class="license"><a href="{escape(link)}">{escape(article["license_name"])}</a></p>'
        citation = (
            f'{escape(author_line(article.get("authors") or []))}. ({escape(str(article.get("year") or ""))}). '
            f'{text(article["title"])}. Sri Lankan Journal of Anaesthesiology, '
            f'{escape(str(vol or ""))}({escape(str(num or ""))}), {escape(article.get("pages") or "")}.'
        )
        if doi:
            citation += f' https://doi.org/{escape(doi)}'
        refs = ""
        if article.get("references") and len(article["references"]) < 40000:
            refs = f'<h2>References</h2><div class="abstract">{article["references"]}</div>'
        abstract = article.get("abstract") or "<p>No abstract is available for this article.</p>"
        write(path, head + f"""
<div class="toolbar">
  <p class="reading"><b>Reading:</b> {text(article["title"])}</p>
  <div class="tool-row">
    <div class="menu" data-menu>
      <button class="btn-navy" type="button">↓ Download</button>
      <div class="panel">{''.join(files)}</div>
    </div>
    <button class="font-ctl" type="button" data-font="up" aria-label="Increase font size">A+</button>
    <button class="font-ctl" type="button" data-font="down" aria-label="Decrease font size">A−</button>
    <span class="pct" data-pct>100%</span>
    <label class="switch"><input type="checkbox" data-alt> Alt. Display</label>
    <div class="menu" data-menu>
      <button class="ghost" type="button" aria-label="Cite this article">Cite</button>
      <div class="panel"><p class="cite-box">{citation}</p></div>
    </div>
  </div>
</div>
<main id="main-content" class="sheet">
  <article class="article">
    <p class="kicker">{escape(article.get("section") or "")}</p>
    <h1>{text(article["title"])}</h1>
    <ul class="author-list">{''.join(authors)}</ul>
    <h2>Abstract</h2>
    <div class="abstract">{abstract}</div>
    <p class="keywords"><b>Keywords:</b> {', '.join(keywords)}</p>
    <div class="pubmeta">
      <span>Year: {escape(str(article.get("year") or ""))}</span>
      {vol_html}
      <span>Page/Article: {escape(article.get("pages") or "")}</span>
      {doi_html}
    </div>
    <div class="dates">
      <span>Accepted on {fmt_date(article.get("date_submitted"))}</span>
      <span>Published on {fmt_date(article.get("date_published"))}</span>
    </div>
    {license_html}
    {refs}
    <section class="metrics">
      <h2>Metrics</h2>
      <p>Live view and download counts are shown on the official article page.</p>
      <p><a href="{LIVE}/articles/{escape(doi or str(article['id']))}">Open this article on slja.sljol.info</a></p>
    </section>
  </article>
  <aside class="side" data-tabs>
    <div class="side-tabs article-tabs">
      <button class="active" type="button" data-tab="contents">Contents</button>
      <button type="button" data-tab="notes">Annotations &amp; Comments</button>
      <button type="button" data-tab="related">Related Articles</button>
    </div>
    <div class="side-panel active" data-panel="contents"><ul class="anchor-list"><li><a href="#main-content">Abstract</a></li></ul></div>
    <div class="side-panel" data-panel="notes"><p class="note">Annotations and comments are available on the official article page.</p></div>
    <div class="side-panel" data-panel="related"><p class="note">Related-article suggestions are loaded on the official article page.</p></div>
  </aside>
</main>
""" + end(js))


if __name__ == "__main__":
    build()
