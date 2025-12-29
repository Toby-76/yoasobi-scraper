#!/usr/bin/env python3
"""
Test script for downloading and processing a single article with video cover.
This helps verify that video covers with anti-hotlinking protection work correctly.

Example article: 💌顔舐め敏感スイッチﾎﾟﾁ💌
URL: https://yoasobi-heaven.com/zh-hans/tokyo/A1304/bb-w/girlid-57698938/diary/2/
"""

import os
import json
from scraper import (
    load_params, get_session, get_csrf_token, 
    fetch_diary_entries, process_and_save, upload_to_notion
)

def test_single_article():
    """Test downloading and processing a single article."""
    
    print("=" * 60)
    print("Testing Single Article with Video Cover")
    print("=" * 60)
    
    # 1. Setup
    print("\n[1] Setting up session...")
    params = load_params()
    session = get_session()
    
    # 2. Auth
    print("\n[2] Getting CSRF token...")
    token = get_csrf_token(session)
    if not token:
        print("❌ Failed to get CSRF token")
        return
    
    # 3. Fetch diary entries and look for video covers
    print("\n[3] Fetching diary entries from API...")
    target_title = "💌顔舐め敏感スイッチﾎﾟﾁ💌"
    test_entry = None
    max_pages_to_search = 5  # Search up to 5 pages
    
    for page_num in range(1, max_pages_to_search + 1):
        print(f"Searching page {page_num}...")
        entries = fetch_diary_entries(session, token, params, page=page_num)
        
        if not entries:
            print(f"No entries found on page {page_num}")
            break
        
        print(f"  Found {len(entries)} entries on page {page_num}")
        
        # First try to find the specific article
        for entry in entries:
            if entry.get("subject") == target_title:
                test_entry = entry
                print(f"\n✅ Found target article: {target_title}")
                break
        
        if test_entry:
            break
        
        # If not found on this page, look for any entry with video cover
        for entry in entries:
            cover_url = entry.get("girls_image_url", "")
            if cover_url and cover_url.lower().endswith('.mp4'):
                test_entry = entry
                print(f"\n✅ Found article with video cover: {entry.get('subject')}")
                break
        
        if test_entry:
            break
    
    # If still not found after searching multiple pages, use first entry from page 1
    if not test_entry:
        print(f"\n⚠️  No video cover found in {max_pages_to_search} pages")
        print("Fetching first entry for basic testing...")
        entries = fetch_diary_entries(session, token, params, page=1)
        if entries:
            test_entry = entries[0]
            print(f"Using: {test_entry.get('subject')}")
        else:
            print("❌ No entries found at all")
            return
    
    # Print entry details
    print("\n" + "-" * 60)
    print("Article Details:")
    print(f"  Title: {test_entry.get('subject')}")
    print(f"  Diary ID: {test_entry.get('c_diary_id')}")
    print(f"  Cover URL: {test_entry.get('girls_image_url')}")
    print(f"  Date: {test_entry.get('create_date')}")
    print("-" * 60)
    
    # 5. Process the entry (download images/videos, translate)
    print("\n[4] Processing entry (downloading files, translating)...")
    processed_data = process_and_save([test_entry], session=session)
    
    if not processed_data:
        print("❌ Failed to process entry")
        return
    
    processed_entry = processed_data[0]
    print(f"✅ Successfully processed!")
    print(f"  Cover type: {processed_entry.get('cover_type')}")
    print(f"  Cover filename: {processed_entry.get('cover_filename')}")
    print(f"  Content blocks: {len(processed_entry.get('content_blocks', []))}")
    
    # Show content blocks summary
    print("\n  Content Structure:")
    for i, block in enumerate(processed_entry.get('content_blocks', [])[:10]):
        block_type = block.get('type')
        if block_type == 'video':
            is_cover = " (COVER)" if block.get('is_cover') else ""
            print(f"    [{i}] Video{is_cover}: {block.get('filename', 'URL only')}")
        elif block_type == 'image':
            print(f"    [{i}] Image: {block.get('filename')}")
        elif block_type == 'heading_2':
            print(f"    [{i}] Heading: {block.get('content')}")
        elif block_type == 'divider':
            print(f"    [{i}] ---")
        elif block_type == 'text':
            preview = block.get('content', '')[:50]
            print(f"    [{i}] Text: {preview}...")
    
    # 6. Upload to Notion (if credentials are set)
    print("\n[5] Uploading to Notion...")
    notion_token = os.environ.get("NOTION_TOKEN")
    notion_db_id = os.environ.get("NOTION_DATABASE_ID")
    
    if notion_token and notion_db_id:
        upload_to_notion(processed_data)
        print("✅ Upload complete! Check your Notion database.")
    else:
        print("⚠️  Notion credentials not set (NOTION_TOKEN, NOTION_DATABASE_ID)")
        print("   Skipping Notion upload (files are downloaded to ./images/)")
    
    # 7. Save to a test JSON file (not data_store.json)
    test_output_file = "test_output.json"
    print(f"\n[6] Saving results to {test_output_file}...")
    with open(test_output_file, "w", encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved to {test_output_file}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nSummary:")
    print(f"  - Article processed: {processed_entry.get('title')}")
    print(f"  - Cover type: {processed_entry.get('cover_type')}")
    print(f"  - Files downloaded to: ./images/")
    print(f"  - Test data saved to: {test_output_file}")
    if notion_token and notion_db_id:
        print(f"  - Uploaded to Notion: ✅")
    else:
        print(f"  - Uploaded to Notion: ⏭️  (skipped - no credentials)")
    print()

if __name__ == "__main__":
    test_single_article()
