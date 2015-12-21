from app import db

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

gene_annotation = db.Table('gene_annotation', 
        db.Column('annotation_id', db.Integer, db.ForeignKey('annotation.id')),
        db.Column('gene_id', db.Integer, db.ForeignKey('gene.id'))
    )

class Gene(db.Model):
    __tablename__ = 'gene'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String())
    reference_assemlby_id = db.Column(db.Integer, 
            db.ForeignKey('reference_assembly.id'))
    reference_assembly = db.relationship("ReferenceAssembly",
            backref=db.backref("genes"))

    def __init__(self, name, reference_assembly):
        self.name = name
        self.reference_assembly = reference_assembly

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
    id = db.Column(db.Integer, primary_key=True)

    source_id = db.Column(db.Integer, db.ForeignKey('annotation_source.id'),
            nullable=False)
    source = db.relationship('AnnotationSource',
            backref=db.backref('annotations'))
    annotation_type = db.Column(db.String)
    
    genes = db.relationship('Gene', secondary=gene_annotation,
            backref=db.backref('annotations'))

    def __init__(self, annotation_type, annotation_source):
        self.annotation_type = annotation_type
        self.source = annotation_source

