"""Убивает процесс, слушающий порт 8000, и запускает бэкенд заново.

После запуска ждёт готовности сервера (до ~20 с) и выводит ошибку,
если сервер так и не поднялся.
"""

import subprocess
import time
import urllib.request

PORT = 8000
HEALTH = f"http://127.0.0.1:{PORT}/api/health"
BACKEND = r"c:\Python\subscription-web\backend"


def find_listeners(port: int) -> set[str]:
    r = subprocess.run(["netstat", "-aon"], capture_output=True, text=True)
    pids: set[str] = set()
    for line in r.stdout.splitlines():
        if f":{port}" in line and "LISTENING" in line.upper():
            parts = line.split()
            if parts:
                pids.add(parts[-1])
    return {p for p in pids if p != "0"}


def health_ok() -> bool:
    try:
        with urllib.request.urlopen(HEALTH, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    for pid in find_listeners(PORT):
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
        cwd=BACKEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    print("backend relaunched, waiting for readiness...")

    for _ in range(20):
        time.sleep(1)
        if health_ok():
            print("server is UP on", HEALTH)
            return
    print("ERROR: server did not start. Check backend\\server.log")


if __name__ == "__main__":
    main()