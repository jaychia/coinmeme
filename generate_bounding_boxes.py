#!/usr/bin/env python3
"""
Script to use OpenAI Vision API to analyze meme template images and generate
accurate bounding boxes for text placement regions.
"""

import base64
import json
import os
from typing import Dict, List, Any
from pathlib import Path

from openai import OpenAI
from PIL import Image


def encode_image(image_path: str) -> str:
    """Encode image to base64 for OpenAI API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_image_dimensions(image_path: str) -> tuple[int, int]:
    """Get image width and height."""
    with Image.open(image_path) as img:
        return img.size


def analyze_meme_with_openai(image_path: str, meme_name: str, schema: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Use OpenAI Vision to analyze a meme image and identify text placement regions."""
    
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    client = OpenAI()
    base64_image = encode_image(image_path)
    width, height = get_image_dimensions(image_path)
    
    # Create schema description for the prompt
    schema_desc = ""
    for field_name, field_info in schema.items():
        schema_desc += f"- {field_name}: {field_info['description']}\n"
    
    prompt = f"""Analyze this meme template image for the "{meme_name}" meme format.

This meme has the following text fields that need to be placed:
{schema_desc}

CRITICAL REQUIREMENTS:
1. Look at where text ACTUALLY appears in existing meme examples of this format
2. Text boxes must be placed in EMPTY/NEUTRAL areas with good contrast
3. Never place text over faces, important objects, or busy backgrounds
4. Text boxes should be CONSERVATIVE in size - better too small than too large
5. Ensure proper spacing between multiple text areas

The image dimensions are {width}x{height} pixels.

Return ONLY a valid JSON object with this exact structure:
{{
  "field_name_1": {{
    "x": 0.5,
    "y": 0.2,
    "width": 0.6,
    "height": 0.1
  }}
}}

STRICT COORDINATE RULES:
- x, y are the CENTER coordinates normalized to 0-1 range
- width, height are normalized to 0-1 range  
- x must be between width/2 and (1 - width/2)
- y must be between height/2 and (1 - height/2)
- width should be between 0.2 and 0.8 (reasonable text area)
- height should be between 0.05 and 0.2 (text height)
- Ensure NO overlap between boxes
- Leave at least 0.1 spacing between box edges

Provide coordinates for: {', '.join(schema.keys())}

REMEMBER: Look at the actual image to see where text typically goes in this meme format!"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Remove any markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
            
            bounding_boxes = json.loads(content)
            
            # Remove reasoning field and validate structure
            cleaned_boxes = {}
            for field_name, box_data in bounding_boxes.items():
                if field_name in schema:
                    # Extract and validate coordinates
                    x = float(box_data.get("x", 0.5))
                    y = float(box_data.get("y", 0.5))
                    width = float(box_data.get("width", 0.3))
                    height = float(box_data.get("height", 0.1))
                    
                    # Enforce size constraints
                    width = max(0.2, min(0.8, width))
                    height = max(0.05, min(0.2, height))
                    
                    # Ensure box stays completely within bounds
                    min_x = width / 2
                    max_x = 1.0 - width / 2
                    min_y = height / 2
                    max_y = 1.0 - height / 2
                    
                    x = max(min_x, min(max_x, x))
                    y = max(min_y, min(max_y, y))
                    
                    # Double-check bounds (safety)
                    left = x - width / 2
                    right = x + width / 2
                    top = y - height / 2
                    bottom = y + height / 2
                    
                    if left < 0 or right > 1 or top < 0 or bottom > 1:
                        print(f"⚠️  Correcting out-of-bounds box for {field_name}")
                        # Recalculate with stricter bounds
                        width = min(width, 0.6)
                        height = min(height, 0.15)
                        x = max(width/2 + 0.05, min(1 - width/2 - 0.05, x))
                        y = max(height/2 + 0.05, min(1 - height/2 - 0.05, y))
                    
                    cleaned_boxes[field_name] = {
                        "x": round(x, 3),
                        "y": round(y, 3), 
                        "width": round(width, 3),
                        "height": round(height, 3)
                    }
            
            return cleaned_boxes
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON from OpenAI response for {meme_name}: {e}")
            print(f"Response content: {content}")
            return {}
    
    except Exception as e:
        print(f"❌ Error analyzing {meme_name} with OpenAI: {e}")
        return {}


def load_meme_database() -> List[Dict[str, Any]]:
    """Load the current meme database."""
    memes = []
    with open("/Users/jaychia/code/coinmeme/memedb.jsonl", 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                memes.append(json.loads(line))
    return memes


def save_meme_database(memes: List[Dict[str, Any]], output_file: str):
    """Save the updated meme database."""
    with open(output_file, 'w') as f:
        for meme in memes:
            f.write(json.dumps(meme) + '\n')


def main():
    """Main function to analyze all meme images and generate bounding boxes."""
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("Set it with: export OPENAI_API_KEY='your-api-key'")
        return
    
    print("🔍 Loading meme database...")
    memes = load_meme_database()
    
    meme_templates_dir = Path("/Users/jaychia/code/coinmeme/meme_templates")
    
    # Map meme names to image files
    image_mapping = {}
    for image_file in meme_templates_dir.glob("*.jpg"):
        # Convert filename to match meme names
        name = image_file.stem.lower().replace("-", "_").replace(" ", "_")
        image_mapping[name] = str(image_file)
    
    print(f"📁 Found {len(image_mapping)} image files")
    print(f"📊 Processing {len(memes)} meme definitions")
    print()
    
    updated_memes = []
    
    for meme in memes:
        meme_name = meme.get("name", "")
        schema = meme.get("schema", {})
        
        # Find matching image file
        image_path = None
        for img_name, img_path in image_mapping.items():
            if meme_name.lower() in img_name or img_name in meme_name.lower():
                image_path = img_path
                break
        
        if not image_path:
            print(f"⚠️  No image file found for meme: {meme_name}")
            updated_memes.append(meme)
            continue
        
        if not schema:
            print(f"⚠️  No schema found for meme: {meme_name}")
            updated_memes.append(meme)
            continue
        
        print(f"🎭 Analyzing {meme_name}...")
        print(f"   📁 Image: {Path(image_path).name}")
        print(f"   📝 Fields: {', '.join(schema.keys())}")
        
        # Analyze with OpenAI
        new_bounding_boxes = analyze_meme_with_openai(image_path, meme_name, schema)
        
        if new_bounding_boxes:
            print(f"   ✅ Generated bounding boxes for {len(new_bounding_boxes)} fields")
            meme["bounding_boxes"] = new_bounding_boxes
        else:
            print(f"   ❌ Failed to generate bounding boxes")
        
        updated_memes.append(meme)
        print()
    
    # Save updated database
    output_file = "/Users/jaychia/code/coinmeme/memedb_ai_generated.jsonl"
    save_meme_database(updated_memes, output_file)
    
    print(f"✅ Updated meme database saved to: {output_file}")
    print("🔄 To apply changes, run: mv memedb_ai_generated.jsonl memedb.jsonl")


if __name__ == "__main__":
    main()