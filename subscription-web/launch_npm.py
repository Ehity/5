import subprocess

flags = (
    subprocess.DETACHED_PROCESS
    | subprocess.CREATE_NEW_PROCESS_GROUP
    | subprocess.CREATE_NO_WINDOW
)
subprocess.Popen(
    ["cmd", "/c", r"c:\Python\subscription-web\frontend\install.bat"],
    creationflags=flags,
    cwd=r"c:\Python\subscription-web\frontend",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
)
print("npm install launched")
