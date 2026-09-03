"""Убивает процесс, слушающий порт 8000, и запускает бэкенд заново."""

import subprocess
import time

# найти PID по netstat
r = subprocess.run(["netstat", "-aon"], capture_output=True, text=True)
pids = set()
for line in r.stdout.splitlines():
    if ":8000" in line and "LISTENING" in line.upper():
        pids.add(line.split()[-1])

for pid in pids:
    if pid != "0":
        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
        print("killed", pid)

time.sleep(1)

flags = (
    subprocess.DETACHED_PROCESS
    | subprocess.CREATE_NEW_PROCESS_GROUP
    | subprocess.CREATE_NO_WINDOW
)
subprocess.Popen(
    ["cmd", "/c", r"c:\Python\subscription-web\backend\run_server.bat"],
    creationflags=flags,
    cwd=r"c:\Python\subscription-web\backend",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
)
print("backend relaunched")
