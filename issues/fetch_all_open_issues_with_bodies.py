import requests
import time
import sys

# Usage: python fetch_all_open_issues_with_bodies.py <owner> <repo> <per_page> <max_issues>
# Example: python fetch_all_open_issues_with_bodies.py adenhq hive 100 1000

OWNER = sys.argv[1] if len(sys.argv) > 1 else "adenhq"
REPO = sys.argv[2] if len(sys.argv) > 2 else "hive"
PER_PAGE = int(sys.argv[3]) if len(sys.argv) > 3 else 100
MAX_ISSUES = int(sys.argv[4]) if len(sys.argv) > 4 else 1000

GITHUB_API = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"
HEADERS = {"Accept": "application/vnd.github.v3+json"}

all_issues = []
page = 1

while True:
    params = {"state": "open", "per_page": PER_PAGE, "page": page}
    print(f"Fetching page {page}...")
    resp = requests.get(GITHUB_API, headers=HEADERS, params=params)
    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}")
        break
    issues = resp.json()
    if not issues:
        break
    for issue in issues:
        if "pull_request" not in issue:
            all_issues.append({
                "number": issue["number"],
                "title": issue["title"],
                "body": issue["body"] or ""
            })
    if len(issues) < PER_PAGE or len(all_issues) >= MAX_ISSUES:
        break
    page += 1
    time.sleep(1)

print(f"Fetched {len(all_issues)} issues.")
with open("issues/open_issues_full.json", "w") as f:
    import json
    json.dump(all_issues, f, indent=2)
print("Saved to issues/open_issues_full.json")
