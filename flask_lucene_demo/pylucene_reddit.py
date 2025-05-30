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
from org.apache.lucene.document import (Document, Field, FieldType, LongPoint, StoredField)
from org.apache.lucene.index import (FieldInfo, IndexWriter, IndexWriterConfig, IndexOptions, DirectoryReader)
from org.apache.lucene.queryparser.classic import MultiFieldQueryParser
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.search.similarities import BM25Similarity

print(">>> LOADING pylucene_reddit from:", __file__)
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
    cfg = IndexWriterConfig(analyzer)
    cfg.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
    cfg.setSimilarity(BM25Similarity())
    writer = IndexWriter(store, cfg)

    # Define field types…
    tokenized = FieldType(); tokenized.setStored(True);  tokenized.setTokenized(True)
    tokenized.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)
    not_tokenized = FieldType(); not_tokenized.setStored(True); not_tokenized.setTokenized(False)
    not_tokenized.setIndexOptions(IndexOptions.DOCS_AND_FREQS)
    comments_field= FieldType(); comments_field.setStored(False);comments_field.setTokenized(True)
    comments_field.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)
    stored_only = FieldType(); stored_only.setStored(True); stored_only.setTokenized(False)
    stored_only.setIndexOptions(IndexOptions.NONE)

    count = 0
    start = time.time()

    for post in reddit_files:
        doc = Document()
        doc.add(Field('Title', str(post.get('title','')), tokenized))
        doc.add(Field('Body', str(post.get('body','')), tokenized))
        doc.add(Field('Username', str(post.get('author','')),not_tokenized))
        doc.add(Field('Subreddit',str(post.get('subreddit','')),tokenized))
        doc.add(Field('PostID', str(post.get('postID','')), not_tokenized))
        doc.add(Field('Category', str(post.get('category','')),tokenized))
        doc.add(Field('Upvotes', str(post.get('upvotes','')), not_tokenized))
        doc.add(Field('PostImage',str(post.get('postImage','')),stored_only))
        doc.add(Field('PostURL', str(post.get('postUrl','')), stored_only))

        comments = post.get('comments', [])
        if isinstance(comments, list):
            comments = "\n".join(comments)
        doc.add(Field('Comments', str(comments), comments_field))

        # timestamp for recency
        ts = int(post.get('created_utc', time.time()))
        doc.add(LongPoint("Timestamp", ts))
        doc.add(StoredField("Timestamp", ts))

        writer.addDocument(doc)
        count += 1
        if count % 1000 == 0:
            print(f"Indexed {count} in {time.time()-start:.2f}s")

    writer.close()
    print(f"Indexing complete: {count} docs in {time.time()-start:.2f}s")

def retrieve(index_dir, user_query, rank_by='combined', weights=(0.5, 0.3, 0.2)):
             
    # rank_by: 'combined'|'relevance'|'time'|'votes'
    # weights: tuple of (w_relevance, w_time, w_votes) used only when rank_by=='combined'
    
    vm_env = lucene.getVMEnv()
    if not vm_env.isCurrentThreadAttached():
        vm_env.attachCurrentThread()

    searcher = IndexSearcher(DirectoryReader.open(NIOFSDirectory(Paths.get(index_dir))))
    searcher.setSimilarity(BM25Similarity())

    qp = MultiFieldQueryParser(['Title','Body','Comments'], StandardAnalyzer())
    query = MultiFieldQueryParser.parse(qp, user_query)
    topDocs = searcher.search(query, 30).scoreDocs

    # normalize weights
    w_r, w_t, w_v = weights
    total = w_r + w_t + w_v
    if total > 0:
        w_r, w_t, w_v = w_r/total, w_t/total, w_v/total
    else:
        w_r, w_t, w_v = 0.5, 0.3, 0.2

    now = time.time()
    results = []

    seen = set()
    for hit in topDocs:
        doc = searcher.doc(hit.doc)
        title = doc.get("Title")
        if title in seen:
            continue
        seen.add(title)

        # build subscores
        bm25 = hit.score
        raw_ts = doc.get("Timestamp")
        ts = now if raw_ts is None else float(raw_ts)
        age_days = (now - ts) / 86400.0
        recency = math.exp(-age_days / 7.0)
        votes = float(doc.get("Upvotes") or 0)
        votes_sc = math.log1p(votes)

        # choose final score
        if rank_by == 'relevance':
            final = bm25
        elif rank_by == 'time':
            final = recency
        elif rank_by == 'votes':
            final = votes_sc
        else:  # combined
            final = w_r * bm25 + w_t * recency + w_v * votes_sc

        results.append({
            "score": bm25,
            "recency": recency,
            "votes_score": votes_sc,
            "final_score": final,
            "title": title,
            "body": doc.get("Body"),
            "subreddit": doc.get("Subreddit"),
            "username": doc.get("Username"),
            "postID": doc.get("PostID"),
            "url": doc.get("PostURL")
        })

    results.sort(key=lambda d: d["final_score"], reverse=True)
    return results[:10]

if __name__ == "__main__":
    if lucene.getVMEnv() is None:
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    # create_index('reddit_lucene_index/', load_files("redditFiles/"))
    print(retrieve('reddit_lucene_index/', 'senate'))
