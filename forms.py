from flask.ext.wtf import Form
from wtforms import SelectField, StringField, FieldList, RadioField


class FunctionClassFilterForm(Form):
    function_class = SelectField(u'Function Classes', default='all')
    limit = SelectField(u'Limit', choices=[('10','10'), ('20', '20'), ('50', '50'), ('100', '100'), ('all', 'Show All')], default='20')
    filter_alternative = RadioField(choices=[
      ('filter_with_type_identifiers', 'Filter by typing in individual annotation identifiers'),
      ('filter_with_search', 'Filter by a search term')],
      default='filter_with_type_identifiers')
    type_identifiers = FieldList(StringField(u'Type identifier'))
    search_annotations = StringField('Search Annotations')
