# 每日 AI 求職小幫手 (Daily AI Job Scraper)

每天自動從求職平台抓取職缺,用 Google Gemini 依「你的履歷」替每個職缺打分數,只把高分、而且是新出現的職缺推播到 Discord。

支援**多組求職檔案(profile)**:例如同時找「技術職」與「行政職」,每組各有自己的關鍵字、履歷、分數門檻與等級偏好,互不干擾。

## 功能

- **104 人力銀行**:使用 104 公開 JSON API 抓取,不需要瀏覽器;自動過濾 104 固定置頂的推廣職缺,只保留與關鍵字相關的結果。
- **AI 配對**:把職缺內容與履歷摘要交給 Gemini,回傳 0–100 分與簡短理由。
- **去重與已看過紀錄**:同一次執行依連結去重,並把已評估過的職缺記在 `seen_jobs.json`(每個 profile 各自獨立),不會每天重複評估或重複通知。
- **Discord 通知**:依分數由高到低以 Embed 發送,標題帶有 profile 名稱與平台。
- **耐用性**:
  - API 呼叫節流,符合免費額度(預設每 21 秒一次)。
  - 遇到 429 / 5xx 自動退避重試。
  - 模型 / 金鑰 / 請求格式錯誤(400、401、403、404)會直接回報,**不會**悄悄用備援分數,也不會把職缺誤記為已評估。
  - API 暫時失敗時,可用 profile 的關鍵字做備援評分;備援評分的職缺不記為已看過,隔天會用 AI 重評。

## 專案結構

```
main.py                  主流程:讀 profile → 抓取 → 去重 → AI 評分 → 通知
config.py                環境變數設定
ai_matcher.py            Gemini 評分、節流與重試、備援評分
discord_notifier.py      Discord Webhook 通知
utils.py                 去重、已看過紀錄、logging
scrapers/scraper_104.py  104 職缺抓取
profiles.json            求職檔案設定
tests/                   單元測試
```

## 快速開始

需要 Python 3.10 以上。

```bash
git clone https://github.com/Albertchiang40210/Automated-Job-Scraper.git
cd Automated-Job-Scraper
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows:.venv\Scripts\pip
```

### 1. 環境變數(`.env`)

```
GEMINI_API_KEY=你的 Gemini API 金鑰
DISCORD_WEBHOOK_URL=你的 Discord Webhook 網址
```

可選設定:

| 變數 | 預設值 | 說明 |
|---|---|---|
| `GEMINI_MODEL` | `gemini-3.8-flash` | 使用的模型。若出現 404 或「模型已不提供」,請改成目前可用的模型 |
| `GEMINI_MIN_INTERVAL` | `21` | 兩次 API 呼叫的最小間隔(秒) |
| `SCORE_THRESHOLD` | `75` | 預設通知分數門檻 |
| `JOB_LIMIT` | `10` | 每個關鍵字取幾筆 |
| `PROFILES_FILE` | `profiles.json` | 求職檔案設定檔 |
| `SEEN_FILE` | `seen_jobs.json` | 已看過職缺的紀錄檔 |

### 2. 履歷摘要

履歷檔**不會**被 Git 追蹤(已列入 `.gitignore`),請自行建立。範本如下,複製後改成你的內容:

```bash
cp resume_summary.example.txt resume_summary.txt
cp resume_admin.example.txt resume_admin.txt
```

AI 完全依這份摘要評分,寫得越具體越準。建議包含:求職目標、**經驗等級**(初階或資深)、技能、專案、地點與薪資偏好,以及「不想要」的條件。

> 摘要會隨每次評分送到 Gemini API,請不要放姓名、電話、住址等個資。

### 3. 求職檔案(`profiles.json`)

```json
[
  {
    "name": "AI應用工程師",
    "resume": "resume_summary.txt",
    "level": "junior",
    "keywords": ["AI應用工程師", "AI Engineer", "Python", "軟體工程師"],
    "fallback_keywords": ["python", "ai", "machine learning", "deep learning", "llm"]
  }
]
```

| 欄位 | 說明 |
|---|---|
| `name` | 檔案名稱,會顯示在通知標題,也用於已看過紀錄 |
| `resume` | 此檔案使用的履歷摘要路徑 |
| `keywords` | 搜尋關鍵字(每個詞都必須出現在職缺標題或描述才算相關) |
| `level` | 備援評分的等級偏好:`junior`(偏好初階)、`senior`(偏好資深/主管)、`any`(不調整) |
| `fallback_keywords` | API 失敗時的備援關鍵字;不設定則不使用備援評分 |
| `threshold` | (選填)此檔案專屬的分數門檻 |
| `limit` | (選填)此檔案每個關鍵字取幾筆 |
| `webhook_env` | (選填)此檔案專屬的 Webhook 環境變數名稱,例如 `DISCORD_WEBHOOK_URL_ADMIN`,未設定則使用預設網址 |

### 4. 執行

```bash
.venv/bin/python main.py
```

第一次會評估所有新職缺,每筆約 21 秒(受 Gemini 免費額度限制);之後每天只會評估新出現的職缺。

## 部署到 Linux 主機(crontab)

```bash
crontab -e
```

加入一行(每天早上 9 點執行,請換成你的實際路徑):

```
0 9 * * * cd /home/使用者/Automated-Job-Scraper && .venv/bin/python main.py >> run.log 2>&1
```

注意事項:

- cron 不會展開 `~`,請使用絕對路徑。
- 以 `date` 確認主機時區正確(台灣為 `Asia/Taipei`)。
- 若用筆電當主機,需設定蓋上螢幕不休眠(`/etc/systemd/logind.conf` 的 `HandleLidSwitch=ignore`)。
- 查看執行結果:`tail -50 run.log`。

## 測試

```bash
.venv/bin/python -m pytest -q
```

## 已知限制

- **目前只支援 104。** 1111 人力銀行的搜尋頁有驗證閘門(Cloudflare Turnstile 等),無法用一般請求或無頭瀏覽器通過,因此未支援。CakeResume 與 Yourator 因無法穩定取得職缺內文,已移除。
- Gemini 的模型名稱會隨時間下架。若評分一律失敗並出現 404,請依錯誤訊息更換 `GEMINI_MODEL`。
- AI 評分僅供參考,實際投遞前請自行閱讀職缺內容。

## 使用技術

Python、Requests、Google Gemini REST API、Discord Webhook、pytest、cron。
