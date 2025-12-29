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

def download_file(url, folder="images"):
    """Download file and return filename if successful."""
    if not url:
        return None
        
    try:
        # Create folder if not exists
        if not os.path.exists(folder):
            os.makedirs(folder)
            
        filename = os.path.basename(url.split("?")[0]) # Handle query params
        filepath = os.path.join(folder, filename)
        
        # Helper to check if valid (simple size check or existence)
        if os.path.exists(filepath):
            return filename
            
        # Download
        headers = {
            "User-Agent": "Mozilla/5.0",
        }
        r = requests.get(url, headers=headers, stream=True)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded: {filename}")
            return filename
        else:
            print(f"Failed to download {url}: {r.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

download_image = download_file

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

import re

# ... existing imports ...

def process_and_save(entries):
    """Process entries, translate, download images, and prepare for Notion."""
    # ... existing processed_ids check ...
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
    from datetime import timedelta # Ensure import
    
    for entry in entries:
        diary_id = entry.get("c_diary_id")
        
        if diary_id in processed_ids:
            # print(f"Skipping duplicate entry {diary_id}")
            continue
            
        print(f"Processing new entry: {entry.get('subject')}")
        
        # 1. Main Cover Image
        image_url = entry.get("girls_image_url")
        main_image_name = download_image(image_url)
        
        # 2. Content & Cookie Validation
        raw_text = entry.get("decoded_body_org", "") or entry.get("body", "")
        if "マイガール登録" in raw_text or "Member Only" in raw_text:
             print("⚠️  WARNING: Member Only content detected! Your YOASOBI_COOKIES might be invalid or expired.")

        # 3. Rich Content Extraction (Body Images + Video)
        content_blocks = []
        
        # A. Text Content (Paragraphs)
        # Simple HTML to text cleanup (preserving newlines)
        clean_text = re.sub(r'<br\s*/?>', '\n', raw_text)
        clean_text = re.sub(r'<[^>]+>', '', clean_text) # Remove other tags
        translated_text = translate_text(clean_text)
        content_blocks.append({"type": "text", "content": translated_text})
        
        # B. Inline Images from Body
        # Regex to find <img src="..."> in the raw body (not decoded, as decoded strip tags sometimes?)
        # Use 'body' or 'pcbody' for HTML
        html_body = entry.get("body", "") or entry.get("pcbody", "")
        inline_images = re.findall(r'src="([^"]+)"', html_body)
        
        for img_src in inline_images:
            if "cityheaven.net" in img_src or "yoasobi-heaven" in img_src:
                # Some are deco/emoji, filter if needed? 
                # Let's verify it's a photo (usually contains 'img/girls' or 'img/deco')
                # Users want all images including menu items, so download all.
                f_name = download_image(img_src)
                if f_name:
                    content_blocks.append({"type": "image", "filename": f_name, "url": img_src})

        # C. Video (if exists)
        # https://img.cityheaven.net/cs/mvdiary/{commu_id}/{member_id}/{diary_id}/{filename}
        movie_file = entry.get("movie_filename")
        if movie_file:
            commu_id = entry.get("c_commu_id")
            member_id = entry.get("c_member_id")
            video_url = f"https://img.cityheaven.net/cs/mvdiary/{commu_id}/{member_id}/{diary_id}/{movie_file}"
            print(f"Found video: {video_url}")
            
            # Download video to handle 404/Referer issues in Notion
            v_name = download_file(video_url)
            if v_name:
                 content_blocks.append({"type": "video", "filename": v_name, "url": video_url})
            else:
                 # Fallback to URL if download fails (might still 404 but better than nothing)
                 content_blocks.append({"type": "video", "url": video_url})

        # 4. Parse Date
        date_str = entry.get("create_date") 
        timestamp = time.time()
        
        if date_str:
            try:
                dt = datetime.strptime(f"{current_year}/{date_str}", "%Y/%m/%d %H:%M")
                if dt > datetime.now() + timedelta(days=1):
                    dt = dt.replace(year=current_year - 1)
                timestamp = dt.timestamp()
            except Exception as e:
                print(f"Error parsing date '{date_str}': {e}")

        processed_entry = {
            "id": diary_id,
            "date": date_str,
            "title": entry.get("subject"),
            "original_text": clean_text,
            "translated_text": translated_text,
            "image_filename": main_image_name,
            "image_url_original": image_url,
            "timestamp": timestamp,
            "content_blocks": content_blocks # New field
        }
        
        new_entries.append(processed_entry)
        
    # Sort new entries by timestamp descending (Newest First)
    new_entries.sort(key=lambda x: x["timestamp"], reverse=True)
        
    return new_entries

def upload_to_notion(entries):
    """Upload new entries to Notion database."""
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    github_repo = os.environ.get("GITHUB_REPOSITORY")
    
    if not token or not database_id:
        print("Notion credentials not found. Skipping upload.")
        return

    client = Client(auth=token)
    
    for entry in entries:
        try:
            print(f"Uploading to Notion: {entry['title']}")
            
            # Construct GitHub raw URL for images
            def get_gh_url(filename):
                if github_repo:
                    return f"https://raw.githubusercontent.com/{github_repo}/main/images/{filename}"
                return None

            # 1. Prepare Block Children (The Page Content)
            children_blocks = []
            
            # Add Text Paragraph
            # Split text by newlines to make nice paragraphs
            for line in entry['translated_text'].split('\n'):
                if line.strip():
                    children_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                        }
                    })
            
            # Add Rich Media Blocks (Inline Images/Videos from body)
            for block in entry.get("content_blocks", []):
                if block['type'] == 'image':
                    img_gh_url = get_gh_url(block['filename']) or block['url']
                    children_blocks.append({
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {"url": img_gh_url}
                        }
                    })
                elif block['type'] == 'video':
                    # Use GitHub URL if filename exists
                    vid_src = block.get('url')
                    if block.get('filename'):
                        vid_src = get_gh_url(block['filename']) or vid_src

                    children_blocks.append({
                        "object": "block",
                        "type": "video",
                        "video": {
                            "type": "external",
                            "external": {"url": vid_src}
                        }
                    })

            # Main Image (at top of content too?)
            # Usually Cover Image is set as page cover or just main property. 
            # We already set it in 'Image' property. User might want it in body too?
            # Let's create the page first with properties.

            main_img_url = get_gh_url(entry['image_filename']) or entry['image_url_original']

            client.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Date": {"date": {"start": datetime.fromtimestamp(entry["timestamp"]).isoformat()}},
                    "Title": {"title": [{"text": {"content": entry["title"]}}]},
                    "Content (JP)": {"rich_text": [{"text": {"content": entry["original_text"][:2000]}}]},
                    "Content (CN)": {"rich_text": [{"text": {"content": entry["translated_text"][:2000]}}]},
                    "Original URL": {"url": entry["image_url_original"]},
                    "Image": {
                        "files": [
                            {
                                "name": entry["image_filename"],
                                "type": "external",
                                "external": {"url": main_img_url}
                            }
                        ]
                    }
                },
                children=children_blocks
            )
            time.sleep(0.5) 
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
            
        new_items_on_page = 0
        total_items = len(entries)
        
        for entry in entries:
            diary_id = str(entry.get("c_diary_id"))
            
            if diary_id in existing_ids:
                # Skip duplicate
                continue
            
            all_entries.append(entry)
            new_items_on_page += 1
            
        print(f"Page {page}: Found {new_items_on_page} new entries out of {total_items}.")
        
        # Stop Condition for Standard Mode
        if not force_backfill:
            if new_items_on_page == 0:
                print("No new entries found on this page. Stopping pagination.")
                break
        
        # Safety limit to prevent infinite loops (e.g. if logic fails)
        if page > 100: 
             print("Reached page 100 limit. Stopping.")
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
