from flask import Flask, render_template, request, make_response, jsonify, redirect, url_for, flash
from flask.ext.sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.backend.sqla import SQLAlchemyBackend
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_login import current_user, LoginManager, login_user, logout_user, login_required
from forms import FunctionClassFilterForm, TaxonomyTableFilterForm
import sqlalchemy
import config
import json
import os
from collections import OrderedDict
from urllib.parse import urlparse, urljoin

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

config.check_oauth_variables(os.environ['APP_SETTINGS'])

db = SQLAlchemy(app)

from models import Sample, SampleSet, TimePlace, SampleProperty, Annotation, Taxon, OAuth, User


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

if os.environ.get('BARM_GOOGLE_CLIENT_ID'):
    google_client_id = os.environ['BARM_GOOGLE_CLIENT_ID']
else:
    raise Exception('The variable BARM_GOOGLE_CLIENT_ID is not set')

if os.environ.get('BARM_GOOGLE_CLIENT_SECRET'):
    google_client_secret = os.environ['BARM_GOOGLE_CLIENT_SECRET']
else:
    raise Exception('The variable BARM_GOOGLE_CLIENT_SECRET is not set')

blueprint = make_google_blueprint(
    client_id=google_client_id,
    client_secret=google_client_secret,
    scope=["profile", "email"],
    offline=True,
    reprompt_consent=True
)
app.register_blueprint(blueprint, url_prefix="/login")

blueprint.backend = SQLAlchemyBackend(OAuth, db.session, user=current_user)

login_manager = LoginManager()
login_manager.login_view = 'google.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    email = user_id
    return User.get_from_email(email)

@oauth_authorized.connect_via(blueprint)
def google_logged_in(blueprint, token):
    if not token:
        msg = "Failed to log in with {name}".format(name=blueprint.name)
        flash(msg, category="error")
        return

    # figure out who the user is
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        email = resp.json()["email"]
        name = resp.json()["name"]
        user = User.get_from_email(email)
        if not user:
            msg = "No user registered for email: {email}".format(email=email)
            flash(msg, category="error")
        else:
            user.name = name
            login_user(user)
            msg = "Successfully signed in with Google"
            flash(msg, category="success")
            return
    else:
        msg = "Failed to fetch user info from {name}".format(name=blueprint.name)
        flash(msg, category="error")
        return

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out")
    return redirect(url_for("index"))

@app.route('/highcharts')
def highcharts():
    return render_template('highcharts.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ajax/taxon_tree_nodes/<string:parent_level>/<string:parent_value>')
def taxon_tree_nodes(parent_level, parent_value):
    child_level, child_values = Taxon.tree_nodes(parent_level, parent_value)
    return render_template('taxon_tree_nodes.html',
                    node_level=child_level,
                    node_values=child_values)


@app.route('/ajax/taxon_tree_nodes_for_table/<string:parent_level>/<string:parent_value>')
def taxon_tree_nodes_for_table(parent_level, parent_value):
    child_level, child_values = Taxon.tree_nodes(parent_level, parent_value)
    return render_template('taxon_tree_nodes_for_table.html',
                    node_level=child_level,
                    node_values=child_values)

@app.route('/ajax/taxon_tree_table_row/<string:level>/<string:complete_taxonomy>')
def taxon_tree_table_row(level, complete_taxonomy):
    samples, rpkm_row, complete_val_to_val = Taxon.rpkm_table_row(level, complete_taxonomy)
    rpkm_row['complete_taxonomy_id'] = complete_taxonomy.replace(';','-')
    return render_template('taxon_tree_table_row.html',
            complete_taxon = complete_taxonomy,
            complete_val_to_val = complete_val_to_val,
            samples = samples,
            table_row=rpkm_row)

@app.route('/taxonomy_tree', methods=['GET'])
def taxonomy_tree():
    node_level = "superkingdom"
    node_values= Taxon.top_entry_taxa()
    return render_template('taxon_tree.html',
            node_level = node_level,
            node_values = node_values
        )


@app.route('/taxonomy_tree_table', methods=['GET'])
def taxonomy_tree_table():
    node_level = "superkingdom"
    node_values = Taxon.top_entry_taxa()

    taxon_level = 'superkingdom'
    parent_values = None
    limit = 20

    sample_scilifelab_codes = [s.scilifelab_code for s in Sample.query.all()]
    samples, table, complete_val_to_val = Taxon.rpkm_table(level=node_level, top_level_complete_values=parent_values, limit=limit)
    for complete_taxon, table_row in table.items():
        table_row['complete_taxonomy_id'] = complete_taxon.replace(';','-')

    return render_template('taxon_tree_table.html',
            node_level = node_level,
            node_values = node_values,
            table=table,
            samples=samples,
            sample_scilifelab_codes = sample_scilifelab_codes,
            complete_val_to_val=complete_val_to_val,
        )

@app.route('/taxonomy_table', methods=['GET'])
def taxon_table():
    taxonomy_levels = Taxon.level_order

    taxon_level = request.args.get('taxon_level', 'superkingdom')
    parent_values = request.args.getlist('parent_values[]', None)
    parent_level = request.args.get('parent_level', None)
    row_limit = request.args.get('row_limit', 20)

    if taxon_level not in taxonomy_levels:
        taxon_level = 'superkingdom'
    if parent_level not in taxonomy_levels:
        parent_values = None
    if row_limit not in ['20', '50', '100', 'all']:
        row_limit = 20

    # Translate to model language
    if row_limit == 'all':
        limit = None
    else:
        limit = row_limit
    sample_scilifelab_codes = [s.scilifelab_code for s in Sample.query.all()]
    samples, table, complete_val_to_val = Taxon.rpkm_table(level=taxon_level, top_level_complete_values=parent_values, top_level=parent_level, limit=limit)
    sorted_table = OrderedDict()
    for complete_taxon, sample_d in table.items():
        new_sample_data = []
        for sample in samples:
            new_sample_data.append(sample_d[sample])
        sorted_table[complete_taxon] = new_sample_data

    return render_template('taxon_table.html',
            table=table,
            samples=samples,
            sorted_table=sorted_table,
            sample_scilifelab_codes = sample_scilifelab_codes,
            complete_val_to_val=complete_val_to_val,
            taxonomy_levels=taxonomy_levels,
            current_level=taxon_level,
            row_limit=row_limit
        )

@app.route('/functional_table', methods=['GET', 'POST'])
def functional_table():
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
    sample_scilifelab_codes = [sample.scilifelab_code for sample in samples]
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
        elif download_select == 'Annotation Counts':
            csv_output = 'annotation_id' + ',' + \
            ','.join([sample.scilifelab_code for sample in samples]) \
            + '\n'
            csv_output += '\n'.join(
                    [annotation.type_identifier + ',' + ','.join(["{:0.2f}".format(sample_d[sample]) for sample in samples]) for annotation, sample_d in table.items()])
            r = make_response(csv_output)
            r.headers["Content-Disposition"] = "attachment; filename=annotation_counts.csv"
            r.headers["Content-Type"] = "text/csv"
            return r
    return render_template('functional_table.html',
            table=table,
            samples=samples,
            sample_scilifelab_codes = sample_scilifelab_codes,
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
