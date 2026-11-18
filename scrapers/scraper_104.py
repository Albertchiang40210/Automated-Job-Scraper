import logging

import requests

from config import USER_AGENT

log = logging.getLogger(__name__)
API = "https://www.104.com.tw/jobs/search/api/jobs"


def scrape_104(keyword="AI Engineer", limit=10):
    """使用 104 公開 JSON API,不需要瀏覽器。"""
    log.info("[104] 搜尋: %s", keyword)
    headers = {"User-Agent": USER_AGENT, "Referer": "https://www.104.com.tw/jobs/search/"}
    params = {"keyword": keyword, "order": 1, "page": 1, "jobsource": "2018indexpoc"}
    try:
        resp = requests.get(API, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("data", [])
    except Exception as e:
        log.error("[104] 爬蟲錯誤: %s", e)
        return []

    jobs = []
    for item in items[:limit]:
        link = (item.get("link") or {}).get("job", "")
        if link.startswith("//"):
            link = "https:" + link
        title = (item.get("jobName") or "").strip()
        if not (title and link):
            continue
        jobs.append({
            "platform": "104",
            "title": title,
            "company": item.get("custName", ""),
            "link": link,
            "description": (item.get("description") or "無敘述")[:1500],
        })
    return jobs
