#!/usr/bin/env python3
"""
Demonstration: How the code handles video covers

This script demonstrates what happens when an article has a video cover
by manually creating test data with a video cover URL.
"""

import json

def demo_video_cover_detection():
    """Show how video cover detection works"""
    
    print("=" * 70)
    print("DEMO: Video Cover Detection Logic")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Normal Image Cover",
            "url": "https://img.cityheaven.net/img/girls/tt/bb-w/grdr0057698938_0767003472pc.jpg",
            "expected_type": "image"
        },
        {
            "name": "MP4 Video Cover",
            "url": "https://img.cityheaven.net/img/girls/tt/bb-w/grdr0057698938_0767003472pc.mp4",
            "expected_type": "video"
        },
        {
            "name": "Video with Query Params",
            "url": "https://example.com/cover.mp4?v=123&quality=hd",
            "expected_type": "video"
        },
        {
            "name": "WebM Video",
            "url": "https://example.com/cover.webm",
            "expected_type": "video"
        }
    ]
    
    print("\nTesting cover type detection:\n")
    
    for i, test in enumerate(test_cases, 1):
        url = test["url"]
        expected = test["expected_type"]
        
        # Simulate the detection logic from scraper.py
        import os
        cover_ext = os.path.splitext(url.split("?")[0])[1].lower()
        if cover_ext in ['.mp4', '.mov', '.avi', '.webm']:
            detected_type = "video"
        else:
            detected_type = "image"
        
        status = "✅" if detected_type == expected else "❌"
        
        print(f"{i}. {test['name']}")
        print(f"   URL: {url}")
        print(f"   Extension: {cover_ext}")
        print(f"   Detected: {detected_type} (expected: {expected}) {status}")
        print()
    
    print("-" * 70)
    print("\nWhat happens with video covers:\n")
    print("1. 🔍 Detection: File extension checked (.mp4, .mov, .avi, .webm)")
    print("2. ⬇️  Download: Video downloaded with referer header for anti-hotlinking")
    print("3. 📦 Storage: Saved with cover_type='video' and cover_filename")
    print("4. 📄 Content: Video added to TOP of content_blocks with is_cover=True")
    print("5. 🌐 Notion: Video appears in page content; Image property uses first image")
    print()
    
    print("-" * 70)
    print("\nExample JSON structure for video cover:\n")
    
    example_entry = {
        "id": "123456",
        "title": "Example Article with Video Cover",
        "cover_filename": "video_cover.mp4",
        "cover_type": "video",
        "image_url_original": "https://example.com/video_cover.mp4",
        "content_blocks": [
            {
                "type": "video",
                "filename": "video_cover.mp4",
                "url": "https://example.com/video_cover.mp4",
                "is_cover": True
            },
            {"type": "divider"},
            {"type": "heading_2", "content": "🇯🇵 原文"},
            {"type": "text", "content": "Article content..."}
        ]
    }
    
    print(json.dumps(example_entry, indent=2, ensure_ascii=False))
    print()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)

if __name__ == "__main__":
    demo_video_cover_detection()
