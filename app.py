# app.py
from flask import Flask, render_template, jsonify
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/jobs')
def get_jobs():
    with open('applications.json') as f:
        jobs = json.load(f)
    return jsonify(sorted(jobs, key=lambda x: float(x['match_score']), reverse=True))

if __name__ == '__main__':
    app.run(debug=True)