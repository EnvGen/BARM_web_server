from flask import Flask, render_template, request, make_response, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from forms import FunctionClassFilterForm, TaxonomyTableFilterForm
import sqlalchemy

import os

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)

from models import Sample, SampleSet, TimePlace, SampleProperty, Annotation, Taxon

@app.route('/ajax/taxon_tree_nodes/<string:parent_level>/<string:parent_value>')
def taxon_tree_nodes(parent_level, parent_value):
    child_level, child_values = Taxon.tree_nodes(parent_level, parent_value)
    return render_template('taxon_tree_nodes.html',
                    node_level=child_level,
                    node_values=child_values)

@app.route('/taxonomy_tree', methods=['GET'])
def taxonomy_tree():
    node_level = "superkingdom"
    node_values= Taxon.top_entry_taxa()
    return render_template('taxon_tree.html',
            node_level = node_level,
            node_values = node_values
        )

@app.route('/taxonomy_table', methods=['GET'])
def taxon_table():
    taxonomy_levels = Taxon.level_order

    taxon_level = request.args.get('taxon_level', 'superkingdom')
    parent_values = request.args.getlist('parent_values[]', None)
    parent_level = request.args.get('parent_level', None)

    if taxon_level not in taxonomy_levels:
        taxon_level = 'superkingdom'
    if parent_level not in taxonomy_levels:
        parent_values = None
    samples, table, complete_val_to_val = Taxon.rpkm_table(level=taxon_level, top_level_complete_values=parent_values, top_level=parent_level)

    return render_template('taxon_table.html',
            table=table,
            samples=samples,
            complete_val_to_val=complete_val_to_val,
            taxonomy_levels=taxonomy_levels,
            current_level=taxon_level
        )

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

        download_action = False
        if form.submit_download.data:
            download_action = True
            download_select = form.download_select.data
    else:
        function_class=None
        limit=20
        samples = None
        download_action = False

    if len(form.type_identifiers) == 0:
        form.type_identifiers.append_entry()

    if type_identifiers == []:
        type_identifiers = None

    samples, table = Annotation.rpkm_table(limit=limit, samples=samples, function_class=function_class, type_identifiers=type_identifiers)
    samples = sorted(samples, key=lambda x: x.scilifelab_code)
    if download_action:
        if download_select == 'Gene List':
            # Fetch all contributing genes for all the annotations in the table
            annotation_ids = [annotation.id for annotation, sample in table.items()]
            genes_per_annotation = Annotation.genes_per_annotation(annotation_ids)
            csv_output = '\n'.join(
                    [','.join([gene.name, annotation.type_identifier]) \
                            for gene, annotation in genes_per_annotation])
            r = make_response(csv_output)
            r.headers["Content-Disposition"] = "attachment; filename=gene_list.csv"
            r.headers["Content-Type"] = "text/csv"
            return r
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
