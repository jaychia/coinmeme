import streamlit as st
import json
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import openai
from typing import Dict, List, Any
import base64
from io import BytesIO

# Configure page
st.set_page_config(
    page_title="Meme Generator",
    page_icon="🎭",
    layout="wide"
)

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Please set your OPENAI_API_KEY environment variable")
        st.stop()
    return openai.OpenAI(api_key=api_key)

def load_meme_briefs() -> List[Dict[str, Any]]:
    """Load meme briefs from the CSV file with viral explanations"""
    briefs = []
    csv_path = "clay_meme_briefs/Custom-Table-Default-view-export-1758929307125.csv"
    
    if not os.path.exists(csv_path):
        st.error(f"CSV file not found: {csv_path}")
        return briefs
    
    try:
        df = pd.read_csv(csv_path)
        
        for _, row in df.iterrows():
            brief = {
                'search': row.get('Topic', 'Unknown'),
                'explanation': row.get('Viral Reason Explanation', ''),
                'detailed_reason': row.get('Viral Reason Explanation Reason', ''),
                'source': 'clay_meme_briefs'
            }
            briefs.append(brief)
            
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
    
    return briefs

def load_meme_templates() -> List[Dict[str, Any]]:
    """Load meme templates from memedb.jsonl"""
    templates = []
    memedb_path = "memedb.jsonl"
    
    if not os.path.exists(memedb_path):
        return templates
    
    try:
        with open(memedb_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    template = json.loads(line.strip())
                    templates.append(template)
    except Exception as e:
        st.error(f"Error loading meme templates: {e}")
    
    return templates

def save_new_template(template: Dict[str, Any], image: Image.Image) -> bool:
    """Save a new template to memedb.jsonl and save the image to meme_templates/"""
    try:
        # Get template name and clean it
        original_name = template.get('name', 'custom_template')
        template_name = original_name.lower().replace(' ', '_').replace('-', '_').replace('"', '').replace("'", '').replace('!', '').replace('?', '').replace(':', '').replace(';', '').replace(',', '').replace('.', '')
        st.info(f"Original template name: '{original_name}' -> Cleaned name: '{template_name}'")
        
        # Ensure unique name by checking existing templates
        existing_templates = load_meme_templates()
        counter = 1
        original_name = template_name
        while any(t.get('name') == template_name for t in existing_templates):
            template_name = f"{original_name}_{counter}"
            counter += 1
        
        # Update template with final name
        template['name'] = template_name
        
        # Ensure meme_templates directory exists
        os.makedirs("meme_templates", exist_ok=True)
        
        # Save image to meme_templates/
        image_path = f"meme_templates/{template_name}.jpg"
        image.save(image_path, "JPEG")
        st.info(f"Image saved to: {image_path}")
        
        # Save template to memedb.jsonl
        with open("memedb.jsonl", "a", encoding='utf-8') as f:
            f.write(json.dumps(template) + "\n")
        st.info(f"Template saved to memedb.jsonl with name: {template_name}")
        
        return True
        
    except Exception as e:
        st.error(f"Error saving template: {e}")
        return False

def analyze_image_for_meme_template(image: Image.Image, description: str, client: openai.OpenAI) -> Dict[str, Any]:
    """Analyze an uploaded image to create a meme template using OpenAI Vision"""
    
    # Convert PIL image to base64
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    prompt = f"""
    Analyze this image as a potential meme template. The user provided this description: "{description}"
    
    Based on the image and description, create a meme template JSON structure with:
    1. A descriptive name for the template
    2. An explanation of what the meme represents
    3. A schema defining text fields that can be overlaid on the image
    4. Bounding boxes for each text field with x, y, width, height coordinates
    
    Look for areas in the image where text is typically placed in memes (speech bubbles, signs, captions, etc.).
    Identify 1-4 text areas that would make sense for meme text.
    
    Return ONLY a JSON object with this structure:
    {{
        "name": "descriptive_template_name",
        "explanation": "What this meme template represents",
        "schema": {{
            "field1": {{"description": "What this text field represents"}},
            "field2": {{"description": "What this text field represents"}}
        }},
        "bounding_boxes": {{
            "field1": {{"x": 100, "y": 200, "width": 300, "height": 80}},
            "field2": {{"x": 150, "y": 400, "width": 250, "height": 60}}
        }}
    }}
    
    Use absolute pixel coordinates based on the image dimensions. Make sure bounding boxes are positioned appropriately for text placement.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        
        try:
            template = json.loads(content)
            return template
        except json.JSONDecodeError:
            # Try to extract JSON from the response if it's wrapped in markdown or other text
            import re
            
            # Look for JSON in code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    template = json.loads(json_match.group(1))
                    return template
                except json.JSONDecodeError:
                    pass
            
            # Look for JSON object in the text
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    template = json.loads(json_match.group(0))
                    return template
                except json.JSONDecodeError:
                    pass
            
            # If all else fails, create a basic template structure
            st.warning("Could not parse JSON response, creating basic template structure")
            
            # Extract basic info from the response
            lines = content.split('\n')
            name = "custom_template"
            explanation = "Custom meme template"
            
            # Try to extract name and explanation from the response
            for line in lines:
                if 'name' in line.lower() and ':' in line:
                    name_part = line.split(':')[-1].strip().strip('"\'')
                    if name_part:
                        name = name_part
                elif 'explanation' in line.lower() and ':' in line:
                    exp_part = line.split(':')[-1].strip().strip('"\'')
                    if exp_part:
                        explanation = exp_part
            
            # Create a basic template structure
            template = {
                "name": name.lower().replace(' ', '_').replace('-', '_'),
                "explanation": explanation,
                "schema": {
                    "text1": {"description": "Main text for the meme"},
                    "text2": {"description": "Secondary text for the meme"}
                },
                "bounding_boxes": {
                    "text1": {"x": 50, "y": 50, "width": 300, "height": 80},
                    "text2": {"x": 50, "y": 200, "width": 300, "height": 80}
                }
            }
            
            return template
            
    except Exception as e:
        st.error(f"Error analyzing image: {e}")
        return None

def generate_meme_content(topic: str, template: Dict[str, Any], client: openai.OpenAI, viral_context: str = "") -> Dict[str, str]:
    """Generate meme content using OpenAI"""
    
    # Create prompt for OpenAI
    schema = template.get('schema', {})
    explanation = template.get('explanation', '')
    
    prompt = f"""
    Create a meme about "{topic}" using the "{template['name']}" template.
    
    Template explanation: {explanation}
    
    Template schema: {json.dumps(schema, indent=2)}
    
    Viral context: {viral_context}
    
    Generate SHORT, FUNNY text for each field in the schema. Make it relevant to the topic "{topic}" and the viral context.
    Keep each text under 50 characters. Be concise and punchy.
    
    Return ONLY a JSON object with field names as keys and SHORT text strings as values.
    Example format: {{"field1": "short funny text", "field2": "another short text"}}
    
    Do NOT include descriptions, explanations, or metadata. Just the raw text content.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative meme generator. Generate funny, relevant text for meme templates."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        
        try:
            result = json.loads(content)
            
            # Clean up the result to extract only text values
            cleaned_result = {}
            for field, value in result.items():
                if isinstance(value, dict):
                    # If it's a dict with description, extract the description
                    if 'description' in value:
                        cleaned_result[field] = value['description']
                    else:
                        # Take the first string value from the dict
                        for v in value.values():
                            if isinstance(v, str):
                                cleaned_result[field] = v
                                break
                elif isinstance(value, str):
                    cleaned_result[field] = value
                else:
                    cleaned_result[field] = str(value)
            
            return cleaned_result
            
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract text from the response
            st.warning("Failed to parse JSON response, using fallback text extraction")
            return {key: f"Generated text for {topic}" for key in schema.keys()}
            
    except Exception as e:
        st.error(f"Error generating meme content: {e}")
        return {key: f"Error generating text" for key in schema.keys()}

def wrap_text(text: str, font, max_width: int) -> str:
    """Wrap text to fit within the specified width"""
    if not font:
        return str(text)
    
    # Ensure text is a string
    text = str(text)
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        # Create a test line with the current word
        test_line = ' '.join(current_line + [word])
        
        # Get text width using a dummy image
        dummy_img = Image.new('RGB', (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long, add it anyway
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)

def fit_text_to_bbox(text: str, font, bbox_width: int, bbox_height: int) -> tuple:
    """Try different font sizes to fit text optimally in bounding box"""
    if not font:
        return str(text), font
    
    # Try different font sizes to maximize text usage
    font_sizes = [24, 20, 18, 16, 14, 12, 10]
    
    for size in font_sizes:
        try:
            test_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", size)
        except:
            test_font = font
        
        # Test if text fits with this font size
        dummy_img = Image.new('RGB', (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        
        # Test single line first
        bbox = dummy_draw.textbbox((0, 0), text, font=test_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        if text_width <= bbox_width and text_height <= bbox_height:
            return text, test_font
        
        # Test wrapped text
        wrapped = wrap_text(text, test_font, bbox_width)
        lines = wrapped.split('\n')
        
        # Calculate total height for wrapped text
        total_height = len(lines) * text_height
        
        if total_height <= bbox_height:
            return wrapped, test_font
    
    # Fallback to original
    return wrap_text(text, font, bbox_width), font

def create_meme_image(template: Dict[str, Any], meme_content: Dict[str, str]) -> Image.Image:
    """Create the final meme image by overlaying text on the template"""
    
    # Load the template image
    template_name = template.get('name', '')
    template_path = f"meme_templates/{template_name}.jpg"
    
    if not os.path.exists(template_path):
        st.error(f"Template image not found: {template_path}")
        return None
    
    try:
        # Open the template image
        img = Image.open(template_path)
        img = img.convert('RGB')
        
        # Create a copy for drawing
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default if not available
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
            font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 14)
        except:
            try:
                font_large = ImageFont.load_default()
                font_medium = font_large
                font_small = font_large
            except:
                font_large = None
                font_medium = None
                font_small = None
        
        # Get image dimensions
        width, height = img.size
        
        # Define text positions using bounding boxes
        text_positions = get_text_positions(template, width, height)
        
        # Add text overlay based on template
        for field, content in meme_content.items():
            if field in text_positions:
                pos = text_positions[field]
                font = pos.get('font', font_medium)
                color = pos.get('color', 'white')
                stroke_color = pos.get('stroke_color', 'black')
                stroke_width = pos.get('stroke_width', 2)
                
                # Ensure content is a string
                content = str(content)
                
                # Wrap text to fit within bounding box
                bbox = pos.get('bbox', (0, 0, width//4, height//4))
                box_width = bbox[2]  # Width of the bounding box
                box_height = bbox[3]  # Height of the bounding box
                
                # Fit text optimally to the bounding box
                fitted_text, optimal_font = fit_text_to_bbox(content, font, box_width, box_height)
                
                # Draw text with stroke for better visibility
                draw.text(
                    pos['position'], 
                    fitted_text, 
                    font=optimal_font, 
                    fill=color,
                    stroke_fill=stroke_color,
                    stroke_width=stroke_width,
                    anchor="mm"
                )
        
        return img
        
    except Exception as e:
        st.error(f"Error creating meme image: {e}")
        return None

def create_template_with_boxes(template: Dict[str, Any]) -> Image.Image:
    """Create a version of the template with bounding boxes drawn on it"""
    
    template_name = template.get('name', '')
    template_path = f"meme_templates/{template_name}.jpg"
    
    if not os.path.exists(template_path):
        return None
    
    try:
        # Open the template image
        img = Image.open(template_path)
        img = img.convert('RGB')
        
        # Create a copy for drawing
        draw = ImageDraw.Draw(img)
        
        # Get image dimensions
        width, height = img.size
        
        # Get bounding boxes
        bounding_boxes = template.get('bounding_boxes', {})
        
        # Draw bounding boxes
        for field, bbox in bounding_boxes.items():
            # Use absolute pixel coordinates directly
            x = bbox['x']
            y = bbox['y']
            box_width = bbox['width']
            box_height = bbox['height']
            
            # Draw rectangle outline
            draw.rectangle(
                [x, y, x + box_width, y + box_height],
                outline="red",
                width=3
            )
            
            # Draw field name in the box
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # Calculate text position (center of box)
            text_x = x + box_width // 2
            text_y = y + box_height // 2
            
            # Draw field name with background
            text_bbox = draw.textbbox((0, 0), field, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Draw background rectangle for text
            padding = 4
            draw.rectangle(
                [text_x - text_width//2 - padding, text_y - text_height//2 - padding,
                 text_x + text_width//2 + padding, text_y + text_height//2 + padding],
                fill="red",
                outline="white"
            )
            
            # Draw text
            draw.text(
                (text_x, text_y),
                field,
                font=font,
                fill="white",
                anchor="mm"
            )
        
        return img
        
    except Exception as e:
        st.error(f"Error creating template with boxes: {e}")
        return None

def get_text_positions(template: Dict[str, Any], width: int, height: int) -> Dict[str, Dict]:
    """Get text positions using bounding boxes from template data"""
    
    positions = {}
    bounding_boxes = template.get('bounding_boxes', {})
    
    # Convert font names to actual font objects
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
        font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
    except:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large
    
    font_map = {"large": font_large, "medium": font_medium, "small": font_small}
    
    # Process each bounding box
    for field, bbox in bounding_boxes.items():
        # Use absolute pixel coordinates directly
        x = bbox['x']
        y = bbox['y']
        box_width = bbox['width']
        box_height = bbox['height']
        
        # Calculate center position for text
        center_x = x + box_width // 2
        center_y = y + box_height // 2
        
        # Determine font size based on bounding box size - more aggressive sizing
        if box_height > 0.3 * height:
            font_size = "large"
        elif box_height > 0.2 * height:
            font_size = "medium"
        else:
            font_size = "small"
        
        # Determine text color based on template
        template_name = template.get('name', '')
        if template_name == "change_my_mind":
            color = "black"
        elif template_name == "uno_draw_25" and field == "consequence":
            color = "red"
        else:
            color = "white"
        
        positions[field] = {
            "position": (center_x, center_y),
            "font": font_map.get(font_size, font_medium),
            "color": color,
            "stroke_color": "black" if color == "white" else "white",
            "stroke_width": 2,
            "bbox": (x, y, box_width, box_height)
        }
    
    return positions

def main():
    st.title("🎭 Meme Generator")
    st.markdown("Generate hilarious memes by selecting a topic and template!")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set your OPENAI_API_KEY environment variable")
        st.stop()
    
    # Load data
    with st.spinner("Loading meme briefs and templates..."):
        briefs = load_meme_briefs()
        templates = load_meme_templates()
    
    if not briefs:
        st.error("No meme briefs found. Please check the meme_briefs directory.")
        st.stop()
    
    if not templates:
        st.error("No meme templates found. Please check the memedb.jsonl file.")
        st.stop()
    
    # Initialize variables
    selected_template = None
    template = None
    new_template = None
    
    # Create two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📝 Select a Topic")
        
        # Display topics
        topic_options = {}
        for brief in briefs:
            search_term = brief.get('search', 'Unknown')
            topic_options[search_term] = brief
        
        selected_topic = st.selectbox(
            "Choose a trending topic:",
            options=list(topic_options.keys()),
            key="topic_select"
        )
        
        if selected_topic:
            brief = topic_options[selected_topic]
            st.info(f"**Topic:** {selected_topic}")
            
            # Display viral explanation
            if brief.get('explanation'):
                st.subheader("🔥 Why It's Going Viral:")
                st.write(brief['explanation'])
            
            # Display detailed reason if available
            if brief.get('detailed_reason'):
                with st.expander("📊 Detailed Analysis"):
                    st.write(brief['detailed_reason'])
    
    with col2:
        st.header("🎨 Meme Template")
        
        # Mode selector
        template_mode = st.radio(
            "Choose template mode:",
            ["Use Existing Template", "Create New Template"],
            key="template_mode"
        )
        
        if template_mode == "Use Existing Template":
            # Display existing templates
            template_options = {}
            for template in templates:
                name = template.get('name', 'Unknown')
                explanation = template.get('explanation', 'No description available')
                template_options[name] = template
            
            selected_template = st.selectbox(
                "Choose a meme template:",
                options=list(template_options.keys()),
                key="template_select"
            )
            
            if selected_template:
                template = template_options[selected_template]
                st.info(f"**Template:** {selected_template}")
                st.caption(template.get('explanation', 'No description available'))
                
                # Display template image
                template_path = f"meme_templates/{selected_template}.jpg"
                if os.path.exists(template_path):
                    st.subheader("Template Preview:")
                    
                    # Show bounding boxes on template
                    if st.checkbox("Show Text Areas", value=True, help="Display bounding boxes where text will be placed"):
                        template_with_boxes = create_template_with_boxes(template)
                        if template_with_boxes:
                            st.image(template_with_boxes, caption=f"{selected_template} template with text areas", use_container_width=True)
                        else:
                            st.image(template_path, caption=f"{selected_template} template", use_container_width=True)
                    else:
                        st.image(template_path, caption=f"{selected_template} template", use_container_width=True)
                else:
                    st.warning(f"Template image not found: {template_path}")
                
                # Show template schema
                schema = template.get('schema', {})
                if schema:
                    st.subheader("Template Fields:")
                    for field, desc in schema.items():
                        st.text(f"• {field}: {desc.get('description', 'No description')}")
        
        else:  # Create New Template
            st.subheader("📸 Create New Meme Template")
            
            # Image source selection
            image_source = st.radio(
                "Choose image source:",
                ["Take Photo", "Upload File"],
                key="image_source"
            )
            
            uploaded_file = None
            
            if image_source == "Take Photo":
                # Camera input
                uploaded_file = st.camera_input(
                    "Take a photo for your meme template:",
                    help="Take a photo that could work as a meme template"
                )
            else:
                # File upload
                uploaded_file = st.file_uploader(
                    "Upload an image for your meme template:",
                    type=['png', 'jpg', 'jpeg'],
                    help="Upload an image that could work as a meme template"
                )
            
            # Description input
            template_description = st.text_area(
                "Describe your meme template:",
                placeholder="e.g., 'A person looking confused at a computer screen' or 'Two people having an argument'",
                help="Provide a brief description of what your meme template represents"
            )
            
            if uploaded_file and template_description:
                # Display uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded image", use_container_width=True)
                
                # Analyze button
                if st.button("🔍 Analyze Image & Create Template", type="primary"):
                    with st.spinner("Analyzing image with AI..."):
                        client = get_openai_client()
                        new_template = analyze_image_for_meme_template(image, template_description, client)
                        
                        if new_template:
                            st.success("✅ Template created successfully!")
                            
                            # Display generated template info
                            st.subheader("Generated Template:")
                            st.write(f"**Name:** {new_template.get('name', 'Unknown')}")
                            st.write(f"**Description:** {new_template.get('explanation', 'No description')}")
                            
                            # Show schema
                            schema = new_template.get('schema', {})
                            if schema:
                                st.write("**Text Fields:**")
                                for field, desc in schema.items():
                                    st.write(f"• {field}: {desc.get('description', 'No description')}")
                            
                            # Show bounding boxes on image
                            st.subheader("Template with Text Areas:")
                            template_with_boxes = create_template_with_boxes(new_template)
                            if template_with_boxes:
                                st.image(template_with_boxes, caption="Template with text areas", use_container_width=True)
                            
                            # Save template
                            if st.button("💾 Save Template", type="secondary"):
                                if save_new_template(new_template, image):
                                    st.success("🎉 Template saved successfully!")
                                    st.rerun()  # Refresh to show new template
                                else:
                                    st.error("❌ Failed to save template")
            
            # Show current template if one was just created
            if 'new_template' in locals() and new_template:
                template = new_template
                
                # Display template image
                template_path = f"meme_templates/{template.get('name', '')}.jpg"
                if os.path.exists(template_path):
                    st.subheader("Template Preview:")
                    
                    # Show bounding boxes on template
                    if st.checkbox("Show Text Areas", value=True, help="Display bounding boxes where text will be placed"):
                        template_with_boxes = create_template_with_boxes(template)
                        if template_with_boxes:
                            st.image(template_with_boxes, caption=f"{template.get('name', '')} template with text areas", use_container_width=True)
                        else:
                            st.image(template_path, caption=f"{template.get('name', '')} template", use_container_width=True)
                    else:
                        st.image(template_path, caption=f"{template.get('name', '')} template", use_container_width=True)
                else:
                    st.warning(f"Template image not found: {template_path}")
                
                # Show template schema
                schema = template.get('schema', {})
                if schema:
                    st.subheader("Template Fields:")
                    for field, desc in schema.items():
                        st.text(f"• {field}: {desc.get('description', 'No description')}")
    
    # Generate meme button
    st.markdown("---")
    
    if st.button("🎭 Generate Meme!", type="primary"):
        if not selected_topic:
            st.error("Please select a topic!")
        elif template_mode == "Use Existing Template" and not selected_template:
            st.error("Please select a template!")
        elif template_mode == "Create New Template" and not template:
            st.error("Please create a new template first!")
        else:
            with st.spinner("Generating your meme..."):
                client = get_openai_client()
                brief = topic_options[selected_topic]
                
                # Get template based on mode
                if template_mode == "Use Existing Template":
                    template = template_options[selected_template]
                
                # Generate meme content with viral context
                viral_context = brief.get('explanation', '') + " " + brief.get('detailed_reason', '')
                meme_content = generate_meme_content(selected_topic, template, client, viral_context)
                
                # Display generated content
                st.subheader("Generated Meme Content:")
                for field, content in meme_content.items():
                    st.text(f"**{field}:** {content}")
                
                # Create and display the meme image
                meme_image = create_meme_image(template, meme_content)
                
                if meme_image:
                    st.subheader("Your Meme:")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.image(meme_image, caption=f"Meme about {selected_topic}", use_container_width=True)
                    
                    # Add download button
                    from io import BytesIO
                    buf = BytesIO()
                    meme_image.save(buf, format="JPEG")
                    byte_im = buf.getvalue()
                    
                    st.download_button(
                        label="Download Meme",
                        data=byte_im,
                        file_name=f"{selected_topic}_{selected_template}_meme.jpg",
                        mime="image/jpeg"
                    )

if __name__ == "__main__":
    main()
