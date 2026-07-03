import urllib.request
import json
import pandas as pd
import time
import sys

def get_token():
    print("Fetching GameDay API token...")
    token_url = 'https://cxm-api.fifa.com/fifaplusweb/api/external/gameDay/token'
    req = urllib.request.Request(token_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            return data['token']
    except Exception as e:
        print(f"Failed to fetch token: {e}")
        sys.exit(1)

def fetch_category_page(cat, page, token):
    url = f"https://gameday-prod.fifa.mangodev.co.uk/1-0/stories?query=(and%20resourceStatus==%60urn:gd:resourceStatus:active%60%20_externalId~%60urn:gd:story:classification:{cat}:competitionId:285023:(.*):rank_asc:page:{page}$%60)&skip=0&limit=1&sort=tags.name==urn:gd:tag:story:fifa:column_number:asc"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Authorization': f'Bearer {token}'
    })
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            items = data.get('items', [])
            if items:
                return items[0]
    except Exception as e:
        print(f"Error fetching {cat} page {page}: {e}")
    return None

def clean_tag_name(name):
    # urn:gd:tag:football:stats:goals -> goals
    if name.startswith("urn:gd:tag:football:stats:"):
        return name.replace("urn:gd:tag:football:stats:", "")
    if name.startswith("urn:gd:tag:story:staff:"):
        return name.replace("urn:gd:tag:story:staff:", "")
    if name.startswith("urn:gd:tag:story:team:"):
        return name.replace("urn:gd:tag:story:team:", "")
    return name

def main():
    token = get_token()
    
    categories = {
        'gcp_top_scorer': 25,
        'gcp_attack': 25,
        'gcp_distribution': 25,
        'gcp_defending': 25,
        'gcp_discipline': 25,
        'gcp_goalkeeping': 3,
        'gcp_movement': 25,
        'gcp_physical': 25
    }
    
    player_data = {}
    
    for cat, max_pages in categories.items():
        print(f"Scraping category: {cat}...")
        for page in range(1, max_pages + 1):
            print(f"  Page {page}/{max_pages}...")
            item = fetch_category_page(cat, page, token)
            if not item:
                print(f"    No data or error on page {page}. Stopping category.")
                break
                
            actors = item.get('actors', [])
            if not actors:
                print(f"    No players on page {page}. Stopping category.")
                break
                
            for actor in actors:
                key = actor.get('key', {})
                pid = key.get('_externalSportsPersonId')
                if not pid:
                    continue
                    
                name = actor.get('name', {}).get('eng', '')
                
                # Extract tags
                tags = actor.get('tags', [])
                extracted = {
                    'name': name,
                    'sports_person_id': pid,
                    'team_id': key.get('_externalTeamId', '')
                }
                
                for t in tags:
                    tname = t.get('name', '')
                    tval = t.get('value')
                    
                    # Clean up common tags
                    if tname == 'urn:gd:tag:story:staff:image':
                        extracted['headshot_url'] = tval
                    elif tname == 'urn:gd:tag:story:team:abbreviation':
                        extracted['team_abbr'] = tval
                    elif tname == 'urn:gd:tag:story:team:image':
                        extracted['flag_url'] = tval
                    elif tname == 'urn:gd:tag:story:team:name:eng':
                        extracted['team_name'] = tval
                    elif tname == 'urn:gd:tag:story:staff:position':
                        extracted['position'] = tval
                    elif tname == 'urn:gd:tag:story:staff:position:description:eng':
                        extracted['position_desc'] = tval
                    elif tname.startswith('urn:gd:tag:football:stats:'):
                        stat_name = clean_tag_name(tname)
                        extracted[stat_name] = tval
                        
                if pid not in player_data:
                    player_data[pid] = extracted
                else:
                    # Update stats
                    player_data[pid].update(extracted)
                    
            time.sleep(0.1) # short pause to avoid rate limiting
            
    print(f"Total unique players scraped: {len(player_data)}")
    
    # Convert to DataFrame and save
    df = pd.DataFrame(list(player_data.values()))
    
    # Reorder columns to put main info first
    info_cols = ['sports_person_id', 'name', 'team_abbr', 'team_name', 'position', 'position_desc', 'team_id', 'headshot_url', 'flag_url']
    other_cols = [c for c in df.columns if c not in info_cols]
    df = df[info_cols + sorted(other_cols)]
    
    output_file = 'fifa_world_cup_2026_player_stats.csv'
    df.to_csv(output_file, index=False)
    print(f"Saved database to {output_file}")
    
    # Save a JSON file as well for richer nested representations or easy Dash consumption
    df.to_json('fifa_world_cup_2026_player_stats.json', orient='records', indent=2)
    print("Saved database to fifa_world_cup_2026_player_stats.json")

if __name__ == "__main__":
    main()
