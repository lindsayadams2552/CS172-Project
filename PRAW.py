import praw
import json
import requests
import os
import math 
import time
# For the HTML cleaning
import re
from bs4 import BeautifulSoup
# For multithreading
from concurrent.futures import ThreadPoolExecutor

# Create the folder
folder_name = "redditFiles"
if not os.path.exists(folder_name):
    os.mkdir(folder_name)

# Remove HTML tags from raw HTML (for clean json)
# Discussion Slides 4
def clean_html(raw_html):
    clean_text = re.sub('<.*?>', '', raw_html)
    return clean_text

# Crawl HTML link in post or comment 
# (gets title and paragraph)
def fetch_page_title(url):
    try:
        # Assures reddit pages are not overlooked
        if url.startswith("/r/"):
            url = "https://www.reddit.com" + url
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

        if r.status_code == 429:
            print(f"429 Too Many Requests, sleeping now!")
            time.sleep(7)  # sleep 5 seconds
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

        r.encoding = 'utf-8'
        # prevent 429 error
        time.sleep(2)

        # Only parse if it's HTML
        if "text/html" in r.headers.get("Content-Type", ""):
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else ""
            return title
        else:
            print(f"Skipped non-HTML content at {url}")
            return None

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

# Fetch all comments in parallel
def fetch_comments(post):
    try:
        post.comments.replace_more(limit=0)
        comments_list = []
        for c in post.comments.list():  # all 100 comments
            comments_list.append(c.body)
        return comments_list
    except Exception as err:
        print(f"Comment fetch error: {err}")
        return []

# Initialize crawler/Authentication
reddit = praw.Reddit(
    client_id="SXtk1VW7Lw90s7AxtAO4yA",
    client_secret="rp6k-MH3NOjJWC3RgY16WLi3RhPUbg",
    user_agent="macOS:my172Crawler:1.0 (by /u/flurfsky)"
)

# List of subreddits to crawl
subreddits = ["books", "pcgaming", "Games", "PS4", "halo", "Hulu", "HBOMAX", "animesuggest", "horrorlit", "InternetIsBeautiful", "startrek", "booksuggestions", "MovieSuggestions", "bestofnetflix", "thesopranos", "SubredditDrama", "thesopranos", "SubredditDrama"]

# File sizing
file_idx = 0
max_size = 10 * 1024 * 1024  # 10MB
total_limit = 500 * 1024 * 1024  # 500MB total

current_path = os.path.join(folder_name, f"posts_{file_idx}.jsonl")
cur_file = open(current_path, "w", encoding="utf-8")
cur_size = 0
sum_size = 0

# Keep track of seen posts to avoid duplicates
seen_posts = set()

# Initialize labels for stream types
stream_labels = ["top", "hot", "new", "rising"]

last_printed_mb = 0

# Create a thread pool for parallel HTML and comment fetching
executor = ThreadPoolExecutor(max_workers=3)  # maximizing CPU firepower

future_to_data = []

# Crawl subreddits defined above
for sub in subreddits:
    subreddit = reddit.subreddit(sub)
    # Pair stream names with PRAW
    streams = [subreddit.top(time_filter="all"), subreddit.hot(), subreddit.new(), subreddit.rising()]

    for idx, stream in enumerate(streams):
        label = stream_labels[idx]
        for post in stream:
            # For duplication
            if post.id in seen_posts:
                continue
            seen_posts.add(post.id)

            # Data dictionary of what we are retrieving (basic post info)
            data = {
                "subreddit": sub,
                "title": post.title,
                "body": clean_html(post.selftext),
                "author": str(post.author) if post.author else "[deleted]",
                "upvotes": post.score,
                "postID": post.id,
                "postImage": post.url,
                "postUrl": post.permalink,
                "comments": [],
                "category": label
            }

            # If a reddit post contains a URL to an html page, get it and save it
            if post.url and not post.is_self:
                future_title = executor.submit(fetch_page_title, post.url)
                data["future_linkTitle"] = future_title
            # Crawl Reddit permalink if it's a self-post (for redundancy)
            elif post.is_self and post.permalink:
                try:
                    full_url = "https://www.reddit.com" + post.permalink
                    future_title = executor.submit(fetch_page_title, full_url)
                    data["future_linkTitle"] = future_title
                except Exception as e:
                    print(f"Self-post link error: {e}")
                    data["future_linkTitle"] = None
            else:
                data["future_linkTitle"] = None

            # Crawl comments
            future_comments = executor.submit(fetch_comments, post)
            data["future_comments"] = future_comments

            # Save to future list for later writing
            future_to_data.append(data)

            if sum_size >= total_limit:
                break
        if sum_size >= total_limit:
            break

# Collect all completed futures
for data in future_to_data:
    # Wait for comment fetching
    if data["future_comments"]:
        data["comments"] = data["future_comments"].result()
    # Wait for link title fetching
    if data["future_linkTitle"]:
        title_result = data["future_linkTitle"].result()
        if title_result:
            data["linkTitle"] = title_result

    # Remove futures before saving to file
    data.pop("future_comments", None)
    data.pop("future_linkTitle", None)

    # Keeps track of how much space the file is using
    line_data = json.dumps(data) + "\n"
    cur_file.write(line_data)
    cur_size += len(line_data.encode('utf-8'))
    sum_size += len(line_data.encode('utf-8'))

    # When the json file exceeds 10MB, open a new one
    if cur_size > max_size:
        cur_file.close()
        file_idx += 1
        current_path = os.path.join(folder_name, f"posts_{file_idx}.jsonl")
        cur_file = open(current_path, "w", encoding="utf-8")
        cur_size = 0

    # Keeps track of current file size in terminal so we can know when it reaches 10mb/500mb
    current_mb = sum_size / (1024 * 1024)
    if current_mb - last_printed_mb >= 0.1:
        print(f"Downloaded {current_mb:.1f} MB...")
        last_printed_mb = current_mb

cur_file.close()
executor.shutdown()
print("Crawling Done.")