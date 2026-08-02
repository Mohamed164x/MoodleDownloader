#!/usr/bin/env python3
"""KFU Moodle Downloader - GUI app (tkinter, no extra deps).

Two ways to download:
  A) Semester sweep: pick college + semesters, download every course's files
     into per-course folders.
  B) Course file browser: pick college + semester + a specific course, list its
     files, tick the ones you want, download only the selection.
"""
import os
import re
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

BASE = "https://elearning.kfu.edu.eg"
COLLEGE_BY_NAME = {"medicine": 3, "dental": 2, "pharmacy": 1}


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
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        self.s.cookies.set("MoodleSession", cookie, domain="elearning.kfu.edu.eg")
        self._name_cache = {}

    def check(self):
        r = self.s.get(BASE + "/my/", timeout=40)
        soup = BeautifulSoup(r.content, "html.parser", from_encoding="utf-8")
        body = soup.find("body")
        return not (body and "notloggedin" in " ".join(body.get("class", [])))

    def semesters(self, college_cat):
        r = self.s.get(f"{BASE}/course/index.php?categoryid={college_cat}", timeout=40)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser", from_encoding="utf-8")
        out, seen = [], set()
        for a in soup.find_all("a", href=True):
            m = re.search(r"course/index\.php\?categoryid=(\d+)", a["href"])
            if not m:
                continue
            cid = int(m.group(1))
            if cid in seen or cid == college_cat or cid == 5:
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

    def resolve_name(self, url, label):
        """Resolve a resource's real filename. Cached."""
        if url in self._name_cache:
            return self._name_cache[url]
        name = ""
        try:
            r = self.s.get(url, timeout=60, allow_redirects=True)
            r.raise_for_status()
            cd = r.headers.get("Content-Disposition", "")
            m = re.search(r'filename="?([^";]+)"?', cd)
            name = m.group(1).strip() if m else unquote(os.path.basename(r.url.split("?")[0]))
        except Exception:
            pass
        name = os.path.basename(name)
        name = sanitize(name)
        if not os.path.splitext(name)[1]:
            name = sanitize(label or "file")
        self._name_cache[url] = name
        return name


class App:
    def __init__(self, root):
        self.root = root
        root.title("KFU Moodle Downloader")
        root.geometry("980x720")
        self.msgs = queue.Queue()
        self.busy = False
        self.dl = None
        self._sems = []
        self._courses = []
        self.cur_files = []      # list of (url, label, name)
        self.file_vars = {}      # idx -> BooleanVar
        self.cookie = None

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        self.tab_sem = ttk.Frame(nb, padding=10)
        self._tab_sem_build()
        nb.add(self.tab_sem, text="Download by Semester")
        self.tab_course = ttk.Frame(nb, padding=10)
        self._tab_course_build()
        nb.add(self.tab_course, text="Pick Files in a Course")

        lf = ttk.Frame(root, padding=(10, 0, 10, 10))
        lf.pack(fill="both", expand=True)
        ttk.Label(lf, text="Log").pack(anchor="w")
        self.log = scrolledtext.ScrolledText(lf, height=11, wrap="none", state="disabled")
        self.log.pack(fill="both", expand=True)

        self.root.after(100, self._drain)

    # ---------- semester tab ----------
    def _tab_sem_build(self):
        f = self.tab_sem
        ttk.Label(f, text="MoodleSession cookie").grid(row=0, column=0, sticky="w")
        self.cookie = ttk.Entry(f, width=46)
        self.cookie.grid(row=0, column=1, sticky="we", padx=4, pady=2)
        ttk.Button(f, text="Check login", command=self.verify).grid(row=0, column=2, padx=4)
        r = 1
        ttk.Label(f, text="College").grid(row=r, column=0, sticky="w")
        self.college = ttk.Combobox(f, values=["medicine", "dental", "pharmacy"], state="readonly")
        self.college.set("medicine")
        self.college.grid(row=r, column=1, sticky="w", padx=4, pady=2)
        r += 1
        ttk.Label(f, text="Semesters (e.g. 1,2,3 / blank = all)").grid(row=r, column=0, sticky="w")
        self.sems = ttk.Entry(f, width=20)
        self.sems.grid(row=r, column=1, sticky="w", padx=4, pady=2)
        self.sems.insert(0, "all")
        r += 1
        ttk.Label(f, text="Output folder").grid(row=r, column=0, sticky="w")
        self.semout = ttk.Entry(f, width=46)
        self.semout.grid(row=r, column=1, sticky="we", padx=4, pady=2)
        self.semout.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.semout)).grid(row=r, column=2)
        r += 1
        self.sem_files_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Skip web/video pages (download files only)",
                        variable=self.sem_files_only).grid(row=r, column=1, sticky="w")
        r += 1
        ttk.Button(f, text="Start Semester Download",
                   command=self.start_semester).grid(row=r, column=1, sticky="w", pady=8)

    # ---------- course tab ----------
    def _tab_course_build(self):
        f = self.tab_course
        ttk.Label(f, text="College").grid(row=0, column=0, sticky="w")
        self.c_college = ttk.Combobox(f, values=["medicine", "dental", "pharmacy"], state="readonly")
        self.c_college.set("medicine")
        self.c_college.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Button(f, text="Load semesters", command=self.load_semesters).grid(row=0, column=2, padx=4)

        ttk.Label(f, text="Semester").grid(row=1, column=0, sticky="w")
        self.c_sem = ttk.Combobox(f, state="readonly", width=32)
        self.c_sem.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        self.c_sem.bind("<<ComboboxSelected>>", lambda e: self.load_courses())
        ttk.Button(f, text="Load courses", command=self.load_courses).grid(row=1, column=2, padx=4)

        ttk.Label(f, text="Course").grid(row=2, column=0, sticky="w")
        self.c_course = ttk.Combobox(f, state="readonly", width=52)
        self.c_course.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        self.c_course.bind("<<ComboboxSelected>>", lambda e: self.load_files())
        ttk.Button(f, text="Show files", command=self.load_files).grid(row=2, column=2, padx=4)

        ttk.Label(f, text="Output folder").grid(row=3, column=0, sticky="w")
        self.c_out = ttk.Entry(f, width=46)
        self.c_out.grid(row=3, column=1, sticky="we", padx=4, pady=2)
        self.c_out.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads"))
        ttk.Button(f, text="Browse", command=lambda: self._browse(self.c_out)).grid(row=3, column=2)

        ctr = ttk.Frame(f)
        ctr.grid(row=4, column=0, columnspan=3, sticky="w", pady=6)
        ttk.Button(ctr, text="Select All", command=lambda: self._toggle_all(True)).pack(side="left", padx=2)
        ttk.Button(ctr, text="Clear", command=lambda: self._toggle_all(False)).pack(side="left", padx=2)
        ttk.Label(ctr, text=" ").pack(side="left")
        ttk.Button(ctr, text="Download Selected", command=self.download_selected).pack(side="left", padx=6)

        self.lbl = ttk.Label(f, text="Choose a semester and course to see its files.")
        self.lbl.grid(row=5, column=0, columnspan=3, sticky="w")

        cols = ("check", "filename")
        self.tree = ttk.Treeview(f, columns=cols, show="tree headings", selectmode="none", height=12)
        self.tree.heading("check", text="")
        self.tree.heading("filename", text="File name")
        self.tree.column("check", width=40, anchor="center")
        self.tree.column("filename", width=600)
        self.tree.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=4)
        sb = ttk.Scrollbar(f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.grid(row=6, column=3, sticky="ns")
        f.rowconfigure(6, weight=1)
        f.columnconfigure(1, weight=1)
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")
        self.selection = set()

    # ---------- ui helpers ----------
    def _browse(self, entry):
        d = filedialog.askdirectory()
        if d:
            entry.delete(0, "end")
            entry.insert(0, d)

    def write(self, msg):
        self.msgs.put(msg)

    def _drain(self):
        try:
            while True:
                msg = self.msgs.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", msg + "\n")
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    def _run(self, fn):
        if self.busy:
            self.write("Task already running.")
            return
        self.busy = True
        threading.Thread(target=self._wrap, args=(fn,), daemon=True).start()

    def _wrap(self, fn):
        try:
            fn()
        except Exception as e:
            self.write(f"ERROR: {e}")
        finally:
            self.write("Done.")
            self.busy = False

    def _ensure_dl(self):
        cookie = self.cookie.get().strip()
        if not cookie:
            raise RuntimeError("Enter your cookie in the 'Download by Semester' tab first.")
        if self.dl is None:
            self.dl = Downloader(cookie)
        if not self.dl.check():
            raise RuntimeError("Cookie invalid/expired.")
        return self.dl

    # ---------- semester ----------
    def verify(self):
        cookie = self.cookie.get().strip()
        if not cookie:
            self.write("Enter a cookie first.")
            return
        self._run(lambda: self.write("Login valid." if Downloader(cookie).check()
                                     else "Cookie INVALID / expired."))

    def start_semester(self):
        cookie = self.cookie.get().strip()
        if not cookie:
            self.write("Enter a cookie first.")
            return
        out = self.semout.get().strip() or "downloads"
        save_all = not self.sem_files_only.get()

        def go():
            dl = Downloader(cookie)
            if not dl.check():
                self.write("Cookie invalid/expired.")
                return
            college = self.college.get().lower()
            cat = COLLEGE_BY_NAME[college]
            sems = dl.semesters(cat)
            want = [int(x) for x in self.sems.get().replace(" ", "").split(",") if x.strip().isdigit()]
            picked = [(c, t) for c, t in sems if sem_number(t) in want] if want else sems
            if not picked:
                self.write("No matching semesters found.")
                return
            for cat, title in picked:
                base = os.path.join(out, college.capitalize(), title)
                for cid, cname in dl.courses(cat):
                    self._dl_course(dl, cid, os.path.join(base, sanitize(cname)), save_all)
            self.write(f"All done -> {out}")

        self._run(go)

    # ---------- course browse ----------
    def load_semesters(self):
        def go():
            dl = self._ensure_dl()
            sems = dl.semesters(COLLEGE_BY_NAME[self.c_college.get().lower()])
            self.root.after(0, lambda: self._set_sems(sems))
        self._run(go)

    def _set_sems(self, sems):
        self._sems = sems
        self.c_sem.configure(values=[t for _, t in sems])
        if sems:
            self.c_sem.set(sems[0][1])

    def load_courses(self):
        sel = self.c_sem.get()
        if not sel or not self._sems:
            self.write("Pick a semester first.")
            return
        cat = next((c for c, t in self._sems if t == sel), None)
        if cat is None:
            return
        def go():
            dl = self._ensure_dl()
            courses = dl.courses(cat)
            self.root.after(0, lambda: self._set_courses(courses))
        self._run(go)

    def _set_courses(self, courses):
        self._courses = courses
        self.c_course.configure(values=[f"{cid}  {name}" for cid, name in courses])
        if courses:
            self.c_course.set(f"{courses[0][0]}  {courses[0][1]}")

    def load_files(self):
        txt = self.c_course.get()
        if not txt or not self._courses:
            self.write("Pick a course first.")
            return
        try:
            cid = int(txt.split()[0])
        except (ValueError, IndexError):
            self.write("Select a course from the list.")
            return
        def go():
            dl = self._ensure_dl()
            res = dl.resources(f"{BASE}/course/view.php?id={cid}")
            items = []
            for url, label in res:
                items.append((url, label, dl.resolve_name(url, label)))
            self.root.after(0, lambda: self._populate(items))
        self._run(go)

    def _populate(self, items):
        self.tree.delete(*self.tree.get_children())
        self.cur_files = items
        self.file_vars = {}
        for idx, (url, label, name) in enumerate(items):
            var = tk.BooleanVar(value=False)
            self.file_vars[idx] = var
            self.tree.insert("", "end", iid=str(idx), values=("[ ]", name))
        self.lbl.configure(
            text=f"{len(items)} file(s). Click a row (or its box) to tick it, then Download Selected.")

    def _toggle_all(self, val):
        mark = "[x]" if val else "[ ]"
        for idx, var in self.file_vars.items():
            var.set(val)
            self.tree.item(str(idx), values=(mark, self.cur_files[idx][2]))

    def _on_tree_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        idx = int(iid)
        var = self.file_vars[idx]
        var.set(not var.get())
        mark = "[x]" if var.get() else "[ ]"
        self.tree.item(iid, values=(mark, self.cur_files[idx][2]))

    def download_selected(self):
        if self.busy:
            self.write("Task already running.")
            return
        selected = [self.cur_files[i] for i, var in self.file_vars.items() if var.get()]
        if not selected:
            self.write("No files selected. Tick some first.")
            return
        out = self.c_out.get().strip() or "downloads"
        requests_to_run = [(url, name) for url, label, name in selected]

        def go():
            dl = self._ensure_dl()
            folder = os.path.join(out, "selected")
            os.makedirs(folder, exist_ok=True)
            self.write(f"Downloading {len(requests_to_run)} file(s) to {folder} ...")
            for url, name in requests_to_run:
                self._save_one(dl, url, folder)
            self.write("Finished selected download.")

        self._run(go)

    def _save_one(self, dl, url, folder):
        try:
            r = dl.s.get(url, timeout=180, allow_redirects=True)
            r.raise_for_status()
            cd = r.headers.get("Content-Disposition", "")
            m = re.search(r'filename="?([^";]+)"?', cd)
            name = m.group(1).strip() if m else unquote(os.path.basename(r.url.split("?")[0]))
            name = os.path.basename(name)
            name = sanitize(name)
            if not os.path.splitext(name)[1]:
                name = sanitize("file")
            path = os.path.join(folder, name)
            i = 1
            b, e = os.path.splitext(path)
            while os.path.exists(path):
                path = f"{b}_{i}{e}"
                i += 1
            with open(path, "wb") as fh:
                fh.write(r.content)
            self.write(f"    Saved: {os.path.basename(path)}")
        except Exception as e:
            self.write(f"    [error] {url}: {e}")

    # ---------- semester low-level ----------
    def _dl_course(self, dl, cid, folder, save_all):
        os.makedirs(folder, exist_ok=True)
        self.write(f"== {os.path.basename(folder)} (id={cid}) ==")
        try:
            res = dl.resources(f"{BASE}/course/view.php?id={cid}")
        except Exception as e:
            self.write(f"    [error loading course] {e}")
            return
        seen = set()
        for url, label in res:
            try:
                r = dl.s.get(url, timeout=180, allow_redirects=True)
                r.raise_for_status()
                if not save_all:
                    ctype = r.headers.get("Content-Type", "")
                    if "text/html" in ctype and b"<html" in r.content[:2000].lower():
                        self.write(f"    [skip html:{label}]")
                        continue
                cd = r.headers.get("Content-Disposition", "")
                m = re.search(r'filename="?([^";]+)"?', cd)
                name = m.group(1).strip() if m else unquote(os.path.basename(r.url.split("?")[0]))
                name = os.path.basename(name)
                name = sanitize(name)
                if not os.path.splitext(name)[1]:
                    name = sanitize(label or "file")
                path = os.path.join(folder, name)
                if path in seen or os.path.exists(path):
                    self.write(f"    [exists] {label}")
                    seen.add(path)
                    continue
                seen.add(path)
                with open(path, "wb") as fh:
                    fh.write(r.content)
                self.write(f"    Saved: {label}")
            except Exception as e:
                self.write(f"    [error] {url}: {e}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()