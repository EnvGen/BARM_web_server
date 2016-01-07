from flask import Flask, render_template
from flask.ext.sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)

from models import Sample, SampleSet, TimePlace, SampleProperty, Annotation

@app.route('/')
def index():
    samples, table = Annotation.rpkm_table()
    return render_template('index.html', table=table, samples=samples)

if __name__ == '__main__':
    app.run()
