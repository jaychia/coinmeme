#!/usr/bin/env python3
"""
Simple script to run the Streamlit app with proper configuration
"""

import subprocess
import sys
import os

def main():
    """Run the Streamlit app"""
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit is installed")
    except ImportError:
        print("❌ Streamlit not found. Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY environment variable not set.")
        print("   Please set it with: export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Run the app
    print("🚀 Starting Meme Generator app...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])

if __name__ == "__main__":
    main()
