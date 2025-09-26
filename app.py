import streamlit as st
import json
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import openai
from typing import Dict, List, Any

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
            max_tokens=500
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
        st.header("🎨 Select a Meme Template")
        
        # Display templates
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
    
    # Generate meme button
    st.markdown("---")
    
    if st.button("🎭 Generate Meme!", type="primary"):
        if not selected_topic or not selected_template:
            st.error("Please select both a topic and a template!")
        else:
            with st.spinner("Generating your meme..."):
                client = get_openai_client()
                brief = topic_options[selected_topic]
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
