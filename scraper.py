import os
import json
import time
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from deep_translator import GoogleTranslator
from notion_client import Client

# Configuration
BASE_URL = "https://yoasobi-heaven.com"
API_URL = f"{BASE_URL}/api/diary/diary-list/"
CSRF_URL = f"{BASE_URL}/api/csrf-token/"
IMAGE_DIR = "images"
DATA_FILE = "data_store.json"

# Headers mimicking a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

def load_params():
    """Load API parameters from local JSON file."""
    with open("params.json", "r") as f:
        return json.load(f)

def get_session():
    """Initialize session with Age Gate bypass and optional User Cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # 1. Base Age Gate Cookie (Always required)
    session.cookies.set("age_checked", "true", domain="yoasobi-heaven.com")
    
    # 2. User Authentication Cookies (for VIP content)
    # User can provide the raw cookie string directly from browser (e.g. "PHPSESSID=...; other=...")
    cookie_str = os.environ.get("YOASOBI_COOKIES")
    if cookie_str:
        print("Loading user cookies from environment...")
        try:
            for cookie in cookie_str.split(';'):
                if '=' in cookie:
                    k, v = cookie.strip().split('=', 1)
                    session.cookies.set(k, v, domain="yoasobi-heaven.com")
        except Exception as e:
            print(f"Error parsing cookies: {e}")
            
    return session

def get_csrf_token(session):
    """Fetch CSRF token from the API."""
    print("Fetching CSRF token...")
    try:
        response = session.get(CSRF_URL)
        response.raise_for_status()
        data = response.json()
        token = data.get("token")
        if not token:
            print("Error: Token not found in response")
            return None
        print(f"CSRF Token obtained: {token[:10]}...")
        return token
    except Exception as e:
        print(f"Failed to get CSRF token: {e}")
        return None

def fetch_diary_entries(session, token, params, page=1):
    """Fetch diary entries for a specific page."""
    print(f"Fetching diary entries (Page {page})...")
    params["page"] = page
    headers = {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": token
    }
    
    try:
        response = session.post(API_URL, json=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success"):
            print("API returned unsuccessful status")
            return []
            
        entries = data.get("diaryData", {}).get("diary_pc_page_data", [])
        print(f"Found {len(entries)} entries on page {page}.")
        return entries
    except Exception as e:
        print(f"Failed to fetch diary entries: {e}")
        return []

def download_image(url):
    """Download image and return local filename."""
    if not url:
        return None
    
    # Create persistent filename based on URL hash to avoid duplicates
    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = os.path.splitext(url)[1]
    if not ext:
        ext = ".jpg" # Default fallback
        
    filename = f"{url_hash}{ext}"
    filepath = os.path.join(IMAGE_DIR, filename)
    
    # Persistence check: Don't re-download if exists
    if os.path.exists(filepath):
        return filename
        
    print(f"Downloading image: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # Ensure directory exists
        os.makedirs(IMAGE_DIR, exist_ok=True)
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        return filename
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

def translate_text(text):
    """Translate Japanese text to Simplified Chinese using Google Translate (Deep Translator)."""
    if not text:
        return ""
    
    # Basic deduplication/cache check could go here
    
    try:
        # Use deep_translator for robust free translation
        translated = GoogleTranslator(source='auto', target='zh-CN').translate(text)
        return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text # Fallback to original

def process_and_save(entries):
    """Process entries, translate, download images, and prepare for Notion."""
    processed_data = []
    
    # Load previously processed IDs to avoid duplicates
    processed_ids = set()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                old_data = json.load(f)
                processed_ids = set(item["id"] for item in old_data)
        except:
            pass

    new_entries = []
    current_year = datetime.now().year
    
    for entry in entries:
        diary_id = entry.get("c_diary_id")
        
        if diary_id in processed_ids:
            print(f"Skipping duplicate entry {diary_id}")
            continue
            
        print(f"Processing new entry: {entry.get('subject')}")
        
        # 1. Download Image
        image_url = entry.get("girls_image_url")
        local_image_name = download_image(image_url)
        
        # 2. Content & Cookie Validation
        raw_text = entry.get("decoded_body_org", "") or entry.get("body", "")
        
        # Check for known "Member Only" placeholders
        if "マイガール登録" in raw_text or "Member Only" in raw_text:
             print("⚠️  WARNING: Member Only content detected! Your YOASOBI_COOKIES might be invalid or expired.")

        # Strip some HTML tags if needed, but translator handles plaintext best
        translated_text = translate_text(raw_text)
        
        # 3. Parse Date
        date_str = entry.get("create_date") # e.g. "12/28 17:00"
        timestamp = time.time()
        
        if date_str:
            try:
                # Parse as current year first
                dt = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d %H:%M")
                
                # If date is in the future (plus a small buffer), it must be from last year
                if dt > datetime.now() + requests.utils.timedelta(days=1):
                    dt = dt.replace(year=current_year - 1)
                
                timestamp = dt.timestamp()
            except Exception as e:
                print(f"Error parsing date '{date_str}': {e}")

        processed_entry = {
            "id": diary_id,
            "date": date_str,
            "title": entry.get("subject"),
            "original_text": raw_text,
            "translated_text": translated_text,
            "image_filename": local_image_name,
            "image_url_original": image_url,
            "timestamp": timestamp
        }
        
        new_entries.append(processed_entry)
        
    return new_entries

def upload_to_notion(entries):
    """Upload new entries to Notion database."""
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    
    if not token or not database_id:
        print("Notion credentials not found. Skipping upload.")
        return

    client = Client(auth=token)
    
    for entry in entries:
        try:
            print(f"Uploading to Notion: {entry['title']}")
            
            # Construct the proper GitHub raw URL for the image
            # Assumes the repo is public or the user has a way to view it. 
            # Ideally, this should be configurable.
            # Format: https://raw.githubusercontent.com/<user>/<repo>/main/images/<filename>
            # For now, we will just use the original URL if we can't construct a permanent one easily without more env vars
            # BUT the user specifically wanted persistent storage.
            # So we should use the raw github url.
            
            github_repo = os.environ.get("GITHUB_REPOSITORY") # "owner/repo"
            if github_repo:
                image_url = f"https://raw.githubusercontent.com/{github_repo}/main/images/{entry['image_filename']}"
            else:
                image_url = entry["image_url_original"] # Fallback

            client.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Date": {"date": {"start": datetime.fromtimestamp(entry["timestamp"]).isoformat()}},
                    "Title": {"title": [{"text": {"content": entry["title"]}}]},
                    "Content (JP)": {"rich_text": [{"text": {"content": entry["original_text"][:2000]}}]}, # Truncate if too long
                    "Content (CN)": {"rich_text": [{"text": {"content": entry["translated_text"][:2000]}}]},
                    "Original URL": {"url": entry["image_url_original"]},
                    "Image": {
                        "files": [
                            {
                                "name": entry["image_filename"],
                                "type": "external",
                                "external": {"url": image_url}
                            }
                        ]
                    }
                }
            )
            time.sleep(0.5) # Avoid rate limits
        except Exception as e:
            print(f"Failed to upload to Notion: {e}")

def fetch_all_entries(session, token, params, existing_ids):
    """Fetch all entries by paginating until no new data is found."""
    all_entries = []
    page = 1
    
    # Backfill mode: If True, we don't stop when we hit an existing ID.
    # We continue fetching until the API returns nothing.
    force_backfill = os.environ.get("BACKFILL", "false").lower() == "true"
    
    if force_backfill:
        print("BACKFILL mode enabled: Will scan all pages despite existing data.")
    
    while True:
        entries = fetch_diary_entries(session, token, params, page)
        if not entries:
            print("No more entries found. Stopping pagination.")
            break
            
        new_batch = []
        stop_signal = False
        
        for entry in entries:
            diary_id = str(entry.get("c_diary_id"))
            
            if diary_id in existing_ids:
                if not force_backfill:
                    print(f"Encountered existing entry {diary_id}. Stopping fetch (Standard Mode).")
                    stop_signal = True
                    break # Stop processing this page
                else:
                    # In backfill mode, just skip adding this one but continue the loop
                    continue
            
            new_batch.append(entry)
            
        # Check standard stop condition
        if stop_signal:
             break
             
        # If searching (Backfill or Empty/New Page), but we found no NEW entries on this page?
        # If backfill is on, we might find a page where ALL entries exist (e.g. page 1), but page 2 might have gaps?
        # Usually unlikely, but to be safe in backfill mode, we should ONLY stop if the API returns 0 items.
        # But if `new_batch` is empty AND we are NOT in stop_signal, it means all items on this page were duplicates.
        # If standard mode, we would have hit the break above.
        # If backfill mode, we should Keep Going because there might be gaps in history? 
        # Or usually if Page N is fully scraped, Page N+1 is likely scraped too. 
        # But let's be robust: In backfill, we keep going until API is empty.
        
        if new_batch:
            all_entries.extend(new_batch)
            print(f"Added {len(new_batch)} new entries from page {page}.")
        elif force_backfill:
             print(f"Page {page} processed (all duplicates), continuing to next page...")
        elif not new_batch:
            # If standard mode and no new entries (but didn't trip stop_signal??), break safety
            print("No new entries on this page. Stopping.")
            break

        page += 1
        time.sleep(1) # Be nice to the server
        
    return all_entries

if __name__ == "__main__":
    # 1. Setup
    params = load_params()
    session = get_session()
    
    # 2. Auth
    token = get_csrf_token(session)
    if not token:
        exit(1)

    # Load existing IDs to know when to stop
    existing_ids = set()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                old_data = json.load(f)
                existing_ids = set(str(item["id"]) for item in old_data)
        except:
            pass
        
    # 3. Fetch All
    entries = fetch_all_entries(session, token, params, existing_ids)
    
    # 4. Process (Download & Translate)
    # Note: process_and_save also checks duplicates, but our fetch loop does it to save API calls
    new_data = process_and_save(entries)
    
    if new_data:
        print(f"Successfully processed {len(new_data)} new entries.")
        
        # 5. Upload to Notion
        upload_to_notion(new_data)
        
        # Append to data store
        all_data = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                all_data = json.load(f)
        
        all_data.extend(new_data)
        
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
            
        print(f"Saved data to {DATA_FILE}")
    else:
        print("No new entries found.")
