#!/bin/sh
# 開機後等網路連上就執行爬蟲;用 flock 避免同時跑兩份。
cd "$(dirname "$0")" || exit 1

# 最多等 5 分鐘讓網路連上
i=0
until curl -s -m 3 -o /dev/null https://www.google.com; do
    i=$((i + 1))
    [ "$i" -ge 60 ] && echo "$(date '+%F %T') 網路無法連線,放棄本次執行" >> run.log && exit 1
    sleep 5
done

exec flock -n /tmp/jobscraper.lock .venv/bin/python main.py >> run.log 2>&1
