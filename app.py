from flask import Flask, render_template, request
from flask.ext.sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)

from models import Sample, SampleSet, TimePlace, SampleProperty, Annotation

@app.route('/')
def index():
    samples, table = Annotation.rpkm_table()
    function_classes = ["COG", "PFAM", "TIGRFAM"]
    return render_template('index.html', table=table, samples=samples, function_classes=function_classes)

@app.route('/ajax/function_classes_table.html')
def function_classes_table():
    button_id = request.args.get('button_id', '')
    if button_id != '' and button_id.startswith('only_'):
        function_class = button_id.replace('only_', '')
        function_class = function_class.lower()
    samples, table = Annotation.rpkm_table(function_class=function_class)
    return render_template('function_classes_table.html', table=table, samples=samples, button_id=button_id)

if __name__ == '__main__':
    app.run()
