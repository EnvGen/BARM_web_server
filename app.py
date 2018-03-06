from flask import Flask, render_template, request, make_response, jsonify, redirect, url_for, flash
from flask.ext.sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.backend.sqla import SQLAlchemyBackend
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_login import current_user, LoginManager, login_user, logout_user, login_required
from forms import FunctionClassFilterForm, TaxonomyTableFilterForm, BlastFilterForm
import sqlalchemy
import config
import json
import os
from collections import OrderedDict
from urllib.parse import urlparse, urljoin
import subprocess
import shutil
import pandas as pd
import io

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

config.check_oauth_variables(os.environ['APP_SETTINGS'])

db = SQLAlchemy(app)

from models import Sample, SampleSet, TimePlace, SampleProperty, Annotation, Taxon, OAuth, User, Gene


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

if os.environ.get('AA_SEQUENCES'):
    AA_SEQUENCES = os.environ['AA_SEQUENCES']
    assert(os.path.isfile(AA_SEQUENCES))
else:
    raise Exception('The variable AA_SEQUENCES is not set')

if os.environ.get('NUC_SEQUENCES'):
    NUC_SEQUENCES = os.environ['NUC_SEQUENCES']
    assert(os.path.isfile(NUC_SEQUENCES))
else:
    raise Exception('The variable NUC_SEQUENCES is not set')

assert(shutil.which('cdbyank') is not None)

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
    if parent_value.endswith(';'):
        return ""
    child_level, child_values = Taxon.tree_nodes(parent_level, parent_value)
    return render_template('taxon_tree_nodes_for_table.html',
                    node_level=child_level,
                    node_values=child_values)

@app.route('/ajax/taxon_tree_table_row/<string:level>/<string:complete_taxonomy>')
def taxon_tree_table_row(level, complete_taxonomy):
    complete_val_to_val = {}
    complete_val = complete_taxonomy.split(';')[-1]
    if complete_val == '':
        complete_val = '<unassigned {}>'.format(complete_taxonomy.split(';')[-2])
    complete_val_to_val[complete_taxonomy] = complete_val

    sample_sets = OrderedDict()
    for sample_set in sorted(SampleSet.all_public(), key=lambda ss: ss.name):
        sample_sets[sample_set] = sample_set.samples

    rpkm_row = Taxon.rpkm_table_row(level, complete_taxonomy)
    rpkm_row['complete_taxonomy_id'] = complete_taxonomy.replace(';','-').replace(' ', '_').replace('.','_')

    json_table = {}
    json_table[complete_taxonomy] = {}
    for sample_set, samples in sample_sets.items():
        json_table_row = []
        for sample in samples:
            json_table_row.append({'y': rpkm_row[sample], 'sample': sample.scilifelab_code})
        json_table[complete_taxonomy][sample_set.name] = json_table_row

    return render_template('taxon_tree_table_row.html',
            complete_taxon = complete_taxonomy,
            complete_val_to_val = complete_val_to_val,
            sample_sets= sample_sets,
            table_row=rpkm_row,
            json_table=json_table)

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

    complete_val_to_val = {}
    sample_sets = OrderedDict()
    sample_scilifelab_codes = [] # Used for highcharts labels
    for sample_set in sorted(SampleSet.all_public(), key=lambda ss: ss.name):
        sample_sets[sample_set] = sample_set.samples
        sample_scilifelab_codes += [sample.scilifelab_code for sample in sample_set.samples]

    table = OrderedDict()
    json_table = {}
    for taxa_name, complete_taxonomy in node_values:
        json_table[complete_taxonomy] = {}
        complete_val_to_val[complete_taxonomy] = taxa_name

        table_row = Taxon.rpkm_table_row(complete_taxonomy=complete_taxonomy)
        for sample_set, samples in sample_sets.items():
            json_table_row = []
            for sample in samples:
                json_table_row.append({'y': table_row[sample], 'sample': sample.scilifelab_code})
            json_table[complete_taxonomy][sample_set.name] = json_table_row

        table_row['complete_taxonomy_id'] = complete_taxonomy.replace(';','-').replace(' ', '_').replace('.','_')
        table[complete_taxonomy] = table_row


    return render_template('taxon_tree_table.html',
            node_level = node_level,
            node_values = node_values,
            table=table,
            sample_sets=sample_sets,
            sample_scilifelab_codes=sample_scilifelab_codes,
            complete_val_to_val=complete_val_to_val,
            json_table=json_table)

def table_to_csv(table, samples, blast=True):
    first_row = ','.join(['gene_id', 'functions', 'taxonomy'])

    if blast:
        first_row += ',' + ','.join(['e_value', 'identity', 'alignment_length'])

    first_row += ',' + ','.join(sample.scilifelab_code for sample in samples)
    csv_output = [first_row]
    for gene, sample_d in table.items():
        row = [gene.name]
        annotations_combined = []
        for annotation_type, annotation_l in sample_d['annotations'].items():
            for annotation in annotation_l:
                annotations_combined.append(annotation.type_identifier)
        row.append('|'.join(annotations_combined))

        try:
            row.append(sample_d['taxonomy'])
        except KeyError:
            row.append('')
        if blast:
            row.append("{0:.2f}".format(sample_d['e_value']))
            row.append("{0:.2f}".format(sample_d['identity']))
            row.append("{}".format(sample_d['alignment_length']))
        for sample in samples:
            row.append(sample_d[sample])
        csv_output.append(','.join(row))

    csv_str = '\n'.join(csv_output)

    return csv_str

@app.route('/blast_search_table', methods=['GET', 'POST'])
def blast_page():
    form = BlastFilterForm()
    form.select_sample_groups.choices = [(sample_set.name, sample_set.name) for sample_set in  SampleSet.all_public()]
    if form.validate_on_submit():
        cmd = [form.blast_algorithm.data]

        e_val = int(form.e_value_factor.data) * 10**int(form.e_value_exponent.data)
        cmd += ["-evalue", str(e_val)]

        if form.blast_algorithm.data == 'blastp':
            blast_db = AA_SEQUENCES
        else:
            blast_db = NUC_SEQUENCES
        cmd += ['-db', blast_db]
        names = ['qacc', 'sacc', 'pident', 'length', 'qstart', 'qend', 'sstart', 'send', 'evalue', 'bitscore']
        cmd += ['-outfmt', '6 {}'.format(" ".join(names))]


        with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,\
                stderr=subprocess.PIPE) as process:
            blast_stdout, stderr = process.communicate(input=form.sequence.data.encode())
            returncode = process.returncode

        if returncode == 0:
            with io.StringIO(blast_stdout.decode()) as stdout_buf:
                df = pd.read_csv(stdout_buf, sep='\t', index_col=1, header=None, names=names)
            total_hits = len(df)
            # Filter on identity and alignment length
            df = df[df['pident'] >= form.min_identity.data]

            hits_after_pident = len(df)
            df = df[df['length'] >= form.min_aln_length.data]

            hits_after_length = len(df)

            # Fetch counts for the matching genes
            if len(df) == 0:
                msg = "No hits were found in the BLAST search"
                flash(msg, category="error")
                return render_template('blast_page.html',
                        form=form,
                        table = {})


            # If gene counts are requested
            if not form.submit_download.data or form.download_select.data == 'Gene Counts':
                samples, table = Gene.rpkm_table(list(df.index))

                sample_set_names = form.select_sample_groups.data
                if len(sample_set_names) > 0:
                    sample_sets = SampleSet.query.filter(SampleSet.name.in_(sample_set_names))
                    samples = Sample.all_from_sample_sets(sample_set_names)
                else:
                    sample_sets = SampleSet.all_public()
                    sample_set_names = [s.name for s in sample_sets]
                    samples = Sample.all_from_sample_sets(sample_set_names)

                def _prepare_json_table(table, sample_sets):
                    json_table = {}
                    for gene, sample_d in table.items():
                        json_table[gene.name] = {}
                        for sample_set in sample_sets:
                            json_table_row = []
                            for sample in sample_set.samples:
                                json_table_row.append({'y': float(sample_d[sample]), 'sample': sample.scilifelab_code})
                            json_table[gene.name][sample_set.name] = json_table_row

                    return json_table

                json_table = _prepare_json_table(table, sample_sets)

                # Update table with blast info
                for gene, sample_d in table.items():
                    table[gene]['e_value'] = df.loc[gene.name]['evalue']
                    table[gene]['identity'] = df.loc[gene.name]['pident']
                    table[gene]['alignment_length'] = df.loc[gene.name]['length']

                if form.submit_download.data:
                    r = make_response(table_to_csv(table, samples))
                    r.headers["Content-Disposition"] = "attachment; filename=gene_counts.csv"
                    r.headers["Content-Type"] = "text/plain"
                    return r
                else:
                    return render_template('blast_page.html',
                        form=form,
                        samples=samples,
                        table=table,
                        sample_scilifelab_codes = [s.scilifelab_code for s in samples],
                        sample_sets=sample_set_names,
                        json_table=json_table)

            # No gene counts are needed
            elif form.download_select.data in ['Amino Acid Sequences', 'Nucleotide Sequences']:
                # Fetch gene ids
                all_ids = list(df.index)

                if form.download_select.data == 'Amino Acid Sequences':
                    seqs, msg = _extract_sequences(all_ids, AA_SEQUENCES)
                else:
                    seqs, msg = _extract_sequences(all_ids, NUC_SEQUENCES)

                if seqs is None:
                    json_table = _prepare_json_table(table, sample_sets)
                    flash(msg, category="error")
                    return render_template('blast_page.html',
                        form=form,
                        samples=[],
                        table={},
                        sample_scilifelab_codes=[])
                else:
                    r = make_response(seqs)
                    r.headers["Content-Disposition"] = "attachment; filename=blast_hits.fa"
                    r.headers["Content-Type"] = "text/plain"
                    return r

            elif form.download_select.data == 'BLAST tabular':
                r = make_response(df.to_csv(sep='\t'))
                if form.blast_algorithm.data == 'blastp':
                    r.headers["content-disposition"] = "attachment; filename=blastp_hits.tsv"
                else:
                    r.headers["content-disposition"] = "attachment; filename=blastn_hits.tsv"
                r.headers["Content-Type"] = "text/plain"
                return r

        msg = "Error, the {} query was not successful.".format(form.blast_algorithm.data)
        flash(msg, category="error")

        # Logging the error
        print("BLAST ERROR, cmd: {}".format(cmd))
        print("BLAST ERROR, returncode: {}".format(returncode))
        print("BLAST ERROR, output: {}".format(blast_stdout))
        print("BLAST ERROR, stderr: {}".format(stderr))

    # else: commented out since also returncode != 0 leads here
    return render_template('blast_page.html',
        form=form,
        samples=[],
        table={},
        sample_scilifelab_codes=[])



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
    DEFAULT_QUERY = 'Photosynth'
    form = FunctionClassFilterForm()
    form.function_class.choices = [('ecnumber', 'EcNumber'),
                    ('pfam', 'Pfam'),
                    ('tigrfam', 'TigrFam'),
                    ('eggnog', 'EggNOG'),
                    ('all', 'All')
                ]

    form.select_sample_groups.choices = [(sample_set.name, sample_set.name) for sample_set in  SampleSet.all_public()]

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

        sample_set_names = form.select_sample_groups.data
        if len(sample_set_names) > 0:
            sample_sets = SampleSet.query.filter(SampleSet.name.in_(sample_set_names))
            samples = [sample.scilifelab_code for sample in Sample.all_from_sample_sets(sample_set_names)]
        else:
            sample_sets = SampleSet.all_public()
            samples = None

        download_action = False
        if form.submit_download.data:
            download_action = True
            download_select = form.download_select.data

        if len(type_identifiers) == 0:
            msg = "Warning, the query was not performed since it did not result in any hit. Try writing a more general query."
            flash(msg, category="error")
        elif len(type_identifiers) > 200:
            msg = "Warning, the query was not performed since it resulted in more than 200 hits. Try writing a more specific query."
            flash(msg, category="error")
            type_identifiers = []
        elif len(type_identifiers) > 20 and download_action and download_select == 'Gene Counts':
            msg = "Warning, the Gene Counts download was not performed since it resulted in more than 20 annotations. Try writing a more specific query."
            flash(msg, category="error")
            type_identifiers = []

    else:
        function_class=None
        limit=20
        samples = None
        download_action = False
        sample_sets = SampleSet.all_public()
        sample_set_names = [ss.name for ss in sample_sets]
        samples = [sample.scilifelab_code for sample in Sample.all_from_sample_sets(sample_set_names)]

        # A default set of type identifiers to avoid query the entire
        # table
        q = _search_query(DEFAULT_QUERY, 'all')
        type_identifiers = [a.type_identifier for a in q.all()]

    if len(form.type_identifiers) == 0:
        form.type_identifiers.append_entry()

    if type_identifiers == []:
        samples = []
        table = dict()
    else:
        samples, table = Annotation.rpkm_table(limit=limit, samples=samples, function_class=function_class, type_identifiers=type_identifiers)
    samples = sorted(samples, key=lambda x: x.scilifelab_code)
    sample_scilifelab_codes = [sample.scilifelab_code for sample in samples]

    def _prepare_json_table(table, sample_sets):
        json_table = {}
        for annotation, sample_d in table.items():
            json_table[annotation.type_identifier] = {}
            for sample_set in sample_sets:
                json_table_row = []
                json_table_row = []
                for sample in sample_set.samples:
                    json_table_row.append({'y': float(sample_d[sample]), 'sample': sample.scilifelab_code})
                json_table[annotation.type_identifier][sample_set.name] = json_table_row
        return json_table

    # This section is not independent from the section above
    if len(type_identifiers) > 0 and download_action:
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

        elif download_select == 'Gene Counts':
            annotation_ids = [annotation.id for annotation, sample in table.items()]
            genes_per_annotation = Annotation.genes_per_annotation(annotation_ids)

            all_gene_names = []
            for gene, annotation in genes_per_annotation:
                all_gene_names.append(gene.name)
                #[gene.name for gene in genes]

            samples, table = Gene.rpkm_table(all_gene_names)
            csv_output = table_to_csv(table, samples, blast=False)

            r = make_response(csv_output)
            r.headers["Content-Disposition"] = "attachment; filename=gene_counts.csv"
            r.headers["Content-Type"] = "text/csv"
            return r

        elif download_select == 'Annotation Counts':
            csv_output = 'annotation_id' + ',' + \
            ','.join([sample.scilifelab_code for sample in samples]) \
            + '\n'
            csv_output += '\n'.join(
                    [annotation.type_identifier + ',' + ','.join([sample_d[sample] for sample in samples]) for annotation, sample_d in table.items()])
            r = make_response(csv_output)
            r.headers["Content-Disposition"] = "attachment; filename=annotation_counts.csv"
            r.headers["Content-Type"] = "text/csv"
            return r

        elif download_select == 'Amino Acid Sequences':
            annotations = [annotation for annotation, sample in table.items()]
            all_gene_ids = set()
            for annotation in annotations:
                gene_ids = set([gene.name for gene in annotation.genes])
                all_gene_ids |= gene_ids

            seqs, msg = _extract_sequences(all_gene_ids, AA_SEQUENCES)
            if seqs is None:
                json_table = _prepare_json_table(table, sample_sets)
                flash(msg, category="error")
            else:
                r = make_response(seqs)
                r.headers["Content-Disposition"] = "attachment; filename=proteins_aa.fa"
                r.headers["Content-Type"] = "text/plain"
                return r

        elif download_select == 'Nucleotide Sequences':
            annotations = [annotation for annotation, sample in table.items()]
            all_gene_ids = set()
            for annotation in annotations:
                gene_ids = set([gene.name for gene in annotation.genes])
                all_gene_ids |= gene_ids

            seqs, msg = _extract_sequences(all_gene_ids, NUC_SEQUENCES)
            if seqs is None:
                json_table = _prepare_json_table(table, sample_sets)
                flash(msg, category="error")
            else:
                r = make_response(seqs)
                r.headers["Content-Disposition"] = "attachment; filename=proteins_nuc.fa"
                r.headers["Content-Type"] = "text/plain"
                return r
    else:
        # Wait to prepare the json table until it's certain that it's necessary
        json_table = _prepare_json_table(table, sample_sets)

    return render_template('functional_table.html',
            table=table,
            samples=samples,
            sample_sets=sample_sets,
            sample_scilifelab_codes = sample_scilifelab_codes,
            form=form,
            json_table=json_table
        )

def _extract_sequences(all_ids, sequence_file):
    """ Will run cdbyank on the sequence file to extract 
    all sequences in all_ids as fasta"""

    index_file = sequence_file + '.cidx'

    with subprocess.Popen(['cdbyank', index_file], stdout=subprocess.PIPE, 
            stdin=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        cdbyank_stdout, stderr = process.communicate(input='\n'.join(all_ids).encode())
    seqs = cdbyank_stdout.decode()
    if len(seqs) == 0 or seqs[0] != '>':
        msg = "Error! The sequence extraction was not possible. We're sorry for the inconvenience."
        print("ERROR IN SEQUENCE EXTRACTION")
        print(stderr.decode())
        return None, msg
    else:
        return seqs, None

def _search_query(search_string, function_class):
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
    if function_class != 'all':
        q = q.filter(Annotation.annotation_type == function_class)

    return q

@app.route('/ajax/search_annotations', methods=['GET'])
def suggestions():
    text_input = request.args.get('text_input', '')
    function_class = request.args.get('function_class', '')
    annotations = []
    nr_annotations_total = 0
    if text_input != '':
        q = _search_query(text_input, function_class)
        nr_annotations_total = q.count()
        annotations = q.limit(10).all()
    return render_template('search_annotations.html', annotations=annotations, nr_annotations_total=nr_annotations_total, nr_annotations_shown = len(annotations))

if __name__ == '__main__':
    app.run()
