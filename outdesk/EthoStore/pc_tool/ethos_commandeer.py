#!/usr/bin/env python3
"""
EthoS-Commandeer v2.0
Definitive GUI tool for Etho$tore catalog management
by SPDW Factory Lab

ULTRA-AUTOMATIC EDITION:
- Auto-process all apps (batch fetch from GitHub)
- Auto-scan all authors
- Download icons locally (optional)
- Progress bar for batch operations
- Enhanced image selector with preview
"""

import os
import sys
import json
import re
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from urllib.parse import urlparse, quote
import requests
from PIL import Image, ImageTk
import io
import shutil
from datetime import datetime

# ===== VERSION =====
APP_NAME = "EthoS-Commandeer"
VERSION = "2.0.0"
AUTHOR = "SPDW Factory Lab"

# ===== CONFIGURATION =====
IMGUR_CLIENT_ID = "YOUR_IMGUR_CLIENT_ID"      # https://api.imgur.com/oauth2/addclient
IMGBB_API_KEY = "YOUR_IMGBB_API_KEY"          # https://api.imgbb.com/
CATBOX_URL = "https://catbox.moe/user/api.php"

# Default file paths
DEFAULT_CATALOG = "db.json"
DEFAULT_OUTPUT = "db_enhanced.json"
AUTHORS_FILE = "authors.json"
CACHE_FILE = "github_cache.json"
ICON_CACHE_DIR = "icons"

# ===== IMAGE UPLOAD SERVICES =====
UPLOAD_SERVICES = {
    "Imgur": {
        "url": "https://api.imgur.com/3/upload",
        "headers": {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"},
        "file_key": "image",
        "response_url": lambda data: data["data"]["link"],
        "needs_key": True
    },
    "ImgBB": {
        "url": "https://api.imgbb.com/1/upload",
        "headers": {},
        "params": {"key": IMGBB_API_KEY},
        "file_key": "image",
        "response_url": lambda data: data["data"]["url"],
        "needs_key": True
    },
    "Catbox.moe": {
        "url": "https://catbox.moe/user/api.php",
        "headers": {},
        "params": {"reqtype": "fileupload"},
        "file_key": "fileToUpload",
        "response_url": lambda data: data.strip(),
        "needs_key": False
    }
}

# ===== CACHE MANAGEMENT =====
cache = {}
cache_loaded = False

def load_cache():
    global cache, cache_loaded
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        except:
            cache = {}
    cache_loaded = True

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def cache_get(key):
    if not cache_loaded:
        load_cache()
    return cache.get(key)

def cache_set(key, value):
    cache[key] = value
    save_cache()

# ===== GITHUB HELPERS =====
def get_repo_info(owner, repo):
    key = f"repo:{owner}/{repo}"
    cached = cache_get(key)
    if cached:
        return cached
    url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            info = {
                "default_branch": data.get("default_branch", "main"),
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "homepage": data.get("homepage"),
                "stargazers": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "open_issues": data.get("open_issues_count"),
                "license": data.get("license", {}).get("name") if data.get("license") else None,
                "topics": data.get("topics", []),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "pushed_at": data.get("pushed_at")
            }
            cache_set(key, info)
            return info
        return None
    except:
        return None

def get_latest_release(owner, repo):
    key = f"release:{owner}/{repo}"
    cached = cache_get(key)
    if cached:
        return cached
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            assets = []
            for asset in data.get("assets", []):
                name = asset["name"].lower()
                if name.endswith((".muxapp", ".zip", ".muxzip", ".muxthm", ".muxupd")):
                    assets.append({
                        "name": asset["name"],
                        "download_url": asset["browser_download_url"],
                        "size": asset["size"]
                    })
            info = {
                "version": data.get("tag_name", ""),
                "release_date": data.get("published_at", ""),
                "assets": assets,
                "html_url": data.get("html_url")
            }
            cache_set(key, info)
            return info
        return None
    except:
        return None

def get_repo_contents(owner, repo, path="", branch="main"):
    key = f"contents:{owner}/{repo}:{path}:{branch}"
    cached = cache_get(key)
    if cached:
        return cached
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            files = []
            for item in data:
                if item["type"] == "file":
                    files.append({
                        "name": item["name"],
                        "path": item["path"],
                        "download_url": item["download_url"]
                    })
                elif item["type"] == "dir":
                    # We'll fetch deeper when needed
                    pass
            cache_set(key, files)
            return files
        return None
    except:
        return None

def find_images_in_repo(owner, repo, branch="main"):
    """Find all image files in the repository."""
    images = []
    image_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.ico', '.gif', '.webp', '.bmp']
    directories_to_check = ["", "assets", "images", "img", "icons", "media", "screenshots", "artwork", "resources"]

    for subdir in directories_to_check:
        files = get_repo_contents(owner, repo, subdir, branch)
        if files:
            for f in files:
                if any(f["name"].lower().endswith(ext) for ext in image_extensions):
                    # Check if it might be an icon (by name)
                    icon_keywords = ["icon", "logo", "appicon", "app-icon", "badge", "avatar"]
                    is_icon = any(kw in f["name"].lower() for kw in icon_keywords)
                    images.append({
                        "name": f["name"],
                        "path": f["path"],
                        "url": f["download_url"],
                        "type": subdir if subdir else "root",
                        "is_icon": is_icon
                    })

    # Sort by priority: icons first, then by path depth (shallower first)
    images.sort(key=lambda x: (not x["is_icon"], x["path"].count("/")))
    return images

def get_readme(owner, repo, branch="main"):
    key = f"readme:{owner}/{repo}:{branch}"
    cached = cache_get(key)
    if cached:
        return cached
    for filename in ["README.md", "readme.md", "Readme.md", "README.MD"]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.text
                cache_set(key, content)
                return content
        except:
            pass
    return None

def extract_images_from_markdown(md_text):
    pattern = r'!\[.*?\]\((.*?)\)'
    matches = re.findall(pattern, md_text)
    filtered = []
    for url in matches:
        if "badge" in url.lower() or "shield" in url.lower() or "img.shields" in url.lower():
            continue
        if url.startswith(('http://', 'https://')):
            filtered.append(url)
    return filtered

def get_author_avatar(owner):
    key = f"user:{owner}"
    cached = cache_get(key)
    if cached:
        return cached
    url = f"https://api.github.com/users/{owner}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            avatar = data.get("avatar_url")
            cache_set(key, avatar)
            return avatar
        return None
    except:
        return None

def get_author_profile(owner):
    key = f"profile:{owner}"
    cached = cache_get(key)
    if cached:
        return cached
    url = f"https://api.github.com/users/{owner}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            profile = {
                "login": data.get("login"),
                "name": data.get("name"),
                "bio": data.get("bio"),
                "location": data.get("location"),
                "company": data.get("company"),
                "blog": data.get("blog"),
                "twitter": data.get("twitter_username"),
                "avatar_url": data.get("avatar_url"),
                "public_repos": data.get("public_repos"),
                "followers": data.get("followers"),
                "following": data.get("following"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at")
            }
            cache_set(key, profile)
            return profile
        return None
    except:
        return None

def parse_github_url(url):
    if not url or "github.com" not in url:
        return None, None
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    parts = path.split('/')
    if len(parts) < 2:
        return None, None
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo

def download_image(url, save_path):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
        return False
    except:
        return False

# ===== IMAGE UPLOAD FUNCTIONS =====
def upload_to_service(service_name, image_path):
    if service_name not in UPLOAD_SERVICES:
        raise Exception(f"Unknown service: {service_name}")
    config = UPLOAD_SERVICES[service_name]

    if config.get("needs_key", False):
        if service_name == "Imgur" and IMGUR_CLIENT_ID == "YOUR_IMGUR_CLIENT_ID":
            raise Exception("Please set your Imgur Client ID in the script.")
        if service_name == "ImgBB" and IMGBB_API_KEY == "YOUR_IMGBB_API_KEY":
            raise Exception("Please set your ImgBB API Key in the script.")

    try:
        with open(image_path, "rb") as f:
            files = {config["file_key"]: f}
            params = config.get("params", {}).copy()
            resp = requests.post(
                config["url"],
                headers=config["headers"],
                params=params,
                files=files,
                timeout=30
            )

        if resp.status_code in (200, 201):
            try:
                data = resp.json()
                return config["response_url"](data)
            except:
                return config["response_url"](resp.text)
        else:
            raise Exception(f"Upload failed: HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        raise Exception(f"Upload failed: {str(e)}")

# ===== MAIN APPLICATION =====
class EthosCommandeer:
    def __init__(self, root):
        self.root = root
        root.title(f"{APP_NAME} v{VERSION}")
        root.geometry("1300x750")
        root.minsize(1100, 650)

        # Data
        self.catalog = {}
        self.authors = {}
        self.apps_list = []
        self.current_app_index = -1
        self.filtered_indices = []
        self.current_author = None

        # Load cache
        load_cache()

        # Build UI
        self.create_menu()
        self.create_widgets()
        self.status("Ready. Load a catalog to start.")

    def create_menu(self):
        menubar = tk.Menu(self.root)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Catalog", command=self.load_catalog)
        filemenu.add_command(label="Save Catalog", command=self.save_catalog)
        filemenu.add_command(label="Save As...", command=self.save_catalog_as)
        filemenu.add_separator()
        filemenu.add_command(label="Export to GitHub", command=self.export_to_github)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        toolmenu = tk.Menu(menubar, tearoff=0)
        toolmenu.add_command(label="Auto-Process All Apps", command=self.auto_process_all)
        toolmenu.add_command(label="Scan All Authors", command=self.scan_all_authors)
        toolmenu.add_separator()
        toolmenu.add_command(label="Reload Catalog", command=self.reload_catalog)
        toolmenu.add_command(label="Clear Cache", command=self.clear_cache)
        toolmenu.add_command(label="Refresh Authors", command=self.refresh_authors)
        menubar.add_cascade(label="Tools", menu=toolmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.show_about)
        helpmenu.add_command(label="Documentation", command=self.show_docs)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.root.config(menu=menubar)

    def create_widgets(self):
        # Main paned window
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: app list + search + filter
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)

        # Search bar
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.filter_apps())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Filter frame
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, pady=5)

        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT, padx=5)
        self.cat_filter_var = tk.StringVar(value="All")
        self.cat_filter_combo = ttk.Combobox(filter_frame, textvariable=self.cat_filter_var, state="readonly", width=15)
        self.cat_filter_combo.pack(side=tk.LEFT, padx=5)
        self.cat_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_apps())

        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=(15,5))
        self.status_filter_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_filter_var, state="readonly", width=10)
        status_combo["values"] = ["All", "release", "testing", "sunset", "builtin", "wip", "legacy"]
        status_combo.pack(side=tk.LEFT, padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_apps())

        # App listbox
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, font=("TkFixedFont", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.bind("<<ListboxSelect>>", self.on_app_select)

        # App count
        self.app_count_label = ttk.Label(left_frame, text="0 apps")
        self.app_count_label.pack(pady=2)

        # Right panel: detail view (Notebook)
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=2)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: App Details
        self.detail_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.detail_tab, text="App Details")
        self.build_detail_tab()

        # Tab 2: Authors
        self.author_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.author_tab, text="Authors")
        self.build_author_tab()

        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

        # Progress bar (hidden by default)
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        self.progress_bar.pack_forget()

    def build_detail_tab(self):
        # Scrollable frame
        canvas = tk.Canvas(self.detail_tab, borderwidth=0)
        scrollbar = ttk.Scrollbar(self.detail_tab, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- Fields ----
        row = 0
        fields = [
            ("ID", "id", "entry"),
            ("Name", "name", "entry"),
            ("Glyph", "glyph", "entry"),
            ("Status", "status", "combo", ["release", "testing", "sunset", "builtin", "wip", "legacy"]),
            ("Author", "author", "entry"),
            ("Version", "version", "entry"),
            ("Release Date", "release_date", "entry"),
            ("Short Description", "short_desc", "entry"),
            ("Detailed Description", "detailed_desc", "text"),
            ("Download URL", "download_url", "entry"),
            ("Direct Download", "direct_download", "entry"),
            ("Source URL", "source_url", "entry"),
            ("Forum URL", "forum_url", "entry"),
            ("Install Path", "install_path", "entry"),
            ("File Type", "file_type", "combo", [".muxapp", ".muxzip", ".zip", ".muxthm", ".muxupd", ".sh", ".py", "N/A"]),
            ("License", "license", "combo", ["MIT", "GPL-2.0", "GPL-3.0", "Apache-2.0", "MPL-2.0", "BSD-3-Clause", "Unknown"]),
            ("Icon URL", "icon", "entry"),
            ("Author Avatar", "author_avatar", "entry"),
            ("Tags", "tags", "text"),
            ("muOS Compatibility", "muos_compatibility", "text"),
            ("Screenshots", "screenshots", "text"),
        ]

        self.entry_vars = {}
        self.entry_widgets = {}

        for label, key, widget_type, *args in fields:
            ttk.Label(scrollable_frame, text=f"{label}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)

            if widget_type == "combo":
                var = tk.StringVar()
                combo = ttk.Combobox(scrollable_frame, textvariable=var, state="readonly", width=40)
                combo["values"] = args[0] if args else []
                combo.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
                self.entry_vars[key] = var
                self.entry_widgets[key] = combo
            elif widget_type == "text":
                text = scrolledtext.ScrolledText(scrollable_frame, height=3, width=40)
                text.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
                self.entry_vars[key] = text
                self.entry_widgets[key] = text
            else:
                var = tk.StringVar()
                entry = ttk.Entry(scrollable_frame, textvariable=var, width=40)
                entry.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
                self.entry_vars[key] = var
                self.entry_widgets[key] = entry
            row += 1

        # ---- Action buttons ----
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Fetch from GitHub", command=self.fetch_from_github).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Upload Image", command=self.upload_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Apply Changes", command=self.apply_app_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh List", command=self.filter_apps).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Create New App", command=self.create_new_app).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=5)

        # Configure grid weights
        scrollable_frame.columnconfigure(1, weight=1)

    def build_author_tab(self):
        # Split into left (author list) and right (details)
        paned = ttk.PanedWindow(self.author_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        # Author list with search
        search_frame = ttk.Frame(left)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.author_search_var = tk.StringVar()
        self.author_search_var.trace("w", lambda *args: self.filter_authors())
        ttk.Entry(search_frame, textvariable=self.author_search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.author_listbox = tk.Listbox(left, selectmode=tk.SINGLE, font=("TkFixedFont", 10))
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.author_listbox.yview)
        self.author_listbox.config(yscrollcommand=scrollbar.set)
        self.author_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.author_listbox.bind("<<ListboxSelect>>", self.on_author_select)

        # Author detail frame
        self.author_detail_frame = ttk.Frame(right)
        self.author_detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Placeholder
        ttk.Label(self.author_detail_frame, text="Select an author to view details").pack()

    def status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def show_progress(self, show=True, value=0):
        if show:
            self.progress_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
            self.progress_var.set(value)
        else:
            self.progress_bar.pack_forget()
        self.root.update_idletasks()

    # ===== LOAD / SAVE =====
    def load_catalog(self, path=None):
        if not path:
            path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                initialfile=DEFAULT_CATALOG
            )
            if not path:
                return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.catalog = json.load(f)

            # Build flat list
            self.apps_list = []
            for cat_key, cat_data in self.catalog.get("macro_categories", {}).items():
                for app in cat_data.get("apps", []):
                    app["_category"] = cat_key
                    self.apps_list.append(app)

            # Load authors if exists
            if os.path.exists(AUTHORS_FILE):
                with open(AUTHORS_FILE, "r", encoding="utf-8") as f:
                    self.authors = json.load(f)

            # Update filter combos
            cats = ["All"] + list(self.catalog.get("macro_categories", {}).keys())
            self.cat_filter_combo["values"] = cats
            self.cat_filter_var.set("All")
            self.status_filter_var.set("All")

            self.filter_apps()
            self.refresh_author_list()
            self.status(f"Loaded {len(self.apps_list)} apps from {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load catalog: {e}")

    def save_catalog(self, path=None):
        if not path:
            path = filedialog.asksaveasfilename(
                filetypes=[("JSON files", "*.json")],
                initialfile=DEFAULT_OUTPUT
            )
            if not path:
                return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            self.status(f"Saved catalog to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save catalog: {e}")

    def save_catalog_as(self):
        self.save_catalog()

    def reload_catalog(self):
        if self.catalog:
            path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                initialfile=DEFAULT_CATALOG
            )
            if path:
                self.load_catalog(path)

    def clear_cache(self):
        if messagebox.askyesno("Clear Cache", "Delete all cached GitHub API data?"):
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
            global cache
            cache = {}
            self.status("Cache cleared")

    # ===== FILTER / LIST =====
    def filter_apps(self):
        search = self.search_var.get().lower().strip()
        cat_filter = self.cat_filter_var.get()
        status_filter = self.status_filter_var.get()

        self.listbox.delete(0, tk.END)
        self.filtered_indices = []

        for idx, app in enumerate(self.apps_list):
            name = app.get("name", "").lower()
            author = app.get("author", "").lower()
            status = app.get("status", "")

            if search:
                if search not in name and search not in author:
                    continue

            if cat_filter != "All" and app.get("_category") != cat_filter:
                continue

            if status_filter != "All" and status != status_filter:
                continue

            self.filtered_indices.append(idx)
            display = f"{app.get('name', 'Unknown')} - {app.get('author', '?')}"
            self.listbox.insert(tk.END, display)

        self.app_count_label.config(text=f"{len(self.filtered_indices)} apps")

    def on_app_select(self, event):
        # Support for multiple selection? We'll just display the first selected
        selection = self.listbox.curselection()
        if not selection:
            return
        list_index = selection[0]
        if list_index >= len(self.filtered_indices):
            return
        app_idx = self.filtered_indices[list_index]
        self.current_app_index = app_idx
        self.display_app(app_idx)

    def display_app(self, idx):
        app = self.apps_list[idx]
        for key, var in self.entry_vars.items():
            val = app.get(key, "")
            if key in ["screenshots", "tags", "muos_compatibility", "detailed_desc"]:
                if isinstance(val, list):
                    val = "\n".join(val)
                var.delete("1.0", tk.END)
                var.insert("1.0", val)
            else:
                var.set(str(val) if val is not None else "")

    def apply_app_changes(self):
        if self.current_app_index < 0:
            messagebox.showinfo("Info", "Select an app first.")
            return

        app = self.apps_list[self.current_app_index]

        for key, var in self.entry_vars.items():
            if key in ["screenshots", "tags", "muos_compatibility", "detailed_desc"]:
                text = var.get("1.0", tk.END).strip()
                if text:
                    items = [line.strip() for line in text.split("\n") if line.strip()]
                    app[key] = items if items else []
                else:
                    app[key] = []
            else:
                val = var.get().strip()
                if val:
                    app[key] = val
                else:
                    app[key] = ""

        # Update in catalog
        cat_key = app.get("_category")
        if cat_key and cat_key in self.catalog.get("macro_categories", {}):
            cat_apps = self.catalog["macro_categories"][cat_key]["apps"]
            for i, a in enumerate(cat_apps):
                if a.get("id") == app.get("id"):
                    cat_apps[i] = app
                    break

        self.status("App updated.")
        self.filter_apps()

    def create_new_app(self):
        if not self.catalog:
            messagebox.showinfo("Info", "Load a catalog first.")
            return

        cats = list(self.catalog.get("macro_categories", {}).keys())
        if not cats:
            messagebox.showinfo("Info", "No categories found in catalog.")
            return

        cat = tk.simpledialog.askstring("New App", "Category:", initialvalue=cats[0] if cats else "")
        if not cat or cat not in self.catalog["macro_categories"]:
            return

        app_id = tk.simpledialog.askstring("New App", "App ID (unique):")
        if not app_id:
            return

        for existing in self.apps_list:
            if existing.get("id") == app_id:
                messagebox.showerror("Error", f"App with ID '{app_id}' already exists.")
                return

        new_app = {
            "id": app_id,
            "name": "New App",
            "glyph": "📦",
            "status": "testing",
            "author": "unknown",
            "version": "0.1.0",
            "short_desc": "New app description",
            "detailed_desc": "",
            "download_url": "",
            "direct_download": "",
            "source_url": "",
            "forum_url": "",
            "install_path": "/ARCHIVE",
            "file_type": ".muxapp",
            "license": "Unknown",
            "icon": "",
            "author_avatar": "",
            "tags": [],
            "muos_compatibility": ["All"],
            "screenshots": [],
            "_category": cat
        }

        self.catalog["macro_categories"][cat]["apps"].append(new_app)
        self.apps_list.append(new_app)

        self.filter_apps()
        self.current_app_index = len(self.apps_list) - 1
        self.display_app(self.current_app_index)
        self.status(f"Created new app: {app_id}")

    def delete_selected(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select one or more apps (Ctrl+click).")
            return

        if not messagebox.askyesno("Delete Apps", f"Delete {len(selection)} selected app(s)?"):
            return

        # Collect app indices to delete (from filtered list)
        indices_to_delete = [self.filtered_indices[i] for i in selection]
        # Sort descending to avoid index shifting
        indices_to_delete.sort(reverse=True)

        for idx in indices_to_delete:
            app = self.apps_list[idx]
            cat_key = app.get("_category")
            if cat_key and cat_key in self.catalog.get("macro_categories", {}):
                cat_apps = self.catalog["macro_categories"][cat_key]["apps"]
                self.catalog["macro_categories"][cat_key]["apps"] = [
                    a for a in cat_apps if a.get("id") != app.get("id")
                ]
            self.apps_list.pop(idx)

        self.filter_apps()
        self.current_app_index = -1
        self.status(f"Deleted {len(selection)} apps.")

    # ===== FETCH FROM GITHUB (SINGLE) =====
    def fetch_from_github(self):
        if self.current_app_index < 0:
            messagebox.showinfo("Info", "Select an app first.")
            return

        app = self.apps_list[self.current_app_index]
        repo_url = app.get("source_url") or app.get("download_url")

        if not repo_url or "github.com" not in repo_url:
            messagebox.showinfo("Info", "No GitHub URL found for this app.\nPlease set 'Source URL' or 'Download URL' first.")
            return

        owner, repo = parse_github_url(repo_url)
        if not owner or not repo:
            messagebox.showerror("Error", "Could not parse GitHub URL.")
            return

        def fetch():
            self.status(f"Fetching from {owner}/{repo} ...")
            try:
                self._process_app(app, owner, repo)
                self.display_app(self.current_app_index)
                self.save_authors()
                self.refresh_author_list()
                self.status("Fetch completed successfully.")
            except Exception as e:
                self.status(f"Error: {e}")
                messagebox.showerror("Error", str(e))

        threading.Thread(target=fetch, daemon=True).start()

    def _process_app(self, app, owner, repo):
        """Internal method to process a single app (used by batch too)"""
        # Get repo info
        repo_info = get_repo_info(owner, repo)
        branch = repo_info.get("default_branch", "main") if repo_info else "main"

        # Get latest release
        release = get_latest_release(owner, repo)
        if release:
            if release.get("version"):
                app["version"] = release["version"]
            if release.get("release_date"):
                app["release_date"] = release["release_date"][:10]
            for asset in release.get("assets", []):
                if asset["name"].lower().endswith((".muxapp", ".muxzip", ".zip")):
                    app["direct_download"] = asset["download_url"]
                    break
            if not app.get("direct_download") and release.get("html_url"):
                app["download_url"] = release["html_url"]

        # Find images in repo
        images = find_images_in_repo(owner, repo, branch)
        if images:
            # Find best icon
            icon_candidates = [img for img in images if img.get("is_icon")]
            if icon_candidates:
                app["icon"] = icon_candidates[0]["url"]
            else:
                # Use first image
                app["icon"] = images[0]["url"]

            # Add some images as screenshots (up to 5)
            screenshot_urls = []
            for img in images:
                if img["url"] != app.get("icon") and len(screenshot_urls) < 5:
                    screenshot_urls.append(img["url"])
            if screenshot_urls:
                current_ss = app.get("screenshots", [])
                for url in screenshot_urls:
                    if url not in current_ss:
                        current_ss.append(url)
                app["screenshots"] = current_ss

        # Get README images for screenshots
        readme = get_readme(owner, repo, branch)
        if readme:
            md_images = extract_images_from_markdown(readme)
            if md_images:
                current_ss = app.get("screenshots", [])
                for url in md_images[:5]:
                    if url not in current_ss:
                        current_ss.append(url)
                app["screenshots"] = current_ss

        # Author avatar
        avatar = get_author_avatar(owner)
        if avatar:
            app["author_avatar"] = avatar

        # Update author profile
        if owner not in self.authors:
            profile = get_author_profile(owner)
            if profile:
                profile["apps"] = []
                self.authors[owner] = profile
        if owner in self.authors:
            existing = [a for a in self.authors[owner].get("apps", []) if a.get("id") == app.get("id")]
            if not existing:
                self.authors[owner]["apps"].append({
                    "id": app.get("id"),
                    "name": app.get("name"),
                    "category": app.get("_category")
                })

    # ===== BATCH PROCESS =====
    def auto_process_all(self):
        if not self.apps_list:
            messagebox.showinfo("Info", "No apps loaded.")
            return

        # Count apps with GitHub URL
        github_apps = []
        for app in self.apps_list:
            repo_url = app.get("source_url") or app.get("download_url")
            if repo_url and "github.com" in repo_url:
                github_apps.append(app)

        if not github_apps:
            messagebox.showinfo("Info", "No apps with GitHub URL found.")
            return

        if not messagebox.askyesno("Auto-Process", f"Process {len(github_apps)} apps with GitHub URLs?\n\nThis may take a while."):
            return

        def process():
            self.status("Batch processing started...")
            self.show_progress(True, 0)
            total = len(github_apps)
            processed = 0
            failed = 0

            for app in github_apps:
                try:
                    repo_url = app.get("source_url") or app.get("download_url")
                    owner, repo = parse_github_url(repo_url)
                    if owner and repo:
                        self._process_app(app, owner, repo)
                    processed += 1
                except Exception as e:
                    failed += 1
                    print(f"Error processing {app.get('name')}: {e}")

                progress = int((processed + failed) / total * 100)
                self.show_progress(True, progress)
                self.status(f"Processed {processed+failed}/{total} apps ({failed} failed)")

            # Save everything
            self.save_authors()
            self.refresh_author_list()
            self.filter_apps()
            self.show_progress(False)
            self.status(f"Batch completed: {processed} apps updated, {failed} failed.")
            messagebox.showinfo("Batch Complete", f"Updated {processed} apps.\n{failed} apps had errors.")

        threading.Thread(target=process, daemon=True).start()

    # ===== SCAN ALL AUTHORS =====
    def scan_all_authors(self):
        if not self.apps_list:
            messagebox.showinfo("Info", "No apps loaded.")
            return

        # Collect all unique author names
        authors = set()
        for app in self.apps_list:
            author = app.get("author")
            if author:
                authors.add(author)

        if not authors:
            messagebox.showinfo("Info", "No authors found in catalog.")
            return

        if not messagebox.askyesno("Scan Authors", f"Scan {len(authors)} authors?\n\nThis will fetch GitHub profiles for all unique author names."):
            return

        def scan():
            self.status("Scanning authors...")
            self.show_progress(True, 0)
            total = len(authors)
            processed = 0
            failed = 0

            for author in authors:
                try:
                    # Check if author is likely a GitHub username
                    # We'll try to get profile anyway
                    profile = get_author_profile(author)
                    if profile:
                        # Merge with existing data
                        if author not in self.authors:
                            self.authors[author] = profile
                            self.authors[author]["apps"] = []
                        else:
                            # Update fields
                            for key, val in profile.items():
                                if val:
                                    self.authors[author][key] = val
                        # Also fetch avatar
                        avatar = get_author_avatar(author)
                        if avatar:
                            self.authors[author]["avatar_url"] = avatar
                        processed += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    print(f"Error scanning {author}: {e}")

                progress = int((processed + failed) / total * 100)
                self.show_progress(True, progress)
                self.status(f"Scanned {processed+failed}/{total} authors ({failed} failed)")

            self.save_authors()
            self.refresh_author_list()
            self.show_progress(False)
            self.status(f"Author scan completed: {processed} profiles updated, {failed} failed.")
            messagebox.showinfo("Scan Complete", f"Updated {processed} author profiles.\n{failed} authors not found on GitHub.")

        threading.Thread(target=scan, daemon=True).start()

    # ===== IMAGE UPLOAD =====
    def upload_image(self):
        # Service selection dialog
        service_dialog = tk.Toplevel(self.root)
        service_dialog.title("Choose Image Host")
        service_dialog.geometry("350x180")
        service_dialog.transient(self.root)
        service_dialog.grab_set()

        ttk.Label(service_dialog, text="Select upload service:", font=("TkDefaultFont", 10)).pack(pady=10)

        service_var = tk.StringVar(value="Imgur")
        combo = ttk.Combobox(
            service_dialog,
            textvariable=service_var,
            values=list(UPLOAD_SERVICES.keys()),
            state="readonly",
            width=20
        )
        combo.pack(pady=5)

        info_label = ttk.Label(service_dialog, text="", foreground="gray")
        info_label.pack(pady=5)

        def update_info(*args):
            service = service_var.get()
            config = UPLOAD_SERVICES.get(service, {})
            needs_key = config.get("needs_key", False)
            if needs_key:
                info_label.config(text="⚠️ This service requires an API key set in the script.")
            else:
                info_label.config(text="✅ No API key required (anonymous upload).")

        update_info()
        combo.bind("<<ComboboxSelected>>", update_info)

        def do_upload():
            service = service_var.get()
            if service not in UPLOAD_SERVICES:
                return

            path = filedialog.askopenfilename(
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico *.webp *.svg")]
            )
            if not path:
                return
            service_dialog.destroy()

            try:
                self.status(f"Uploading to {service}...")
                url = upload_to_service(service, path)
                self.status(f"Uploaded: {url}")

                choice = messagebox.askquestion("Use as", "Use as Icon?", icon='question')
                if choice == 'yes':
                    app = self.apps_list[self.current_app_index]
                    app["icon"] = url
                    self.display_app(self.current_app_index)
                    self.status("Icon updated.")
                else:
                    if messagebox.askyesno("Add to Screenshots", "Add to screenshots?"):
                        app = self.apps_list[self.current_app_index]
                        screenshots = app.get("screenshots", [])
                        if url not in screenshots:
                            screenshots.append(url)
                            app["screenshots"] = screenshots
                            self.display_app(self.current_app_index)
                            self.status("Screenshot added.")
                        else:
                            self.status("URL already in screenshots.")
                    else:
                        if messagebox.askyesno("Use as Avatar", "Use as Author Avatar?"):
                            app = self.apps_list[self.current_app_index]
                            app["author_avatar"] = url
                            self.display_app(self.current_app_index)
                            self.status("Author avatar updated.")

            except Exception as e:
                messagebox.showerror("Upload Error", str(e))
                self.status(f"Upload failed: {e}")

        ttk.Button(service_dialog, text="Select Image & Upload", command=do_upload).pack(pady=10)
        ttk.Button(service_dialog, text="Cancel", command=service_dialog.destroy).pack(pady=5)

    # ===== AUTHORS =====
    def save_authors(self):
        try:
            with open(AUTHORS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.authors, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.status(f"Failed to save authors: {e}")

    def refresh_authors(self):
        self.refresh_author_list()

    def filter_authors(self):
        search = self.author_search_var.get().lower()
        self.author_listbox.delete(0, tk.END)
        for login, profile in self.authors.items():
            name = profile.get("name") or login
            if search and search not in name.lower() and search not in login.lower():
                continue
            self.author_listbox.insert(tk.END, f"{name} ({login})")

    def refresh_author_list(self):
        self.author_listbox.delete(0, tk.END)
        for login, profile in self.authors.items():
            name = profile.get("name") or login
            self.author_listbox.insert(tk.END, f"{name} ({login})")

    def on_author_select(self, event):
        sel = self.author_listbox.curselection()
        if not sel:
            return
        text = self.author_listbox.get(sel[0])
        login = text.split("(")[-1].rstrip(")")
        self.display_author(login)

    def display_author(self, login):
        profile = self.authors.get(login, {})
        for widget in self.author_detail_frame.winfo_children():
            widget.destroy()

        if not profile:
            ttk.Label(self.author_detail_frame, text="No profile data for this author.").pack()
            return

        canvas = tk.Canvas(self.author_detail_frame, borderwidth=0)
        scrollbar = ttk.Scrollbar(self.author_detail_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Avatar
        avatar_url = profile.get("avatar_url")
        if avatar_url:
            try:
                resp = requests.get(avatar_url, timeout=10)
                img = Image.open(io.BytesIO(resp.content))
                img.thumbnail((100, 100))
                photo = ImageTk.PhotoImage(img)
                lbl = ttk.Label(scrollable_frame, image=photo)
                lbl.image = photo
                lbl.pack(pady=5)
            except:
                pass

        fields = [
            ("Login", "login"),
            ("Name", "name"),
            ("Bio", "bio"),
            ("Location", "location"),
            ("Company", "company"),
            ("Blog", "blog"),
            ("Twitter", "twitter"),
            ("Followers", "followers"),
            ("Following", "following"),
            ("Public Repos", "public_repos"),
            ("Joined", "created_at"),
            ("Last Updated", "updated_at")
        ]

        for label, key in fields:
            val = profile.get(key, "")
            if val:
                frame = ttk.Frame(scrollable_frame)
                frame.pack(fill=tk.X, pady=2)
                ttk.Label(frame, text=f"{label}:", font=("TkDefaultFont", 9, "bold"), width=12).pack(side=tk.LEFT)
                ttk.Label(frame, text=str(val), wraplength=300).pack(side=tk.LEFT, padx=5)

        ttk.Label(scrollable_frame, text="Apps by this author:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W, pady=(10,5))

        apps = profile.get("apps", [])
        if apps:
            for app in apps:
                app_name = app.get("name", "Unknown")
                cat = app.get("category", "")
                ttk.Label(scrollable_frame, text=f"  • {app_name} ({cat})").pack(anchor=tk.W)
        else:
            ttk.Label(scrollable_frame, text="  No apps associated yet.").pack(anchor=tk.W)

        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Edit Profile", command=lambda: self.edit_author(login)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=lambda: self.display_author(login)).pack(side=tk.LEFT, padx=5)

    def edit_author(self, login):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Author: {login}")
        dialog.geometry("500x450")
        dialog.transient(self.root)
        dialog.grab_set()

        profile = self.authors.get(login, {})
        fields = ["name", "bio", "location", "company", "blog", "twitter"]
        entries = {}

        canvas = tk.Canvas(dialog, borderwidth=0)
        scrollbar = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for i, key in enumerate(fields):
            ttk.Label(scrollable_frame, text=key.capitalize()).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            var = tk.StringVar(value=profile.get(key, ""))
            entry = ttk.Entry(scrollable_frame, textvariable=var, width=40)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[key] = var

        def save():
            for key, var in entries.items():
                profile[key] = var.get().strip()
            self.authors[login] = profile
            self.save_authors()
            self.display_author(login)
            dialog.destroy()
            self.status(f"Author {login} updated.")

        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    # ===== EXPORT =====
    def export_to_github(self):
        messagebox.showinfo("Coming Soon", """
        GitHub export will be implemented in the next version.

        For now, you can:
        1. Save the catalog locally (File → Save Catalog)
        2. Manually push to your GitHub repository

        Future version will support:
        - Direct push with personal access token
        - Commit message and file selection
        """)

    # ===== ABOUT =====
    def show_about(self):
        messagebox.showinfo("About",
            f"{APP_NAME} v{VERSION}\n\n"
            f"Definitive GUI tool for Etho$tore catalog management.\n"
            f"by {AUTHOR}\n\n"
            f"ULTRA-AUTOMATIC EDITION\n\n"
            f"• Auto-process all apps (batch fetch from GitHub)\n"
            f"• Auto-scan all authors\n"
            f"• Download icons locally (optional)\n"
            f"• Progress bar for batch operations\n"
            f"• Enhanced image selector with preview\n\n"
            f"Requires Python 3.6+ with Pillow and requests"
        )

    def show_docs(self):
        docs = """
        EthoS-Commandeer v2.0 - User Guide

        1. LOADING A CATALOG
           File → Open Catalog → select your db.json

        2. VIEWING APPS
           - Search by name or author (top-left)
           - Filter by category or status
           - Click an app to view/edit its details

        3. AUTO-PROCESS ALL APPS (NEW)
           Tools → Auto-Process All Apps
           - Scans every app with a GitHub URL
           - Updates version, release date, direct download
           - Finds icon (searches entire repo)
           - Finds screenshots (from README and image folders)
           - Updates author avatar and profile
           - Progress bar shows status
           - No manual confirmation needed

        4. SCAN ALL AUTHORS (NEW)
           Tools → Scan All Authors
           - Fetches GitHub profiles for all authors
           - Updates bio, location, company, etc.
           - Downloads avatars

        5. EDITING AN APP
           - Edit any field directly
           - "Apply Changes" saves to memory
           - "Save Catalog" writes to disk

        6. IMAGE UPLOAD
           - Click "Upload Image"
           - Choose service (Imgur, ImgBB, Catbox)
           - Select image file
           - Choose where to use it (Icon, Screenshot, or Avatar)

        7. DELETE APPS
           - Select one or more apps (Ctrl+click)
           - Click "Delete Selected"
           - Confirm deletion

        8. CACHE
           - GitHub API calls are cached for speed
           - Tools → Clear Cache to refresh

        9. SAVING
           - File → Save Catalog (overwrites current)
           - File → Save As... (save to new file)
        """
        messagebox.showinfo("Documentation", docs)

# ===== MAIN =====
def main():
    try:
        import requests
        import PIL
    except ImportError:
        print("ERROR: Missing required packages.")
        print("Please install: pip install Pillow requests")
        sys.exit(1)

    root = tk.Tk()
    app = EthosCommandeer(root)

    if os.path.exists(DEFAULT_CATALOG):
        app.load_catalog(DEFAULT_CATALOG)

    root.mainloop()

if __name__ == "__main__":
    main()