import praw
import json
import requests
import os
import math
from bs4 import BeautifulSoup

# Create the folder
dataFolder = "redditFiles"
os.makedirs(dataFolder, exist_ok=True)

# Crawl HTML link in post or comment
def getLink(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.title.string if soup.title else None
    except Exception as e:
        print(f"Error retrieving link from {url}: {e}")
        return None

# Initialize crawler/Authentication
reddit = praw.Reddit(
    client_id="SXtk1VW7Lw90s7AxtAO4yA",
    client_secret="rp6k-MH3NOjJWC3RgY16WLi3RhPUbg",
    user_agent="macOS:my172Crawler:1.0 (by /u/flurfsky)"
)

# Subreddits
subreddit = reddit.subreddit("AskReddit+Science")

# File sizing
index = 0
max_file_size = 10 * 1024 * 1024  # 10MB
largest_total_size = 500 * 1024 * 1024  # 500MB

current_file = open(os.path.join(dataFolder, f"posts_{index}.jsonl"), "w", encoding="utf-8")
current_size = 0
total_size = 0

# Pair stream names with PRAW
stream_pairs = [
    ("top", subreddit.top(time_filter="all", limit=None)),
    ("hot", subreddit.hot(limit=None)),
    ("new", subreddit.new(limit=None)),
    ("rising", subreddit.rising(limit=None))
]

for stream_name, stream in stream_pairs:
    for post in stream:
        # Data dictionary of what we are retrieving
        post_data = {
            "body": post.selftext,
            "title": post.title,
            "postID": post.id,
            "upvotes": post.score,
            "postImage": post.url,
            "postUrl": post.permalink,
            "author": str(post.author),
            "comments": [],
            "category": stream_name
        }

        # If a reddit post contains a URL to an html page, obtain/save info on that page
        if post.url and not post.is_self:
            html = getLink(post.url)
            if html:
                post_data["linkTitle"] = html #saves link to data dictionary

        # Crawl comments
        try:
            post.comments.replace_more(limit=0)
            comments = []
            for comment in post.comments.list():
                comments.append(comment.body)
                post_data["comments"] = comments
        except Exception as e:
            print(f"Error fetching comments for post {post.id}: {e}")


        # Keeps track of how much space the file is using
        line = json.dumps(post_data) + "\n"
        line_bytes = len(line.encode('utf-8'))
        # When the json file exceeds 10MB, open a new one
        if current_size + line_bytes > max_file_size:
            current_file.close()
            index += 1
            current_file = open(os.path.join(dataFolder, f"posts_{index}.jsonl"), "w", encoding="utf-8")
            current_size = 0

        # Keeps track of current file size in terminal so we can know when it reaches 10mb/500mb
        current_file.write(line)
        current_size += line_bytes
        total_size += line_bytes
        print(f"Collected {total_size / (1024 * 1024):.2f} MB so far...", end="\r")

        if total_size >= largest_total_size:
            break
    if total_size >= largest_total_size:
        break

current_file.close()
print("Crawling has finished.")
