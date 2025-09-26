#!/usr/bin/env python3
"""
Test script to verify data loading works correctly
"""

import json
import os

def test_meme_briefs():
    """Test loading meme briefs"""
    print("Testing meme briefs loading...")
    
    briefs = []
    brief_dir = "meme_briefs"
    
    if not os.path.exists(brief_dir):
        print(f"❌ Directory {brief_dir} not found")
        return False
    
    count = 0
    for filename in sorted(os.listdir(brief_dir)):
        if filename.startswith("brief_") and filename.endswith(".json"):
            filepath = os.path.join(brief_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    brief = json.load(f)
                    briefs.append(brief)
                    count += 1
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")
                return False
    
    print(f"✅ Loaded {count} meme briefs")
    if briefs:
        print(f"   Sample brief: {briefs[0].get('search', 'Unknown')}")
    return True

def test_meme_templates():
    """Test loading meme templates"""
    print("Testing meme templates loading...")
    
    templates = []
    memedb_path = "memedb.jsonl"
    
    if not os.path.exists(memedb_path):
        print(f"❌ File {memedb_path} not found")
        return False
    
    try:
        with open(memedb_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    template = json.loads(line.strip())
                    templates.append(template)
    except Exception as e:
        print(f"❌ Error loading templates: {e}")
        return False
    
    print(f"✅ Loaded {len(templates)} meme templates")
    if templates:
        print(f"   Sample template: {templates[0].get('name', 'Unknown')}")
    return True

def test_template_images():
    """Test that template images exist"""
    print("Testing template images...")
    
    memedb_path = "memedb.jsonl"
    if not os.path.exists(memedb_path):
        print(f"❌ File {memedb_path} not found")
        return False
    
    templates = []
    try:
        with open(memedb_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    template = json.loads(line.strip())
                    templates.append(template)
    except Exception as e:
        print(f"❌ Error loading templates: {e}")
        return False
    
    missing_images = []
    for template in templates:
        template_name = template.get('name', '')
        image_path = f"meme_templates/{template_name}.jpg"
        if not os.path.exists(image_path):
            missing_images.append(template_name)
    
    if missing_images:
        print(f"❌ Missing images for templates: {missing_images}")
        return False
    
    print(f"✅ All {len(templates)} template images found")
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Meme Generator data...")
    print("=" * 50)
    
    tests = [
        test_meme_briefs,
        test_meme_templates,
        test_template_images
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All tests passed! The app should work correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main()
