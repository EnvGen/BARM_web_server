from flask.ext.wtf import Form
from wtforms import SelectField, TextField, FieldList


class FunctionClassFilterForm(Form):
    function_class = SelectField(u'Function Classes', default='all')
    limit = SelectField(u'Limit', choices=[('10','10'), ('20', '20'), ('50', '50'), ('100', '100'), ('all', 'Show All')], default='20')
    type_identifiers = FieldList(TextField(u'Type identifier'))
