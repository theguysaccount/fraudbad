"""One place to launch Chromium: system Chrome if present, else Playwright's bundled browser."""
import os


def launch_args():
    for path in ("/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(path):
            return {"executable_path": path, "args": ["--no-sandbox", "--allow-file-access-from-files"]}
    return {"args": ["--no-sandbox", "--allow-file-access-from-files"]}
