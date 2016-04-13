from flask import Flask, render_template, request
from flask.ext.sqlalchemy import SQLAlchemy
from forms import FunctionClassFilterForm
import sqlalchemy

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

    form.select_sample_groups.choices = [(sample_set.name, sample_set.name) for sample_set in  SampleSet.query.all()]

    type_identifiers = []
    if form.validate_on_submit():
        function_class = form.function_class.data
        if function_class == 'all':
            function_class = None
        limit = form.limit.data
        if limit == 'all':
            limit = None
        else:
            limit = int(limit)

        filter_alternative = form.filter_alternative.data
        if filter_alternative == 'filter_with_type_identifiers':
            for type_identifier in form.type_identifiers.entries:
                if type_identifier.data != '':
                    type_identifiers.append(type_identifier.data)
        elif filter_alternative == 'filter_with_search':
            search_string = form.search_annotations
            if search_string.data != '':
                q = _search_query(search_string.data)
                type_identifiers = [a.type_identifier for a in q.all()]


        sample_sets = form.select_sample_groups.data
        if len(sample_sets) > 0:
            samples = [sample.scilifelab_code for sample in Sample.all_from_sample_sets(sample_sets)]
        else:
            samples = None
    else:
        function_class=None
        limit=20
        samples = None

    if len(form.type_identifiers) == 0:
        form.type_identifiers.append_entry()

    if type_identifiers == []:
        type_identifiers = None
    samples, table = Annotation.rpkm_table(limit=limit, samples=samples, function_class=function_class, type_identifiers=type_identifiers)
    return render_template('index.html',
            table=table,
            samples=samples,
            form=form
        )

def _search_query(search_string):
    """ adding % signs before and after will create a substring search

    It will be case insensitive but will only match exactly whats in search_string
    """
    search_string = '%'+search_string+'%'
    q = Annotation.query.filter(
            sqlalchemy.or_(
                Annotation.type_identifier.ilike(search_string),
                Annotation.description.ilike(search_string)
            )
        )
    return q

@app.route('/ajax/search_annotations', methods=['GET'])
def suggestions():
    text_input = request.args.get('text_input', '')
    annotations = []
    nr_annotations_total = 0
    if text_input != '':
        q = _search_query(text_input)
        nr_annotations_total = q.count()
        annotations = q.limit(10).all()
    return render_template('search_annotations.html', annotations=annotations, nr_annotations_total=nr_annotations_total, nr_annotations_shown = len(annotations))

if __name__ == '__main__':
    app.run()
