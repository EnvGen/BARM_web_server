from app import db
import sqlalchemy
import collections
##########
# Sample #
##########

class SampleSet(db.Model):
    __tablename__ = 'sample_set'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())


    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<SampleSet {}>'.format(self.id)


class TimePlace(db.Model):
    __tablename__ = 'time_place'

    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime())
    latitude = db.String()
    longitude = db.String()

    def __init__(self, time, latitude, longitude):
        self.time = time
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return '<TimePlace {}>'.format(self.id)


class Sample(db.Model):
    __tablename__ = 'sample'

    id = db.Column(db.Integer, primary_key=True)
    scilifelab_code = db.Column(db.String(11))
    sample_set_id = db.Column(db.Integer, db.ForeignKey('sample_set.id'))
    sample_set = db.relationship('SampleSet',
            backref=db.backref('samples'))

    timeplace_id = db.Column(db.Integer, db.ForeignKey('time_place.id'))
    timeplace = db.relationship('TimePlace',
            backref=db.backref('samples'))

    def __init__(self, scilifelab_code, sample_set, timeplace):
        self.scilifelab_code = scilifelab_code
        self.sample_set = sample_set
        self.timeplace = timeplace

    def __repr__(self):
        return '<Sample {}>'.format(self.id)


class SampleProperty(db.Model):
    __tablename__ = 'sample_property'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), index=True)
    value = db.Column(db.String(), index=True)
    unit = db.Column(db.String())

    # Sample Property has one sample
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'))
    sample = db.relationship("Sample",
            backref=db.backref("properties"))

    def __init__(self, name, value, unit, sample):
        self.name = name
        self.value = value
        self.unit = unit
        self.sample = sample

    def __repr__(self):
        return '<SampleProperty {}>'.format(self.id)

class ReferenceAssembly(db.Model):
    __tablename__ = 'reference_assembly'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String())

    def __init__(self, name):
        self.name = name

class GeneAnnotation(db.Model):
    __tablename__ = 'gene_annotation'
    id = db.Column(db.Integer, primary_key=True)

    annotation_id = db.Column('annotation_id', db.Integer, db.ForeignKey('annotation.id'))
    gene_id = db.Column('gene_id', db.Integer, db.ForeignKey('gene.id'))
    e_value = db.Column('e_value', db.Float, nullable=True)

    annotation_source_id = db.Column(db.Integer, db.ForeignKey('annotation_source.id'),
            nullable=False)

    annotation_source = db.relationship('AnnotationSource',
            backref=db.backref('annotations'))
    gene = db.relationship("Gene")
    annotation = db.relationship("Annotation")

    def __init__(self, annotation=None, gene=None, annotation_source=None, e_value=None):
        self.annotation = annotation
        self.gene = gene
        self.annotation_source = annotation_source
        self.e_value = e_value

class Gene(db.Model):
    __tablename__ = 'gene'
    __table_args__ = (
        db.UniqueConstraint('name', 'reference_assembly_id', name='gene_within_assembly_unique'),
        )
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String())
    reference_assembly_id = db.Column(db.Integer,
            db.ForeignKey('reference_assembly.id'))
    reference_assembly = db.relationship("ReferenceAssembly",
            backref=db.backref("genes"))
    gene_annotations = db.relationship("GeneAnnotation")


    def __init__(self, name, reference_assembly):
        self.name = name
        self.reference_assembly = reference_assembly

    @property
    def annotations(self):
        q = db.session.query(Annotation).join(GeneAnnotation).\
                filter(Annotation.id == GeneAnnotation.annotation_id).\
                filter(GeneAnnotation.gene_id == self.id)
        return list(q.all())

    @property
    def rpkm(self):
        return { sc.sample: sc.rpkm for sc in self.sample_counts }

    def e_value_for(self, annotation):
        return self.gene_annotation_for(annotation).e_value

    def gene_annotation_for(self, annotation):
        return db.session.query(GeneAnnotation).\
                filter_by(gene = self).\
                filter_by(annotation = annotation).first()

class GeneCount(db.Model):
    __tablename__ = 'gene_count'
    __table_args__ = (
        db.UniqueConstraint('sample_id', 'gene_id', name='genecount_unique'),
        )
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'),
            nullable=False)
    sample = db.relationship('Sample',
            backref=db.backref('gene_counts'))

    gene_id = db.Column(db.Integer, db.ForeignKey('gene.id'),
            nullable=False)
    gene = db.relationship('Gene',
            backref=db.backref('sample_counts'))

    rpkm = db.Column(db.Float)

    def __init__(self, gene, sample, rpkm):
        self.gene = gene
        self.sample = sample
        self.rpkm = rpkm

class AnnotationSource(db.Model):
    __tablename__ = 'annotation_source'
    id = db.Column(db.Integer, primary_key=True)

    dbname = db.Column(db.String)
    dbversion = db.Column(db.String)
    algorithm = db.Column(db.String)
    algorithm_parameters = db.Column(db.String)

    def __init__(self, dbname, dbversion, algorithm, algorithm_parameters):
        self.dbname = dbname
        self.dbversion = dbversion
        self.algorithm = algorithm
        self.algorithm_parameters = algorithm_parameters


class Annotation(db.Model):
    __tablename__ = 'annotation'
    __table_args__ = (
        db.UniqueConstraint('annotation_type', 'type_identifier', name='annotation_unique'),
        )
    id = db.Column(db.Integer, primary_key=True)

    annotation_type = db.Column(db.String)

    gene_annotations = db.relationship('GeneAnnotation')

    type_identifier = db.Column(db.String, nullable=False, unique=True)

    description = db.Column(db.String(4000))

    @classmethod
    def rpkm_table(self, samples=None, function_class=None, limit=20, type_identifiers=None):
        # Use only the annotations which has the highest total
        q_first = db.session.query(Annotation, sqlalchemy.func.sum(GeneCount.rpkm)).\
                outerjoin(GeneAnnotation).\
                filter(GeneAnnotation.annotation_id == Annotation.id).\
                outerjoin(Gene).\
                filter(Gene.id == GeneAnnotation.gene_id).\
                outerjoin(GeneCount).\
                filter(GeneCount.gene_id == Gene.id)

        if function_class is not None:
            q_first = q_first.filter(Annotation.annotation_type == function_class)

        if type_identifiers is not None:
            q_first = q_first.filter(Annotation.type_identifier.in_(type_identifiers))

        q_first = q_first.group_by(Annotation.id).\
                    order_by(sqlalchemy.func.sum(GeneCount.rpkm).desc())

        if limit is not None:
            q_first = q_first.limit(limit)

        annotation_ids = []
        annotations = []
        for annotation, rpkm_sum in q_first.all():
            annotations.append(annotation)
            annotation_ids.append(annotation.id)

        if not len(annotation_ids):
            return [], {}

        q = db.session.query(Sample, Annotation, sqlalchemy.func.sum(GeneCount.rpkm)).\
                join(GeneCount).\
                filter(Sample.id == GeneCount.sample_id).\
                join(Gene).\
                filter(GeneCount.gene_id == Gene.id).\
                join(GeneAnnotation).\
                filter(Gene.id == GeneAnnotation.gene_id).\
                join(Annotation).\
                filter(GeneAnnotation.annotation_id == Annotation.id).\
                filter(Annotation.id.in_(annotation_ids))

        if samples is not None:
            q = q.filter(Sample.scilifelab_code.in_(samples))

        q = q.group_by(Annotation.id, Sample.id).\
            order_by(Annotation.id, Sample.id)

        # format to have one row per list item
        rows_unordered = {}
        samples = set()
        for sample, annotation, rpkm_sum in q.all():
            samples.add(sample)
            if annotation in rows_unordered:
                rows_unordered[annotation][sample] = rpkm_sum
            else:
                rows_unordered[annotation] = collections.OrderedDict()
                rows_unordered[annotation][sample] = rpkm_sum

        rows = collections.OrderedDict()

        for annotation in annotations:
            rows[annotation] = rows_unordered[annotation]

        return list(samples), rows

    @property
    def genes(self):
        q = db.session.query(Gene).join(GeneAnnotation).\
                filter(Gene.id == GeneAnnotation.gene_id).\
                filter(GeneAnnotation.annotation_id == self.id)
        return list(q.all())

    @property
    def rpkm(self):
        q = db.session.query(Sample, sqlalchemy.func.sum(GeneCount.rpkm)).\
                join(GeneCount).\
                filter(Sample.id == GeneCount.sample_id).\
                join(Gene).\
                filter(GeneCount.gene_id == Gene.id).\
                join(GeneAnnotation).\
                filter(Gene.id == GeneAnnotation.gene_id).\
                join(Annotation).\
                filter(GeneAnnotation.annotation_id == Annotation.id).\
                filter(Annotation.id == self.id).\
                group_by(Sample.id)

        return { sample: rpkm_sum for sample, rpkm_sum in q.all() }

    __mapper_args__ = {
            'polymorphic_identity': 'annotation',
            'polymorphic_on': annotation_type
        }

    def __init__(self, type_identifier, description = None):
        self.type_identifier = type_identifier
        self.description = description

class Cog(Annotation):
    __tablename__ = 'cog'
    id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            primary_key=True)
    category = db.Column(db.String)

    def __init__(self, type_identifier, category, **kwargs):
        super().__init__(type_identifier, **kwargs)
        self.category = category

    __mapper_args__ = {
            'polymorphic_identity':'cog'
        }

class Pfam(Annotation):
    __tablename__ = 'pfam'
    id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'pfam'
        }

class TigrFam(Annotation):
    __tablename__ = 'tigrfam'
    id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'tigrfam'
        }

class EcNumber(Annotation):
    __tablename__ = 'ecnumber'
    id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            primary_key=True)

    first_digit = db.Column(db.Integer, index=True)
    second_digit = db.Column(db.Integer, index=True)
    third_digit = db.Column(db.Integer, index=True)
    fourth_digit = db.Column(db.Integer, index=True)

    def __init__(self, type_identifier, **kwargs):
        super().__init__(type_identifier, **kwargs)
        ec_digits = self.type_identifier.split('.')
        digit_translation_d = {
                0: self.first_digit,
                1: self.second_digit,
                2: self.third_digit,
                3: self.fourth_digit
                }
        for i, ec_digit in enumerate(ec_digits):
            if ec_digit == '-':
                digit_translation_d[i] = None
            else:
                digit_translation_d[i] = int(ec_digit)

    __mapper_args__ = {
            'polymorphic_identity': 'ecnumber'
        }
