import os
import sys
import subprocess

from src.config import CRON_SCHEDULE, CRON_LOG_PATH

JOB_TAG = "# telegrambot-daily-send"
PYTHON_PATH = sys.executable
LOG_PATH = os.path.abspath(f"{CRON_LOG_PATH}/cron.log")

script = os.path.abspath("main.py")
entry = f"{CRON_SCHEDULE} {PYTHON_PATH} {script} >> {LOG_PATH} 2>&1 {JOB_TAG}"

result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
existing = result.stdout if result.returncode == 0 else ""

lines = [l for l in existing.splitlines() if JOB_TAG not in l]
lines.append(entry)

subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
print(f"Installed: {entry}")
