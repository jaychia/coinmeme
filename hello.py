import requests
import os
from pytrends.request import TrendReq # type: ignore
import pandas as pd
import json

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
        
        for i, row in enumerate(top_25.itertuples(index=False)):
            # Create a JSON for each trend
            print(row)
            trend = row.Trends
            start_trending = row.Started
            end_trending = row.Ended
            image_prompt = [] # fetch multiple images from flickr based on trend search word

            with open(f"meme_briefs/brief_{i}.json", "w", encoding="utf-8") as f:
                data = {
                    "search": trend,
                    "explanation": "",
                    "start_trending": start_trending,
                    "end_trending": end_trending,
                    "image_prompt": image_prompt
                }
                json.dump(data, f, indent=4)  
        


            

        


if __name__ == "__main__":
    main()
    generate_meme_brief()
