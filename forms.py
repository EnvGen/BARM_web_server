from flask.ext.wtf import Form
from wtforms import SelectField, SelectMultipleField, StringField, FieldList, RadioField, SubmitField, IntegerField, TextAreaField, ValidationError

DEFAULT_BLAST_GENE=""">IMG reference gene:2504129627
MTNITPQSIKEELHKALGQLDSFESCALLNYPDYLNFGDHLIWLGTVIYLTDVLKTKIKYASSIADFSPTIMEDKIGKAPIFLQGGGNLGDLWRVDQQFREQIIAKYQDRPIIILPQSIFFAKLDNLQKTANIFNSHPNLTIFVRDDRSYKIAEESFNKCRVIKSPDMAFQLLNLPGISTNHNSKSSILYHCRKDKELNPEFSIDTVKIPNLVVQDWVSFEWVLGVRHRGIKRFATQAVREVWQRGLMTPVEWIYRQKWQYFYSNTDKFNQMYNPFMHKLLWSFLHSGIYQLQQHQLVITNRLHGHILCILLGIPHVFLPNAYYKNESFYETWTKNVSFCRFVKDINQIESVVKELLEISKSGKINV"""

def fasta_length_check(form, field):
    if len(field.data) < 1:
        raise ValidationError('Please submit an input sequence')
    if len(field.data) > 15000:
        raise ValidationError('Input sequence must be less than 15000 characters')
    if field.data[0] != '>':
        raise ValidationError('Input sequence must be in fasta format')
    # Count number of fasta headers:
    all_headers = [line for line in field.data.split('\n') if (not len(line)==0) and (line[0] == '>')]
    if len(all_headers) != 1:
        raise ValidationError('Only one input sequence at a time is allowed')

def e_val_exponent_check(form, field):
    # Check max value, min value
    # Ignore case when data is not integer which is handled by wtforms
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < -256:
            raise ValidationError('Exponent is required to be larger than -256')
        if data_i > 256:
            raise ValidationError('Exponent is required to be smaller than 256')

def e_val_factor_check(form, field):
    # Check max value, min value
    # Ignore case when data is not integer which is handled by wtforms
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0:
            raise ValidationError('Factor is required to be non-negative')
        if data_i > 9:
            raise ValidationError('Exponent is required to be smaller than 10')

def identity_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0:
            raise ValidationError('Minimum identity is required to be non-negative')
        if data_i > 100:
            raise ValidationError('Minimum identity is required to be smaller than 101')


def aln_length_check(form, field):
    # Check max value, min value
    if field.data is not None:
        try:
            data_i = int(field.data)
        except:
            return None
        if data_i < 0:
            raise ValidationError('Minimum alignment length is required to be non-negative')
        if data_i > 100000:
            raise ValidationError('Minimum alignment length is required to be smaller than 100000')

class BlastFilterForm(Form):
    sequence = TextAreaField('Sequence', [fasta_length_check], default=DEFAULT_BLAST_GENE)
    blast_algorithm = RadioField(u'Algorithm', choices=[('blastp','blastp'), ('blastn','blastn')], default='blastp')
    e_value_exponent = IntegerField(u'e_value_exponent', [e_val_exponent_check], default=-5)
    e_value_factor = IntegerField(u'e_value_factor', [e_val_factor_check], default=1)
    min_identity = IntegerField(u'min_identity', [identity_check], default=0)
    min_aln_length = IntegerField(u'min_aln_length', [aln_length_check], default=0)
    select_sample_groups = SelectMultipleField(u'Sample Groups')
    submit_view = SubmitField(u'View Results')
    submit_download = SubmitField(u'Download')
    download_select = SelectField(u'What to download', choices=[('Gene Counts', 'Gene Counts with BLAST statistics'), ('BLAST tabular', 'BLAST result details (no gene counts)'), ('Amino Acid Sequences', 'Matching sequences (Amino Acids)'), ('Nucleotide Sequences', 'Matching sequences (Nucleotides)')], default='Gene Counts')

class FunctionClassFilterForm(Form):
    function_class = SelectField(u'Function Classes', default='all')
    limit = SelectField(u'Limit', choices=[('10','10'), ('20', '20'), ('50', '50'), ('100', '100'), ('all', 'Show All')], default='20')
    filter_alternative = RadioField(choices=[
      ('filter_with_search', 'Filter by a search term'),
      ('filter_with_type_identifiers', 'Filter by typing in individual annotation identifiers')],
      default='filter_with_search')
    type_identifiers = FieldList(StringField(u'Type identifier'))
    search_annotations = StringField('Search Annotations', default='Photosynth')
    select_sample_groups = SelectMultipleField(u'Sample Groups')
    submit_view = SubmitField(u'View Results')
    submit_download = SubmitField(u'Download')
    download_select = SelectField(u'What to download', choices=[('Gene Counts', 'Gene Counts'), ('Gene List', 'Gene List'), ('Annotation Counts', 'Annotation Counts'), ('Amino Acid Sequences', 'Amino Acid Sequences'), ('Nucleotide Sequences', 'Nucleotide Sequences')], default='Gene List')

class TaxonomyTableFilterForm(Form):
    taxonomy_levels = [("superkingdom", "superkingdom"), ("phylum", "phylum"), ("taxclass", "taxclass"), ("order", "order"), ("family", "family"), ("genus", "genus"), ("species", "species")]

    view_level = SelectField(u'Taxon Levels',
        choices=taxonomy_levels, default='superkingdom')
    submit_update = SubmitField(u'Update')


