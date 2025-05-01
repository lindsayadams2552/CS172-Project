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
subreddit = reddit.subreddit("AskReddit+funny+worldnews+gaming+science+todayilearned+movies+technology+news")

# File sizing
index = 0
max_file_size = 10 * 1024 * 1024  # 10MB
largest_file_size = 500 * 1024 * 1024  # 500MB

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

        if post.url and not post.is_self:
            html = getLink(post.url)
            if html:
                post_data["linkTitle"] = html

        line = json.dumps(post_data) + "\n"
        line_bytes = len(line.encode('utf-8'))

        if current_size + line_bytes > max_file_size:
            current_file.close()
            index += 1
            current_file = open(os.path.join(dataFolder, f"posts_{index}.jsonl"), "w", encoding="utf-8")
            current_size = 0

        current_file.write(line)
        current_size += line_bytes
        total_size += line_bytes
        print(f"Collected {total_size / (1024 * 1024):.2f} MB so far...", end="\r")

        if total_size >= largest_file_size:
            break
    if total_size >= largest_file_size:
        break

current_file.close()
print("Crawling complete.")

#Search Engine Stuff
def load_posts(folder):
    posts = []
    for filename in os.listdir(folder):
        if filename.endswith(".jsonl"):
            with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
                for line in f:
                    post = json.loads(line)
                    posts.append(post)
    return posts

def score_post(post, query):
    query = query.lower()
    title = post.get("title", "").lower()
    body = post.get("body", "").lower()
    category = post.get("category", "").lower()
    
    title_match = query in title
    body_match = query in body
    category_match = query in category

    upvotes_score = math.log(post["upvotes"] + 1)  # avoid log(0)

    # Give weights
    score = 5 * title_match + 2 * body_match + 1 * category_match + upvotes_score
    return score

def search_posts(posts, query):
    query = query.strip().lower()

    if query.startswith("user:"):
        username = query.split(":", 1)[1].strip()
        return [p for p in posts if p["author"].lower() == username]

    elif query == "trending":
        return sorted(posts, key=lambda p: p["upvotes"], reverse=True)[:20]

    elif query == "new":
        return posts[-20:]  # assumes they were saved in order

    else:
        scored = [(score_post(p, query), p) for p in posts]
        scored = [item for item in scored if item[0] > 0]
        return [p for _, p in sorted(scored, key=lambda x: x[0], reverse=True)]

# Load posts and search in CLI
posts = load_posts(dataFolder)

while True:
    user_query = input("\nSearch Reddit (or type 'exit'): ").strip()
    if user_query.lower() == "exit":
        break

    results = search_posts(posts, user_query)
    print(f"\nTop {min(len(results), 10)} results:")
    for post in results[:10]:
        print(f"Title: {post['title']}\nUpvotes: {post['upvotes']}, Author: {post['author']}\n---")
