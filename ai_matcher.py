import json
import logging
import os
import re
import time

import requests

from config import GEMINI_MIN_INTERVAL, GEMINI_MODEL

log = logging.getLogger(__name__)
_last_call = 0.0


def _throttle():
    """確保兩次 API 呼叫間隔至少 GEMINI_MIN_INTERVAL 秒(第一次不等待)。"""
    global _last_call
    wait = _last_call + GEMINI_MIN_INTERVAL - time.monotonic()
    if _last_call and wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def fallback_score(job_description: str, keywords=None, level="junior") -> dict:
    """API 無法使用時的關鍵字備援評分。

    keywords: 命中任一個就加分;英文字詞使用單字邊界(避免 'email' 命中 'ai')。
    level: "junior" 偏好初階/無經驗職缺;"senior" 偏好有經驗/資深職缺。
    """
    desc = job_description.lower()
    score, reason = 60, "API 降級模式:未發現關鍵技能。"
    hit = any(
        (re.search(rf"\b{re.escape(k.lower())}\b", desc) if k.isascii() else k in desc)
        for k in (keywords or [])
    )
    if hit:
        score += 20
        reason = "API 降級模式:發現相關關鍵字,初步判定符合。"
    junior = re.search(r"\bjunior\b|助理|實習|儲備|無經驗|不拘經驗", desc)
    senior = re.search(r"\bsenior\b|資深|主管|經理|\blead\b", desc)
    if level == "senior":
        if senior:
            score += 15
            reason += " 符合資深/主管等級。"
        elif junior:
            score -= 10
    elif level == "junior":
        if junior:
            score += 15
            reason += " 適合初階/實習等級。"
        elif senior:
            score -= 10
    score = min(score, 100)
    if score >= 90:
        reason = "[關鍵字精準命中] " + reason
    return {"score": score, "reason": reason, "fallback": True}


def _fallback(description, keywords, level="junior"):
    # 沒有設定備援關鍵字的檔案不使用備援評分(避免用不相干的規則亂打分)
    if not keywords:
        return {"score": 0, "reason": "API 無法使用", "error": True}
    return fallback_score(description, keywords, level)


def parse_response(text: str) -> dict:
    """解析模型回覆(容忍 markdown code fence),失敗丟出 ValueError。"""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    data = json.loads(text)
    return {"score": max(0, min(100, int(data["score"]))), "reason": str(data.get("reason", "無"))}


def evaluate_job(resume_text: str, job_title: str, job_description: str,
                 fallback_keywords=None, level="junior") -> dict:
    """回傳 {"score", "reason"};備援評分含 "fallback": True,完全無法評估含 "error": True。"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.warning("未設定 GEMINI_API_KEY,跳過 AI 評估。")
        return {"score": 0, "reason": "No API Key", "error": True}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    prompt = f"""你是一個專業的職涯顧問。請根據以下求職者的「履歷摘要」與「職缺資訊」,評估此職缺與求職者的匹配程度。

【求職者履歷摘要】
{resume_text}

【職缺資訊】
職缺名稱:{job_title}
職缺描述:{job_description}

請以 JSON 回覆:{{"score": 85, "reason": "簡短說明"}}。score 為 0 到 100 的整數。"""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    for attempt in range(3):
        _throttle()
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        except requests.RequestException as e:
            log.error("Gemini 連線失敗: %s", type(e).__name__)
            return _fallback(job_description, fallback_keywords, level)

        if resp.status_code in (429, 500, 502, 503, 504) and attempt < 2:
            backoff = 30 * (2 ** attempt)
            log.warning("Gemini %s,%d 秒後重試", resp.status_code, backoff)
            time.sleep(backoff)
            continue
        if resp.status_code in (400, 401, 403, 404):
            # 設定錯誤(模型/金鑰/請求格式):不用備援分數,避免把職缺誤記為已評估
            log.error("Gemini 設定錯誤 %s (模型 %s): %s", resp.status_code, GEMINI_MODEL, resp.text[:300])
            return {"score": 0, "reason": f"Gemini 設定錯誤 {resp.status_code}", "error": True}
        if resp.status_code != 200:
            log.error("Gemini 請求失敗,狀態碼 %s: %s", resp.status_code, resp.text[:300])
            return _fallback(job_description, fallback_keywords, level)
        try:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return parse_response(text)
        except (KeyError, IndexError, ValueError, TypeError) as e:
            log.error("Gemini 回覆解析失敗: %s", e)
            return _fallback(job_description, fallback_keywords, level)
    return _fallback(job_description, fallback_keywords, level)
