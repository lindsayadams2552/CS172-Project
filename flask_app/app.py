from flask import Flask, request, render_template
import lucene
from sys import path
from os.path import dirname, abspath

# Allow importing from parent folder
path.append(dirname(dirname(abspath(__file__))))
from pylucene_reddit import retrieve

# Only init the JVM once if it's not already running
if lucene.getVMEnv() is None:
    lucene.initVM(vmargs=['-Djava.awt.headless=true'])

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('search.html')

@app.route('/results', methods=['POST'])
def results():
    # Attach thread before Lucene usage
    vm_env = lucene.getVMEnv()
    if not vm_env.isCurrentThreadAttached():
        vm_env.attachCurrentThread()

    # query = request.form['query']
    user_query = request.form.get('query', '').strip()
    if not user_query:
        return "Error: No query received", 400
    results = retrieve('../reddit_lucene_index/', user_query)
    return render_template('results.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)