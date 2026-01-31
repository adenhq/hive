import json
import os
import re

def normalize(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())

# Load open issues from GitHub export
with open("issues/open_issues_full.json") as f:
    open_issues = json.load(f)
open_titles = set(normalize(issue["title"]) for issue in open_issues)
open_bodies = set(normalize(issue["body"]) for issue in open_issues)

# List all local issue markdown files
local_dir = "issues"
local_files = [f for f in os.listdir(local_dir) if f.endswith(".md")]

duplicates = []
for fname in local_files:
    with open(os.path.join(local_dir, fname)) as f:
        content = f.read()
    # Extract title (first non-empty line, ignoring markdown headers)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    title = ""
    for l in lines:
        if l.startswith("#"):
            title = l.lstrip("# ")
            break
    norm_title = normalize(title)
    norm_body = normalize(content)
    if norm_title in open_titles or norm_body in open_bodies:
        duplicates.append(fname)

if duplicates:
    print("Duplicate local issues found:")
    for d in duplicates:
        print("  ", d)
        os.remove(os.path.join(local_dir, d))
    print(f"Deleted {len(duplicates)} duplicate local issues.")
else:
    print("No duplicate local issues found.")
