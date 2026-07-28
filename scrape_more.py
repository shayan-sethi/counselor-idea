import urllib.request
import re
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prism_agent.opportunity_radar import CompeteMapScraper

def main():
    url = "https://competemap.com/competitions?country=INTERNATIONAL&subject=&q=&status=&month=&registration_method=&online_status=&min_age=&max_age=&sort=deadline"
    print(f"Fetching {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
        return
        
    links = set(re.findall(r'href="(/competitions/[^"?]+)"', html))
    print(f"Found {len(links)} competition links.")
    
    db_path = "data/competitions_db.json"
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            comps = json.load(f)
    else:
        comps = []
    
    existing_urls = {c.get("url") for c in comps if c.get("url")}
    
    new_comps = []
    for link in links:
        if "page=" in link:
            continue
        full_url = f"https://competemap.com{link}"
        if full_url in existing_urls:
            print(f"Skipping {full_url} (already exists)")
            continue
            
        print(f"Scraping {full_url}")
        comp = CompeteMapScraper.scrape_url(full_url)
        if comp:
            new_comps.append(comp)
            existing_urls.add(full_url)
            
    if new_comps:
        comps.extend(new_comps)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(comps, f, indent=2)
        print(f"Added {len(new_comps)} new competitions to {db_path}")
    else:
        print("No new competitions found.")

if __name__ == "__main__":
    main()
