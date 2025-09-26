# 🎭 Meme Generator

A Streamlit app that generates hilarious memes by combining trending topics with popular meme templates using OpenAI's API.

## Features

- **Topic Selection**: Choose from trending topics loaded from `meme_briefs/` directory
- **Template Selection**: Pick from various meme templates defined in `memedb.jsonl`
- **AI-Powered Content**: Uses OpenAI to generate funny, relevant text for your memes
- **Image Processing**: Automatically overlays text on meme templates
- **Download**: Save your generated memes as JPEG files

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API Key**:
   - Get your OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Set the environment variable: `export OPENAI_API_KEY="your-api-key-here"`

3. **Run the App**:
   ```bash
   streamlit run app.py
   ```

## Usage

1. **Select a Topic**: Choose from the trending topics in the left column
2. **Pick a Template**: Select a meme template from the right column
3. **Generate**: Click the "Generate Meme!" button
4. **Download**: Save your meme using the download button

## File Structure

- `app.py` - Main Streamlit application
- `meme_briefs/` - JSON files containing trending topics
- `meme_templates/` - JPG images of meme templates
- `memedb.jsonl` - JSON schema definitions for meme templates
- Environment variable `OPENAI_API_KEY` - Your OpenAI API key

## Meme Templates Supported

- Distracted Boyfriend
- Two Buttons
- One Does Not Simply
- Change My Mind
- Batman Slapping Robin
- Kermit Sipping Tea
- Left Exit Ramp
- Running Away Balloon
- UNO Draw 25
- Sad Pablo Escobar
- Bernie Once Again

## Customization

You can add new meme templates by:
1. Adding the template image to `meme_templates/`
2. Adding the schema definition to `memedb.jsonl`
3. Updating the `get_text_positions()` function in `app.py` to define text placement

## Requirements

- Python 3.13+
- OpenAI API key
- Internet connection for API calls