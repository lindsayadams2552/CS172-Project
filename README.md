# CS172 Reddit Pop Culture Search Engine  
This project was built in two phases as part of **CS172 – Information Retrieval**. It focuses on **collecting Reddit data (Part A)** and building a **searchable web interface (Part B)** for exploring pop culture content across multiple subreddits.  

---

## Project Structure
- **Part A – Reddit Post Collector** (`PRAW.py`, JSON data files)  
- **Part B – Search Engine & Web Interface** (`pylucene_reddit.py`, `flask_lucene_demo/`)  
- **Reports**: Detailed writeups for both parts are included in this repo.  
  - [Part A: Reddit Post Collector](Reports/PartA_RedditPostCollector_Report.pdf)
  - [Part B: Search Interface](Reports/PartB_SearchInterface_Report.pdf)

---

## Part A: Reddit Post Collector

### Goal
Collect ~500MB of Reddit posts & comments from pop culture subreddits (movies, TV, music, gaming, celebrities, etc.) to serve as the dataset for our search engine.  

### Features
- Crawler Architecture  
- PRAW API for authentication & streaming posts.  
- Subreddit Crawler pulls from `top`, `hot`, `new`, `rising`.  
- BeautifulSoup fetches HTML `<title>` tags for external links.  
- Multithreading with `ThreadPoolExecutor` for faster crawling.  
- Duplicate handling via `seen_posts` set.  
- Data Storage:  
  - JSONL format, 10MB per file, up to 500MB total.  
  - Stores subreddit, title, body, author, upvotes, permalink, comments, category, and external link titles.  
- Data Structures: dictionaries (post metadata), sets (deduplication), lists (subreddits, streams, comments).  

### Run Instructions
1. Ideally, you should include a crawler.bat (Windows) or crawler.sh (Unix/Linux) executable file that takes as input all necessary parameters.
2. Install python3
3. Install python libraries: pip install praw requests beautifulsoup4
4. Change directory into CS172-Project: cd CS172-Project
5. Run crawler: python3 PRAW.py

--- 

## Part B: Build Index & Search Interface
### Goal
Index the collected Reddit dataset using PyLucene and build a Flask-based web application that allows searching by relevance, recency, upvotes, or combined.

### Features
- Indexing with PyLucene
- Inverted index stores title, body, comments, upvotes, and timestamp.
- BM25Similarity for relevance ranking.
- Indexing flexibility: title/body tokenized, comments indexed, upvotes numeric.
- Search & Ranking
- User queries matched across title, body, and comments.

### Ranking Modes
- **Relevance** (BM25)
- **Time** (newer posts rank higher)
- **Votes** (upvote counts, scaled)
- **Combined** (weighted formula: relevance + recency + votes).

## Web Interface (Flask)
- `input.html` → search form with ranking options.
- `output.html` → top 10 results, showing snippets, metadata, and Reddit links.

### Run Instructions
1. Ideally, you should include an indexer.bat (Windows) or indexer.sh (Unix/Linux) executable file that takes as input all necessary parameters Example: [user@server] ./indexer.sh <output-dir>
2. Install python3
3. Change directory into CS172-Project: cd CS172-Project
4. Run the pylucene file (to test retrieval or build the index): python3 pylucene_reddit.py
5. This will create __pycache__ folder: change directory into flask_lucene_demo: cd flask_lucene_demo
6. Run the flask file: python3 flask_demo.py
7. The app will launch locally on http://localhost:8888

---

## Demo
- Screenshots & example queries are included in the reports.
- Video Demo: Included in report
  - [Part A: Reddit Post Collector](Reports/PartA_RedditPostCollector_Report.pdf)
  - [Part B: Search Interface](Reports/PartB_SearchInterface_Report.pdf)

---

## Team Contributors
- Lindsay Adams
- Ananya Sood
- Selina Wu
- Nada Salib
- Rhea Niraj

---

## Summary
This project demonstrates the full pipeline of an information retrieval system:
- Data Collection – 500MB Reddit dataset (JSON).
- Indexing – PyLucene inverted index.
- Search & Ranking – BM25 + recency + upvotes.
- Web Application – Flask frontend for interactive querying.

---

## Motivation / End Goal of the Search Engine
The goal of our search engine is to provide easy access to information about pop culture across a wide range of Reddit communities. Pop culture was chosen as the central theme because it is broad and dynamic, spanning movies, television, gaming, music, celebrities, and countless online discussions. By collecting 500MB of raw Reddit data from popular subreddits, we aimed to build a diverse and specialized dataset that reflects the latest conversations and trends.  

Our motivation stems from the fact that pop culture discussions are often scattered across many subreddits, posts, and comment threads, making them difficult to track. Valuable insights and opinions are easily buried, forcing users to spend significant time browsing multiple communities.  

This project addresses that problem by centralizing and indexing Reddit content into a single searchable system. The search engine eliminates the need for manual browsing and enables users to quickly find relevant posts, opinions, and discussions. With built-in categorization and filtering, the system improves search quality and ensures that users can access targeted, high-value content with minimal effort.  

---
