#!/usr/bin/env python3
"""KFU Moodle Downloader - mobile web app.

Runs a small local web server. Open the phone browser to the PC's IP:port,
paste a MoodleSession cookie, browse college -> semester -> course, tick files,
and download. Files are saved on the PC (this machine) into the chosen folder.

Usage:
    python webdl.py [--port 5000] [--host 0.0.0.0]
"""
import os
import re
import argparse
import threading
import queue
import time
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_from_directory

BASE = "https://elearning.kfu.edu.eg"
COLLEGE_BY_NAME = {"medicine": 3, "dental": 2, "pharmacy": 1}

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ------------------------------------------------------------------ downloader
def sanitize(name, maxlen=90):
    name = re.sub(r'[<>:"/\\|?*]', "_", name or "").replace("\n", " ").strip()
    name = re.sub(r"\s+", " ", name)
    return name[:maxlen].strip(" .") or "untitled"


def abs_url(h):
    return h if h.startswith("http") else BASE + h


def sem_number(title):
    m = re.search(r"(\d+)", title)
    if m:
        return int(m.group(1))
    words = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
             "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}
    low = title.lower().split()
    for w, n in words.items():
        if w in low:
            return n
    return None


class Downloader:
    def __init__(self, cookie):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        self.s.cookies.set("MoodleSession", cookie, domain="elearning.kfu.edu.eg")
        self._cache = {}

    def check(self):
        r = self.s.get(BASE + "/my/", timeout=40)
        soup = BeautifulSoup(r.content, "html.parser", from_encoding="utf-8")
        b = soup.find("body")
        return not (b and "notloggedin" in " ".join(b.get("class", [])))

    def semesters(self, ccat):
        r = self.s.get(f"{BASE}/course/index.php?categoryid={ccat}", timeout=40)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser", from_encoding="utf-8")
        out, seen = [], set()
        for a in soup.find_all("a", href=True):
            m = re.search(r"course/index\.php\?categoryid=(\d+)", a["href"])
            if not m:
                continue
            cid = int(m.group(1))
            if cid in seen or cid == ccat or cid == 5:
                continue
            seen.add(cid)
            out.append((cid, " ".join(a.stripped_strings).strip() or f"Semester {len(out)+1}"))
        return out

    def courses(self, category):
        r = self.s.get(f"{BASE}/course/index.php?categoryid={category}", timeout=40)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser", from_encoding="utf-8")
        out, seen = [], set()
        for a in soup.find_all("a", href=True):
            m = re.search(r"/course/view\.php\?id=(\d+)", a["href"])
            if not m:
                continue
            cid = int(m.group(1))
            if cid in seen:
                continue
            seen.add(cid)
            out.append((cid, " ".join(a.stripped_strings).strip() or f"Course {cid}"))
        return out

    def resources(self, course_url):
        r = self.s.get(course_url, timeout=40)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser", from_encoding="utf-8")
        out, seen = [], set()
        for a in soup.find_all("a", href=True):
            h = a["href"]
            if "/mod/resource/view.php?id=" not in h:
                continue
            url = abs_url(h)
            if url in seen:
                continue
            seen.add(url)
            out.append((url, " ".join(a.stripped_strings).strip()))
        return out

    def resource_name(self, url, label):
        if url in self._cache:
            return self._cache[url]
        name = ""
        try:
            r = self.s.get(url, timeout=60, allow_redirects=True)
            r.raise_for_status()
            cd = r.headers.get("Content-Disposition", "")
            m = re.search(r'filename="?([^";]+)"?', cd)
            name = m.group(1).strip() if m else unquote(os.path.basename(r.url.split("?")[0]))
        except Exception:
            pass
        name = sanitize(os.path.basename(name))
        if not os.path.splitext(name)[1]:
            name = sanitize(label or "file")
        self._cache[url] = name
        return name

    def stream(self, url):
        """Return (Response, filename). Caller is responsible for closing."""
        r = self.s.get(url, timeout=180, allow_redirects=True, stream=True)
        r.raise_for_status()
        cd = r.headers.get("Content-Disposition", "")
        m = re.search(r'filename="?([^";]+)"?', cd)
        name = m.group(1).strip() if m else unquote(os.path.basename(r.url.split("?")[0]))
        return r, sanitize(os.path.basename(name)) or "file"


# Per-cookie active sessions, keyed by a client-provided token.
SESSIONS = {}
ACTIVE_DL = threading.Lock()


def get_dl(token):
    d = SESSIONS.get(token)
    if d is None:
        raise ValueError("Cookie not verified yet.")
    return d


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/dl/<path:f>")
def getfile(f):
    return send_from_directory("static", f)


@app.route("/api/connect", methods=["POST"])
def connect():
    data = request.get_json(force=True)
    cookie = (data.get("cookie") or "").strip()
    if not cookie:
        return jsonify(ok=False, error="Cookie missing")
    d = Downloader(cookie)
    if not d.check():
        return jsonify(ok=False, error="Invalid/expired cookie")
    token = cookie[:12]
    SESSIONS[token] = d
    return jsonify(ok=True, token=token)


@app.route("/api/semesters")
def api_semesters():
    try:
        d = get_dl(request.args["token"])
        college = request.args.get("college", "medicine").lower()
        return jsonify(ok=True, semesters=[{"id": c, "title": t}
                                           for c, t in d.semesters(COLLEGE_BY_NAME[college])])
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route("/api/courses")
def api_courses():
    try:
        d = get_dl(request.args["token"])
        cat = int(request.args["category"])
        return jsonify(ok=True, courses=[{"id": c, "name": n} for c, n in d.courses(cat)])
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route("/api/files")
def api_files():
    try:
        d = get_dl(request.args["token"])
        cid = int(request.args["course"])
        res = d.resources(f"{BASE}/course/view.php?id={cid}")
        items = [{"idx": i, "url": u, "label": l, "name": d.resource_name(u, l)}
                 for i, (u, l) in enumerate(res)]
        return jsonify(ok=True, files=items)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route("/api/download")
def api_download():
    """Download a single file directly to the phone (streamed through browser)."""
    try:
        d = get_dl(request.args["token"])
        url = request.args["url"]
        r, name = d.stream(url)
        ct = r.headers.get("Content-Type", "")
        if "text/html" in ct:
            r.close()
            return jsonify(ok=False, error="That link is a web page, not a file.")
        headers = {"Content-Disposition": f'attachment; filename="{name}"'}
        return r.raw, 200, headers
    except Exception as e:
        return jsonify(ok=False, error=str(e))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", default=5000, type=int)
    args = ap.parse_args()
    print(f"\nKFU Moodle Downloader running at:")
    print(f"  http://127.0.0.1:{args.port}")
    print(f"  On your phone, open: http://<THIS-PC-LAN-IP>:{args.port}\n")
    app.run(host=args.host, port=args.port, threaded=True)