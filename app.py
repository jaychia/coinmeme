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
    """Load all meme briefs from the meme_briefs directory"""
    briefs = []
    brief_dir = "meme_briefs"
    
    if not os.path.exists(brief_dir):
        return briefs
    
    for filename in sorted(os.listdir(brief_dir)):
        if filename.startswith("brief_") and filename.endswith(".json"):
            filepath = os.path.join(brief_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    brief = json.load(f)
                    brief['filename'] = filename
                    briefs.append(brief)
            except Exception as e:
                st.error(f"Error loading {filename}: {e}")
    
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

def generate_meme_content(topic: str, template: Dict[str, Any], client: openai.OpenAI) -> Dict[str, str]:
    """Generate meme content using OpenAI"""
    
    # Create prompt for OpenAI
    schema = template.get('schema', {})
    explanation = template.get('explanation', '')
    
    prompt = f"""
    Create a meme about "{topic}" using the "{template['name']}" template.
    
    Template explanation: {explanation}
    
    Template schema: {json.dumps(schema, indent=2)}
    
    Generate appropriate text for each field in the schema. Make it funny and relevant to the topic "{topic}".
    Return only a JSON object with the field names as keys and the generated text as values.
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
        # Try to parse JSON from the response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a simple response
            return {key: f"Generated text for {topic}" for key in schema.keys()}
            
    except Exception as e:
        st.error(f"Error generating meme content: {e}")
        return {key: f"Error generating text" for key in schema.keys()}

def create_meme_image(template_name: str, meme_content: Dict[str, str]) -> Image.Image:
    """Create the final meme image by overlaying text on the template"""
    
    # Load the template image
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
            font_large = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
            font_medium = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            font_small = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
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
        
        # Define text positions based on template type
        text_positions = get_text_positions(template_name, width, height)
        
        # Add text overlay based on template
        for field, content in meme_content.items():
            if field in text_positions:
                pos = text_positions[field]
                font = pos.get('font', font_medium)
                color = pos.get('color', 'white')
                stroke_color = pos.get('stroke_color', 'black')
                stroke_width = pos.get('stroke_width', 2)
                
                # Draw text with stroke for better visibility
                draw.text(
                    pos['position'], 
                    content, 
                    font=font, 
                    fill=color,
                    stroke_fill=stroke_color,
                    stroke_width=stroke_width,
                    anchor="mm"
                )
        
        return img
        
    except Exception as e:
        st.error(f"Error creating meme image: {e}")
        return None

def get_text_positions(template_name: str, width: int, height: int) -> Dict[str, Dict]:
    """Define text positions for different meme templates"""
    
    positions = {}
    
    if template_name == "distracted_boyfriend":
        positions = {
            "boyfriend": {"position": (width//2, height//2), "font": "large", "color": "white"},
            "girlfriend": {"position": (width//4, height//2), "font": "medium", "color": "white"},
            "other_girl": {"position": (3*width//4, height//2), "font": "medium", "color": "white"}
        }
    elif template_name == "two_buttons":
        positions = {
            "option_1": {"position": (width//4, height//2), "font": "medium", "color": "white"},
            "option_2": {"position": (3*width//4, height//2), "font": "medium", "color": "white"}
        }
    elif template_name == "one_does_not_simply":
        positions = {
            "task": {"position": (width//2, height//2), "font": "large", "color": "white"}
        }
    elif template_name == "change_my_mind":
        positions = {
            "statement": {"position": (width//2, height//2), "font": "medium", "color": "black"}
        }
    elif template_name == "batman_slapping_robin":
        positions = {
            "robin_says": {"position": (width//4, height//2), "font": "medium", "color": "white"},
            "batman_replies": {"position": (3*width//4, height//2), "font": "medium", "color": "white"}
        }
    elif template_name == "kermit_sipping_tea":
        positions = {
            "observation": {"position": (width//2, height//2), "font": "medium", "color": "white"}
        }
    elif template_name == "left_exit_ramp":
        positions = {
            "main_road": {"position": (width//2, height//3), "font": "medium", "color": "white"},
            "exit_ramp": {"position": (width//2, 2*height//3), "font": "medium", "color": "white"}
        }
    elif template_name == "running_away_balloon":
        positions = {
            "person": {"position": (width//4, height//2), "font": "medium", "color": "white"},
            "balloon": {"position": (3*width//4, height//2), "font": "medium", "color": "white"}
        }
    elif template_name == "uno_draw_25":
        positions = {
            "action": {"position": (width//2, height//3), "font": "medium", "color": "white"},
            "consequence": {"position": (width//2, 2*height//3), "font": "large", "color": "red"}
        }
    elif template_name == "sad_pablo_escobar":
        positions = {
            "feeling_or_situation": {"position": (width//2, height//2), "font": "medium", "color": "white"}
        }
    elif template_name == "bernie_once_again":
        positions = {
            "request": {"position": (width//2, height//2), "font": "medium", "color": "white"}
        }
    
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
    
    # Update positions with actual font objects
    for field, pos in positions.items():
        if 'font' in pos and isinstance(pos['font'], str):
            pos['font'] = font_map.get(pos['font'], font_medium)
    
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
            if brief.get('start_trending'):
                st.caption(f"Started trending: {brief['start_trending']}")
    
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
                
                # Generate meme content
                meme_content = generate_meme_content(selected_topic, template, client)
                
                # Display generated content
                st.subheader("Generated Meme Content:")
                for field, content in meme_content.items():
                    st.text(f"**{field}:** {content}")
                
                # Create and display the meme image
                meme_image = create_meme_image(selected_template, meme_content)
                
                if meme_image:
                    st.subheader("Your Meme:")
                    st.image(meme_image, caption=f"Meme about {selected_topic}", use_column_width=True)
                    
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
