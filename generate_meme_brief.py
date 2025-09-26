import requests
import os
from pytrends.request import TrendReq # type: ignore
import pandas as pd
import json
from dotenv import load_dotenv

def main():
    print("Hello from coinmeme!")

def generate_meme_brief():
    # pull top trends from google trends and create briefs per trend 

    if not os.path.exists("meme_briefs"):
        os.mkdir("meme_briefs")

    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        trending_df = pytrends.trending_searches(pn='united_states')

        # Get top 25 trending search keywords
        top_25 = trending_df.head(25)

        print(top_25)
    except:
        csv_filename = "meme_briefs/trending_searches_fallback.csv"
        df = pd.read_csv(csv_filename)
        top_25 = df.head(25)

        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("CSE_ID")
        num_results = 3

        for i, row in enumerate(top_25.itertuples(index=False)):
            # Create a JSON for each trend
            trend = row.Trends
            start_trending = row.Started
            end_trending = row.Ended
            description = row.Description

            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": api_key,
                "cx": cse_id,
                "q": trend,
                "searchType": "image",
                "num": num_results
            }

            response = requests.get(url, params=params)
            data = response.json()

            image_prompt = [item["link"] for item in data.get("items", [])] # fetch multiple images from google custom search based on trend search word

            with open(f"meme_briefs/brief_{i}.json", "w", encoding="utf-8") as f:
                data = {
                    "search": trend,
                    "explanation": description,
                    "start_trending": start_trending,
                    "end_trending": end_trending,
                    "google_image_prompt": image_prompt
                }
                json.dump(data, f, indent=4) 
        


if __name__ == "__main__":
    load_dotenv()
    main()
    generate_meme_brief()
