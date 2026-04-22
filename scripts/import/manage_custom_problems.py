#!/usr/bin/env python3
"""List and optionally delete custom problems from QDUOJ."""
import requests
import sys

OJ_URL = "http://localhost:8000"

def main():
    s = requests.Session()
    s.get(f"{OJ_URL}/api/profile")
    csrf = s.cookies.get("csrftoken", "")
    s.post(f"{OJ_URL}/api/login", json={"username": "root", "password": "rootroot"},
           headers={"X-CSRFToken": csrf})
    csrf = s.cookies.get("csrftoken", csrf)

    # Get all problems
    all_problems = []
    page = 1
    while True:
        r = s.get(f"{OJ_URL}/api/admin/problem?limit=50&page={page}",
                   headers={"X-CSRFToken": csrf})
        d = r.json()
        if d.get("error") is not None:
            break
        results = d["data"]["results"]
        if not results:
            break
        all_problems.extend(results)
        page += 1

    print(f"Total problems: {len(all_problems)}")

    # Find custom- problems (created by our script)
    custom = [p for p in all_problems if p["_id"].startswith("custom-")]
    print(f"Custom problems: {len(custom)}")
    for p in custom:
        print(f"  id={p['id']} _id={p['_id']} title={p['title']}")

    if "--delete" in sys.argv and custom:
        print("\nDeleting custom problems...")
        for p in custom:
            r = s.delete(f"{OJ_URL}/api/admin/problem?id={p['id']}",
                          headers={"X-CSRFToken": csrf})
            status = "OK" if r.json().get("error") is None else "FAIL"
            print(f"  Deleted id={p['id']}: {status}")
        print("Done.")

if __name__ == "__main__":
    main()