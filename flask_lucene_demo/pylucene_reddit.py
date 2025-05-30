import logging, sys
import json
import time
import math
import lucene
import os

from java.nio.file import Paths
from java.lang import Float
from java.util import HashMap

from org.apache.lucene.store import NIOFSDirectory, SimpleFSDirectory
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.analysis.miscellaneous import PerFieldAnalyzerWrapper
from org.apache.lucene.document import (
    Document, Field, FieldType,
    LongPoint, StoredField
)
from org.apache.lucene.index import (
    FieldInfo, IndexWriter, IndexWriterConfig,
    IndexOptions, DirectoryReader
)
from org.apache.lucene.queryparser.classic import MultiFieldQueryParser
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.search.similarities import BM25Similarity

print(">>> LOADING pylucene_reddit from:", __file__)

# suppress all Lucene logging
logging.disable(sys.maxsize)

def load_files(directory):
    for file_name in os.listdir(directory):
        path = os.path.join(directory, file_name)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading {path}: {e}")

def create_index(index_dir, reddit_files):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)

    store = SimpleFSDirectory(Paths.get(index_dir))
    analyzer = PerFieldAnalyzerWrapper(StandardAnalyzer())
    config = IndexWriterConfig(analyzer)
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    config.setSimilarity(BM25Similarity())
    writer = IndexWriter(store, config)

    # field types
    tokenized = FieldType()
    tokenized.setStored(True)
    tokenized.setTokenized(True)
    tokenized.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

    not_tokenized = FieldType()
    not_tokenized.setStored(True)
    not_tokenized.setTokenized(False)
    not_tokenized.setIndexOptions(IndexOptions.DOCS_AND_FREQS)

    comments_field = FieldType()
    comments_field.setStored(False)
    comments_field.setTokenized(True)
    comments_field.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

    stored_only = FieldType()
    stored_only.setStored(True)
    stored_only.setTokenized(False)
    stored_only.setIndexOptions(IndexOptions.NONE)

    count = 0
    start = time.time()

    for post in reddit_files:
        doc = Document()
        doc.add(Field('Title', str(post.get('title', '')), tokenized))
        doc.add(Field('Body', str(post.get('body', '')), tokenized))
        doc.add(Field('Username', str(post.get('author', '')), not_tokenized))
        doc.add(Field('Subreddit', str(post.get('subreddit', '')), tokenized))
        doc.add(Field('PostID', str(post.get('postID', '')), not_tokenized))
        doc.add(Field('Category', str(post.get('category', '')), tokenized))
        doc.add(Field('Upvotes', str(post.get('upvotes', '')), not_tokenized))
        doc.add(Field('PostImage', str(post.get('postImage', '')), stored_only))
        doc.add(Field('PostURL', str(post.get('postUrl', '')), stored_only))

        comments = post.get('comments', [])
        if isinstance(comments, list):
            comments = "\n".join(comments)
        doc.add(Field('Comments', str(comments), comments_field))

        # --- ADD TIMESTAMP FIELD for recency scoring ---
        ts = int(post.get('created_utc', time.time()))
        doc.add(LongPoint("Timestamp", ts))    # enable numeric range queries
        doc.add(StoredField("Timestamp", ts))  # so we can read it in retrieve()

        writer.addDocument(doc)
        count += 1
        if count % 1000 == 0:
            print(f"Indexed {count} documents in {time.time() - start:.2f} sec")

    writer.close()
    print(f"Indexing complete. Total: {count} docs in {time.time() - start:.2f} sec")

def retrieve(index_dir, user_query):
    # Ranking = 0.7·BM25_score + 0.3·exp(−age_days/7)
    # where age_days = (now − Timestamp)/86400, so posts ~1 week old have recency ≈0.5

    # ensure current thread is attached if called from Flask
    vm_env = lucene.getVMEnv()
    if not vm_env.isCurrentThreadAttached():
        vm_env.attachCurrentThread()

    search_dir = NIOFSDirectory(Paths.get(index_dir))
    searcher = IndexSearcher(DirectoryReader.open(search_dir))
    searcher.setSimilarity(BM25Similarity())

    fields = ['Title', 'Body', 'Comments']
    analyzer = StandardAnalyzer()
    qp = MultiFieldQueryParser(fields, analyzer)
    query = MultiFieldQueryParser.parse(qp, user_query)

    topDocs = searcher.search(query, 30).scoreDocs
    results = []
    seen = set()

    now = time.time()
    alpha = 0.7

    for hit in topDocs:
        doc   = searcher.doc(hit.doc)
        title = doc.get("Title")
        if title in seen:
            continue
        seen.add(title)

        # compute recency (guard against missing Timestamp)
        raw_ts = doc.get("Timestamp")
        if raw_ts is None:
            ts = now
        else:
            ts = float(raw_ts)

        age_days = (now - ts) / 86400.0
        recency  = math.exp(-age_days / 7.0)
        final_score = alpha * hit.score + (1 - alpha) * recency

        results.append({
            "score":       hit.score,
            "final_score": final_score,
            "title":       title,
            "body":        doc.get("Body"),
            "subreddit":   doc.get("Subreddit"),
            "username":    doc.get("Username"),
            "postID":      doc.get("PostID"),
            "url":         doc.get("PostURL")
        })

    # sort by combined score
    results.sort(key=lambda d: d["final_score"], reverse=True)
    return results[:10]

if __name__ == "__main__":
    if lucene.getVMEnv() is None:
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    # create_index('reddit_lucene_index/', load_files("redditFiles/"))
    print(retrieve('reddit_lucene_index/', 'senate'))