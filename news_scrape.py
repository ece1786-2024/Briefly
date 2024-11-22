# selenium >= 4.6
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options # If cloudflare issues pop up
# Logging for selenium errors
import logging
logging.basicConfig(level=logging.DEBUG)

from newspaper import Article # use instead of bs4 to extract stuff

import time
import uuid
import pandas as pd
import os
import datetime

def get_article(url, category, csv_path):
    # Set up selenium webdriver with Chrome, add Options if we run into cloudflare etc.
    driver = webdriver.Chrome(service=Service())
    # Load the page with selenium and parse with newspaper3k
    driver.get(url)
    time.sleep(3)  # loading time

    # Get html using selenium
    html = driver.page_source
    driver.quit()

    # Use newspaper3k to parse the HTML
    article = Article(url)
    article.set_html(html)
    article.parse()

    # Extract information
    article_id = str(uuid.uuid4())
    date_of_article = article.publish_date.strftime('%Y-%m-%d') if article.publish_date else datetime.datetime.now().strftime('%Y-%m-%d')
    title = article.title
    body = article.text
    data = {
        "ID": [article_id],
        "Date of Article": [date_of_article],
        "Category": [category],
        "Title": [title],
        "Body": [body],
        "URL": [url]
    }
    df = pd.DataFrame(data)

    # Check if CSV file exists and handle dupes
    if os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path)
        
        # Check if URL already exists
        if url in existing_df['URL'].values:
            print("Duplicate article found based on URL. Skipping...")
            return None

        # Append
        df.to_csv(csv_path, mode='a', header=False, index=False)
    else: # Create a new CSV 
        df.to_csv(csv_path, index=False)
    
    print(f"Article '{title}' saved to {csv_path}.")
    return df