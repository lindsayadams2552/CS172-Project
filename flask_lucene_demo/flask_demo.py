import lucene
import os
import sys
from flask import request, Flask, render_template, redirect, url_for
#from pylucene_reddit import retrieve  # Import retrieve function
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # ensures current dir is in path

from pylucene_reddit import retrieve
app = Flask(__name__)

# Ensure the JVM is initialized
lucene.initVM(vmargs=['-Djava.awt.headless=true'])

@app.route("/")
def home():
    return redirect(url_for("input"))

@app.route("/input", methods=['GET'])
def input():
    return render_template('input.html')

@app.route("/output", methods=['POST'])
def output():
    form_data = request.form
    query = form_data['query']
    print(f"Query received: {query}")

    # Attach thread to JVM
    lucene.getVMEnv().attachCurrentThread()

    # Use your Reddit index directory
    docs = retrieve('reddit_lucene_index/', query)

    return render_template('output.html', lucene_output=docs)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
