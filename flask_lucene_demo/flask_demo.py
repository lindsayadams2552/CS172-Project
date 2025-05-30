import lucene, os, sys
from flask import request, Flask, render_template, redirect, url_for
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pylucene_reddit import retrieve

app = Flask(__name__)
lucene.initVM(vmargs=['-Djava.awt.headless=true'])

@app.route("/")
def home():
    return redirect(url_for("input"))

@app.route("/input", methods=['GET'])
def input():
    return render_template('input.html')

@app.route("/output", methods=['POST'])
def output():
    form = request.form
    query = form['query']
    rank_by = form.get('rank_by', 'combined')
    try:
        w_r = float(form.get('w_relevance', 0.5))
        w_t = float(form.get('w_time',      0.3))
        w_v = float(form.get('w_votes',     0.2))
    except ValueError:
        w_r, w_t, w_v = 0.5, 0.3, 0.2

    # attach JVM to this thread
    lucene.getVMEnv().attachCurrentThread()

    docs = retrieve(
        'reddit_lucene_index/',
        query,
        rank_by=rank_by,
        weights=(w_r, w_t, w_v)
    )
    return render_template('output.html', lucene_output=docs)

if __name__ == "__main__":
    app.run(port=8888, debug=True)