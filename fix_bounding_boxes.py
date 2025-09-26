#!/usr/bin/env python3
"""
Script to fix overlapping bounding boxes in memedb.jsonl.
Bounding boxes should not overlap and should fit within the image bounds (0-1).
"""

import json
import math
from typing import Dict, List, Tuple, Any


def boxes_overlap(box1: Dict[str, float], box2: Dict[str, float]) -> bool:
    """Check if two bounding boxes overlap."""
    # Calculate boundaries
    box1_left = box1['x'] - box1['width'] / 2
    box1_right = box1['x'] + box1['width'] / 2
    box1_top = box1['y'] - box1['height'] / 2
    box1_bottom = box1['y'] + box1['height'] / 2
    
    box2_left = box2['x'] - box2['width'] / 2
    box2_right = box2['x'] + box2['width'] / 2
    box2_top = box2['y'] - box2['height'] / 2
    box2_bottom = box2['y'] + box2['height'] / 2
    
    # Check for overlap
    return not (box1_right <= box2_left or box2_right <= box1_left or 
                box1_bottom <= box2_top or box2_bottom <= box1_top)


def get_overlap_area(box1: Dict[str, float], box2: Dict[str, float]) -> float:
    """Calculate the area of overlap between two boxes."""
    if not boxes_overlap(box1, box2):
        return 0.0
    
    # Calculate boundaries
    box1_left = box1['x'] - box1['width'] / 2
    box1_right = box1['x'] + box1['width'] / 2
    box1_top = box1['y'] - box1['height'] / 2
    box1_bottom = box1['y'] + box1['height'] / 2
    
    box2_left = box2['x'] - box2['width'] / 2
    box2_right = box2['x'] + box2['width'] / 2
    box2_top = box2['y'] - box2['height'] / 2
    box2_bottom = box2['y'] + box2['height'] / 2
    
    # Calculate overlap dimensions
    overlap_width = min(box1_right, box2_right) - max(box1_left, box2_left)
    overlap_height = min(box1_bottom, box2_bottom) - max(box1_top, box2_top)
    
    return overlap_width * overlap_height


def fix_overlapping_boxes(bounding_boxes: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Fix overlapping bounding boxes by adjusting their positions."""
    if len(bounding_boxes) <= 1:
        return bounding_boxes
    
    fixed_boxes = bounding_boxes.copy()
    box_names = list(fixed_boxes.keys())
    
    # Find all overlapping pairs
    overlaps_found = True
    max_iterations = 20
    iteration = 0
    
    while overlaps_found and iteration < max_iterations:
        overlaps_found = False
        iteration += 1
        
        for i in range(len(box_names)):
            for j in range(i + 1, len(box_names)):
                box1_name = box_names[i]
                box2_name = box_names[j]
                box1 = fixed_boxes[box1_name]
                box2 = fixed_boxes[box2_name]
                
                if boxes_overlap(box1, box2):
                    overlaps_found = True
                    
                    # Calculate center-to-center distance
                    dx = box2['x'] - box1['x']
                    dy = box2['y'] - box1['y']
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance == 0:
                        # Boxes are at same position, separate them horizontally
                        dx = 1.0
                        dy = 0.0
                        distance = 1.0
                    
                    # Normalize direction vector
                    dx /= distance
                    dy /= distance
                    
                    # Calculate minimum separation needed
                    min_separation = (box1['width'] + box2['width']) / 2 + 0.05  # 5% padding
                    
                    # Move boxes apart along the line connecting their centers
                    move_distance = (min_separation - distance) / 2
                    
                    # Adjust positions
                    box1['x'] -= dx * move_distance
                    box1['y'] -= dy * move_distance
                    box2['x'] += dx * move_distance
                    box2['y'] += dy * move_distance
                    
                    # Ensure boxes stay within image bounds (0-1)
                    for box in [box1, box2]:
                        # Keep center within bounds considering box dimensions
                        min_x = box['width'] / 2
                        max_x = 1.0 - box['width'] / 2
                        min_y = box['height'] / 2
                        max_y = 1.0 - box['height'] / 2
                        
                        box['x'] = max(min_x, min(max_x, box['x']))
                        box['y'] = max(min_y, min(max_y, box['y']))
    
    return fixed_boxes


def analyze_meme_boxes(meme_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze and report on bounding box issues for a single meme."""
    name = meme_data.get('name', 'unknown')
    boxes = meme_data.get('bounding_boxes', {})
    
    issues = []
    
    if not boxes:
        return {"name": name, "issues": ["No bounding boxes defined"], "overlaps": []}
    
    # Check for overlaps
    overlaps = []
    box_names = list(boxes.keys())
    
    for i in range(len(box_names)):
        for j in range(i + 1, len(box_names)):
            box1_name = box_names[i]
            box2_name = box_names[j]
            box1 = boxes[box1_name]
            box2 = boxes[box2_name]
            
            if boxes_overlap(box1, box2):
                overlap_area = get_overlap_area(box1, box2)
                overlaps.append({
                    "boxes": [box1_name, box2_name],
                    "overlap_area": round(overlap_area, 4)
                })
    
    # Check for out-of-bounds boxes
    for box_name, box in boxes.items():
        left = box['x'] - box['width'] / 2
        right = box['x'] + box['width'] / 2
        top = box['y'] - box['height'] / 2
        bottom = box['y'] + box['height'] / 2
        
        if left < 0 or right > 1 or top < 0 or bottom > 1:
            issues.append(f"{box_name} extends outside image bounds")
    
    return {
        "name": name,
        "issues": issues,
        "overlaps": overlaps,
        "total_overlaps": len(overlaps)
    }


def main():
    """Main function to fix bounding boxes in memedb.jsonl."""
    input_file = "/Users/jaychia/code/coinmeme/memedb.jsonl"
    output_file = "/Users/jaychia/code/coinmeme/memedb_fixed.jsonl"
    
    print("🔍 Analyzing memedb.jsonl for bounding box issues...")
    
    # Read and analyze the data
    memes = []
    issues_found = []
    
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                meme_data = json.loads(line)
                memes.append(meme_data)
                
                # Analyze this meme's boxes
                analysis = analyze_meme_boxes(meme_data)
                if analysis['issues'] or analysis['overlaps']:
                    issues_found.append(analysis)
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing line {line_num}: {e}")
                continue
    
    print(f"📊 Found {len(issues_found)} memes with bounding box issues:")
    print()
    
    # Report issues
    total_overlaps = 0
    for issue in issues_found:
        print(f"🎭 {issue['name']}:")
        if issue['issues']:
            for problem in issue['issues']:
                print(f"  ⚠️  {problem}")
        if issue['overlaps']:
            for overlap in issue['overlaps']:
                print(f"  🔄 {overlap['boxes'][0]} overlaps with {overlap['boxes'][1]} (area: {overlap['overlap_area']})")
                total_overlaps += 1
        print()
    
    if total_overlaps == 0:
        print("✅ No overlapping bounding boxes found!")
        return
    
    print(f"🔧 Fixing {total_overlaps} overlapping bounding box pairs...")
    print()
    
    # Fix the issues
    fixed_memes = []
    for meme_data in memes:
        if 'bounding_boxes' in meme_data and meme_data['bounding_boxes']:
            original_boxes = meme_data['bounding_boxes'].copy()
            fixed_boxes = fix_overlapping_boxes(meme_data['bounding_boxes'])
            meme_data['bounding_boxes'] = fixed_boxes
            
            # Report what was changed
            changed = False
            for box_name in original_boxes:
                orig = original_boxes[box_name]
                fixed = fixed_boxes[box_name]
                if (abs(orig['x'] - fixed['x']) > 0.001 or 
                    abs(orig['y'] - fixed['y']) > 0.001):
                    if not changed:
                        print(f"🔄 Fixed {meme_data['name']}:")
                        changed = True
                    print(f"  📦 {box_name}: ({orig['x']:.3f}, {orig['y']:.3f}) → ({fixed['x']:.3f}, {fixed['y']:.3f})")
            if changed:
                print()
        
        fixed_memes.append(meme_data)
    
    # Write the fixed data
    with open(output_file, 'w') as f:
        for meme_data in fixed_memes:
            f.write(json.dumps(meme_data) + '\n')
    
    print(f"✅ Fixed bounding boxes saved to: {output_file}")
    print("🔄 To apply changes, run: mv memedb_fixed.jsonl memedb.jsonl")


if __name__ == "__main__":
    main()