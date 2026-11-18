import logging
import os
import time

import requests

log = logging.getLogger(__name__)


def _color(score):
    return 5763719 if score >= 85 else 16776960  # 綠 / 黃(低於門檻的不會被推薦)


def build_embeds(jobs, label=None):
    embeds = []
    for job in sorted(jobs, key=lambda x: x.get("score", 0), reverse=True):
        score = job.get("score", 0)
        desc = f"**公司:** {job.get('company')}\n**匹配度:** {score} 分\n**AI 簡評:** {job.get('reason')}"
        embeds.append({
            "title": f"[{label + '｜' if label else ''}{job.get('platform')}] {job.get('title')}"[:256],
            "url": job.get("link"),
            "description": desc[:4000],
            "color": _color(score),
        })
    return embeds


def _post(url, payload):
    for _ in range(3):
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 429:
                time.sleep(float(r.json().get("retry_after", 2)) + 0.5)
                continue
            r.raise_for_status()
            return True
        except requests.RequestException as e:
            log.error("發送 Discord 通知失敗: %s", e)
            return False
    return False


def send_discord_notification(jobs: list, label=None, webhook_env="DISCORD_WEBHOOK_URL"):
    # 若該檔案有專屬 webhook(profile 的 webhook_env 指定,例如 DISCORD_WEBHOOK_URL_ADMIN)則使用,否則用預設
    webhook_url = os.getenv(webhook_env) or os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        log.warning("未設定 DISCORD_WEBHOOK_URL,跳過通知發送。")
        return
    if not jobs:
        return
    embeds = build_embeds(jobs, label)
    for i in range(0, len(embeds), 10):  # webhook 一次最多 10 個 embeds
        payload = {
            "content": f"🔔 **今日 AI 推薦職缺來囉!{('(' + label + ')') if label else ''}**" if i == 0 else "",
            "embeds": embeds[i:i + 10],
        }
        _post(webhook_url, payload)
