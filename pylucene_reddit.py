import logging, sys
import json
import time
import lucene
import os

from java.nio.file import Paths
from java.lang import Float
from java.util import HashMap

from org.apache.lucene.store import NIOFSDirectory, SimpleFSDirectory
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.analysis.miscellaneous import PerFieldAnalyzerWrapper
from org.apache.lucene.document import Document, Field, FieldType
from org.apache.lucene.index import (
    FieldInfo, IndexWriter, IndexWriterConfig,
    IndexOptions, DirectoryReader
)
from org.apache.lucene.queryparser.classic import MultiFieldQueryParser  # correct parser class
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.search.similarities import BM25Similarity

logging.disable(sys.maxsize)

# load in reddit json data
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

    # handle Lucene fields that will be tokenized (match doesn't have to be exact)
    tokenized = FieldType()
    tokenized.setStored(True)
    tokenized.setTokenized(True)
    tokenized.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

    # handle Lucene fields that won't be tokenized (for exact matches)
    not_tokenized = FieldType()
    not_tokenized.setStored(True)
    not_tokenized.setTokenized(False)
    not_tokenized.setIndexOptions(IndexOptions.DOCS_AND_FREQS)

    # comments field (don't want to store it bc it's rly big)
    comments_field = FieldType()
    comments_field.setStored(False)
    comments_field.setTokenized(True)
    comments_field.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)

    # handle Lucene fields that are only stored (not tokenized or indexed)
    stored_only = FieldType()
    stored_only.setStored(True)
    stored_only.setTokenized(False)
    stored_only.setIndexOptions(IndexOptions.NONE)

    # Outputs to terminal to help see how much was processed
    count = 0
    start = time.time()

    # added field types for indexing (from data dictionary)
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

        # Outputs to terminal to help see how much was processed
        writer.addDocument(doc)
        count += 1
        if count % 1000 == 0:
            print(f"Indexed {count} documents in {time.time() - start:.2f} sec")

    writer.close()
    print(f"Indexing complete. Total: {count} docs in {time.time() - start:.2f} sec")

# retrieves search results using Lucene query
def retrieve(index_dir, user_query):
    from org.apache.lucene.queryparser.classic import MultiFieldQueryParser  # do it here to avoid shadowing

    vm_env = lucene.getVMEnv()
    if not vm_env.isCurrentThreadAttached():
        vm_env.attachCurrentThread()

    search_dir = NIOFSDirectory(Paths.get(index_dir))
    searcher = IndexSearcher(DirectoryReader.open(search_dir))
    searcher.setSimilarity(BM25Similarity())

    fields = ['Title', 'Body', 'Comments']
    analyzer = StandardAnalyzer()
    qparser = MultiFieldQueryParser(fields, analyzer)  # DO NOT name this `MultiFieldQueryParser` again

    query = qparser.parse(user_query.strip())  # use .parse() correctly on the instance

    topDocs = searcher.search(query, 10).scoreDocs
    results = []
    for hit in topDocs:
        doc = searcher.doc(hit.doc)
        results.append({
            "score": hit.score,
            "title": doc.get("Title"),
            "body": doc.get("Body"),
            "subreddit": doc.get("Subreddit"),
            "username": doc.get("Username"),
            "postID": doc.get("PostID"),
            "url": doc.get("PostURL")
        })
    return results

# main indexing entry point
if __name__ == "__main__":
    if lucene.getVMEnv() is None:
        lucene.initVM(vmargs=['-Djava.awt.headless=true'])
    create_index('reddit_lucene_index/', load_files("redditFiles/"))