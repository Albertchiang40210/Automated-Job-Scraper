import logging

from ai_matcher import evaluate_job
from config import KEYWORDS, LIMIT_PER_SOURCE, SCORE_THRESHOLD, SEEN_FILE
from discord_notifier import send_discord_notification
from scrapers.scraper_104 import scrape_104
from utils import dedupe_jobs, job_key, load_seen, save_seen, setup_logging

log = logging.getLogger(__name__)

# 目前啟用的求職平台(1111 有驗證閘門,尚未支援)
SCRAPERS = {"104": scrape_104}


def read_resume():
    try:
        with open("resume_summary.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.error("找不到 resume_summary.txt,請建立該檔案並填寫您的履歷摘要。")
        return ""


def scrape_all(keywords, limit):
    jobs = []
    for keyword in keywords:
        for name, fn in SCRAPERS.items():
            try:
                jobs.extend(fn(keyword=keyword, limit=limit))
            except Exception as e:
                log.error("%s 爬蟲失敗: %s", name, e)
    return jobs


def main():
    setup_logging()
    log.info("=== 啟動求職爬蟲 (%s) ===", ", ".join(KEYWORDS))
    resume_text = read_resume()
    if not resume_text:
        return

    seen = load_seen(SEEN_FILE)
    jobs = dedupe_jobs(scrape_all(KEYWORDS, LIMIT_PER_SOURCE))
    new_jobs = [j for j in jobs if job_key(j) not in seen]
    log.info("抓取 %d 筆(去重後),其中 %d 筆為新職缺,開始 AI 評估", len(jobs), len(new_jobs))

    recommended = []
    for i, job in enumerate(new_jobs, 1):
        log.info("評估中 (%d/%d): %s - %s", i, len(new_jobs), job["platform"], job["title"])
        result = evaluate_job(resume_text, job["title"], job["description"])
        if result.get("error"):
            continue  # 完全失敗:不記錄為已看過,下次再試
        job["score"], job["reason"] = result["score"], result["reason"]
        if not result.get("fallback"):  # 備援評分的職缺下次再用 AI 重評
            seen.add(job_key(job))
        if job["score"] >= SCORE_THRESHOLD:
            recommended.append(job)
    save_seen(SEEN_FILE, seen)

    if recommended:
        log.info("共 %d 筆符合條件,發送通知", len(recommended))
        send_discord_notification(recommended)
    else:
        log.info("今日沒有分數達 %d 的新推薦職缺。", SCORE_THRESHOLD)


if __name__ == "__main__":
    main()
