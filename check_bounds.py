#!/usr/bin/env python3
"""
Script to check which bounding boxes extend outside image bounds.
"""

import json
from typing import Dict, List, Any


def check_box_bounds(box: Dict[str, float], box_name: str, meme_name: str) -> List[str]:
    """Check if a bounding box extends outside 0-1 bounds."""
    issues = []
    
    # Calculate boundaries
    left = box['x'] - box['width'] / 2
    right = box['x'] + box['width'] / 2
    top = box['y'] - box['height'] / 2
    bottom = box['y'] + box['height'] / 2
    
    if left < 0:
        issues.append(f"{meme_name}.{box_name}: left edge at {left:.3f} (< 0)")
    if right > 1:
        issues.append(f"{meme_name}.{box_name}: right edge at {right:.3f} (> 1)")
    if top < 0:
        issues.append(f"{meme_name}.{box_name}: top edge at {top:.3f} (< 0)")
    if bottom > 1:
        issues.append(f"{meme_name}.{box_name}: bottom edge at {bottom:.3f} (> 1)")
    
    return issues


def main():
    """Check all bounding boxes for bounds issues."""
    print("🔍 Checking bounding box bounds...")
    
    all_issues = []
    
    with open("/Users/jaychia/code/coinmeme/memedb.jsonl", 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                meme_data = json.loads(line)
                meme_name = meme_data.get('name', f'line_{line_num}')
                bounding_boxes = meme_data.get('bounding_boxes', {})
                
                for box_name, box in bounding_boxes.items():
                    issues = check_box_bounds(box, box_name, meme_name)
                    all_issues.extend(issues)
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing line {line_num}: {e}")
                continue
    
    if all_issues:
        print(f"\n❌ Found {len(all_issues)} bounding box issues:")
        for issue in all_issues:
            print(f"  {issue}")
    else:
        print("\n✅ All bounding boxes are within image bounds!")


if __name__ == "__main__":
    main()