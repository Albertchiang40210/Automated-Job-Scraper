import json
import logging

from ai_matcher import evaluate_job
from config import LIMIT_PER_SOURCE, PROFILES_FILE, SCORE_THRESHOLD, SEEN_FILE
from discord_notifier import send_discord_notification
from scrapers.scraper_104 import scrape_104
from utils import dedupe_jobs, job_key, load_seen, save_seen, setup_logging

log = logging.getLogger(__name__)

# 目前啟用的求職平台(1111 有驗證閘門,尚未支援)
SCRAPERS = {"104": scrape_104}


def load_profiles(path=PROFILES_FILE):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_resume(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
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


def run_profile(profile, seen):
    """執行單一求職檔案;seen 會被就地更新(key 帶有 profile 名稱,不同檔案互不影響)。"""
    name = profile["name"]
    resume = read_resume(profile["resume"])
    if not resume:
        log.error("[%s] 找不到或空白的履歷檔 %s,略過此檔案。", name, profile["resume"])
        return
    threshold = profile.get("threshold", SCORE_THRESHOLD)
    log.info("=== [%s] 關鍵字: %s ===", name, ", ".join(profile["keywords"]))

    jobs = dedupe_jobs(scrape_all(profile["keywords"], profile.get("limit", LIMIT_PER_SOURCE)))
    new_jobs = [j for j in jobs if f"{name}|{job_key(j)}" not in seen]
    log.info("[%s] 抓取 %d 筆(去重後),其中 %d 筆為新職缺", name, len(jobs), len(new_jobs))

    recommended = []
    for i, job in enumerate(new_jobs, 1):
        log.info("[%s] 評估中 (%d/%d): %s - %s", name, i, len(new_jobs), job["platform"], job["title"])
        result = evaluate_job(resume, job["title"], job["description"], profile.get("fallback_keywords"),
                              profile.get("level", "junior"))
        if result.get("error"):
            continue  # 完全失敗:不記錄為已看過,下次再試
        job["score"], job["reason"] = result["score"], result["reason"]
        log.info("[%s] 分數 %3d | %s | %s", name, job["score"], job["title"], job["reason"][:80])
        if not result.get("fallback"):  # 備援評分的職缺下次再用 AI 重評
            seen.add(f"{name}|{job_key(job)}")
        if job["score"] >= threshold:
            recommended.append(job)

    if recommended:
        log.info("[%s] 共 %d 筆符合條件,發送通知", name, len(recommended))
        send_discord_notification(recommended, label=name,
                                  webhook_env=profile.get("webhook_env", "DISCORD_WEBHOOK_URL"))
    else:
        log.info("[%s] 沒有分數達 %d 的新推薦職缺。", name, threshold)


def main():
    setup_logging()
    seen = load_seen(SEEN_FILE)
    try:
        for profile in load_profiles():
            run_profile(profile, seen)
            save_seen(SEEN_FILE, seen)  # 每個檔案跑完就存,中途中斷不會全部重來
    finally:
        save_seen(SEEN_FILE, seen)


if __name__ == "__main__":
    main()
