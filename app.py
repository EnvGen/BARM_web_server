from flask import Flask, render_template, request
from flask.ext.sqlalchemy import SQLAlchemy
from forms import FunctionClassFilterForm
import os

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)

from models import Sample, SampleSet, TimePlace, SampleProperty, Annotation

@app.route('/', methods=['GET', 'POST'])
def index():
    form = FunctionClassFilterForm()
    form.function_class.choices = [('cog', 'Cog'),
                    ('pfam', 'Pfam'),
                    ('tigrfam', 'TigrFam'),
                    ('all', 'All')
                ]

    if form.validate_on_submit():
        function_class = form.function_class.data
        if function_class == 'all':
            function_class = None
        limit = form.limit.data
        if limit == 'all':
            limit = None
        else:
            limit = int(limit)
    else:
        function_class=None
        limit=20

    samples, table = Annotation.rpkm_table(limit=limit, function_class=function_class)

    return render_template('index.html',
            table=table,
            samples=samples,
            form=form
        )

if __name__ == '__main__':
    app.run()
