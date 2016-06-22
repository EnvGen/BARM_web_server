from app import db
import sqlalchemy
from materialized_view_factory import MaterializedView, create_mat_view
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
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    def __init__(self, time, latitude, longitude):
        self.time = time
        self.latitude = float(latitude)
        self.longitude = float(longitude)

    def __repr__(self):
        return '<TimePlace {}>'.format(self.id)

    def date_formatted(self):
        return self.time.strftime('%Y-%m-%d')

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

    rpkm_table_rows = db.relationship('RpkmTable', backref='sample',
                                primaryjoin='Sample.id==RpkmTable.sample_id',
                                foreign_keys='RpkmTable.sample_id')

    def __init__(self, scilifelab_code, sample_set, timeplace):
        self.scilifelab_code = scilifelab_code
        self.sample_set = sample_set
        self.timeplace = timeplace

    def __repr__(self):
        return '<Sample {}>'.format(self.id)


    @classmethod
    def all_from_sample_sets(self, sample_sets):
        # Use only the annotations which has the highest total
        q = db.session.query(Sample).\
                join(SampleSet).\
                filter(Sample.sample_set_id == SampleSet.id).\
                filter(SampleSet.name.in_(sample_sets))

        return q.all()

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
    taxon_id = db.Column(db.Integer, db.ForeignKey('taxon.id'))
    taxon = db.relationship("Taxon",
            backref=db.backref("genes"))
    gene_annotations = db.relationship("GeneAnnotation")


    def __init__(self, name, reference_assembly, taxon_id=None):
        self.name = name
        self.reference_assembly = reference_assembly
        self.taxon_id = taxon_id

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

class Taxon(db.Model):
    __tablename__ = 'taxon'
    id = db.Column(db.Integer, primary_key=True)

    up_to_superkingdom = db.Column(db.String)
    up_to_phylum = db.Column(db.String)
    up_to_taxclass = db.Column(db.String)
    up_to_order = db.Column(db.String)
    up_to_family = db.Column(db.String)
    up_to_genus = db.Column(db.String)
    up_to_species = db.Column(db.String)
    full_taxonomy = db.Column(db.String)

    def __init__(self, superkingdom = None, phylum=None, taxclass=None, order=None, family=None, genus=None, species=None):
        tax_l = [superkingdom, phylum, taxclass, order, family, genus, species]

        full_taxonomy = ""
        for tax_value in tax_l:
            if tax_value is not None:
                full_taxonomy += tax_value
            full_taxonomy += ";"
        self.full_taxonomy = full_taxonomy
        self.up_to_superkingdom = ";".join(full_taxonomy.split(';')[0:1])
        self.up_to_phylum = ";".join(full_taxonomy.split(';')[0:2])
        self.up_to_taxclass = ";".join(full_taxonomy.split(';')[0:3])
        self.up_to_order = ";".join(full_taxonomy.split(';')[0:4])
        self.up_to_family = ";".join(full_taxonomy.split(';')[0:5])
        self.up_to_genus = ";".join(full_taxonomy.split(';')[0:6])
        self.up_to_species = ";".join(full_taxonomy.split(';')[0:7])

    @property
    def superkingdom(self):
        return self.up_to_superkingdom

    @property
    def phylum(self):
        return self.up_to_phylum.split(';')[-1]

    @property
    def taxclass(self):
        return self.up_to_taxclass.split(';')[-1]

    @property
    def order(self):
        return self.up_to_order.split(';')[-1]

    @property
    def family(self):
        return self.up_to_family.split(';')[-1]

    @property
    def genus(self):
        return self.up_to_genus.split(';')[-1]

    @property
    def species(self):
        return self.up_to_species.split(';')[-1]

    @classmethod
    def rpkm_table(self, level="superkingdom", top_level_complete_value=None, top_level=None, samples=None, limit=20):
        filter_level = "up_to_" + level
        q_first = db.session.query(getattr(Taxon, filter_level), sqlalchemy.func.sum(GeneCount.rpkm)).\
            join(Gene).join(GeneCount).\
            order_by(sqlalchemy.func.sum(GeneCount.rpkm).desc())

        if top_level is not None:
            filter_top_level = "up_to_" + top_level
            q_first = q_first.filter(getattr(Taxon, filter_top_level) == top_level_complete_value)

        if samples is not None:
            q_first = q_first.\
                        join(Sample).\
                        filter(Sample.scilifelab_code.in_(samples))

        q_first = q_first.group_by(getattr(Taxon, filter_level)).limit(limit)

        taxon_counts = q_first.all()
        taxon_level_vals = []
        for level_val, count in taxon_counts:
            taxon_level_vals.append(level_val)

        q = db.session.query(Sample, getattr(Taxon, filter_level), sqlalchemy.func.sum(GeneCount.rpkm)).\
                join(GeneCount).join(Gene).join(Taxon).\
                filter(getattr(Taxon, filter_level).in_(taxon_level_vals))

        if samples is None:
            samples = Sample.query.all()
        else:
            q = q.filter(Sample.scilifelab_code.in_(samples))
            samples = Sample.query.filter(Sample.scilifelab_code.in_(samples)).all()


        q = q.group_by(getattr(Taxon, filter_level)).\
                group_by(Sample.id).order_by(sqlalchemy.func.sum(GeneCount.rpkm))

        unsorted_rows = {}
        for sample, level_val, rpkm in q.all():
            if level_val in unsorted_rows:
                unsorted_rows[level_val][sample] = rpkm
            else:
                unsorted_rows[level_val] = collections.OrderedDict()
                unsorted_rows[level_val][sample] = rpkm

        sorted_rows = collections.OrderedDict()
        for complete_level_val in taxon_level_vals:
            level_val = complete_level_val.split(';')[-1]
            sorted_rows[(complete_level_val, level_val)] = unsorted_rows[complete_level_val]

        return samples, sorted_rows

    @property
    def rpkm(self):
        q = db.session.query(Sample, sqlalchemy.func.sum(GeneCount.rpkm)).\
                join(GeneCount).\
                filter(Sample.id == GeneCount.sample_id).\
                join(Gene).\
                filter(GeneCount.gene_id == Gene.id).\
                join(Taxon).\
                filter(Taxon.id == self.id).\
                group_by(Sample.id)

        return { sample: rpkm_sum for sample, rpkm_sum in q.all() }

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

    rpkm_table_rows = db.relationship('RpkmTable', backref='annotation',
                                primaryjoin='Annotation.id==RpkmTable.annotation_id',
                                foreign_keys='RpkmTable.annotation_id')

    @classmethod
    def genes_per_annotation(self, annotation_ids):
        q = db.session.query(Gene, Annotation).\
                join(GeneAnnotation).\
                join(Annotation).\
                filter(GeneAnnotation.annotation_id.in_(annotation_ids))
        return q.all()

    @classmethod
    def rpkm_table(self, samples=None, function_class=None, limit=20, type_identifiers=None):
        q_first = db.session.query(RpkmTable.annotation_id)

        if function_class is not None:
            q_first = q_first.filter(RpkmTable.annotation_type == function_class)

        if type_identifiers is not None:
            annotation_ids_from_type_ids = db.session.query(Annotation.id).\
                        filter(Annotation.type_identifier.in_(type_identifiers)).all()
            q_first = q_first.\
                         filter(RpkmTable.annotation_id.in_(annotation_ids_from_type_ids))

        if samples is not None:
            q_first = q_first.\
                        filter(RpkmTable.sample_scilifelab_code.in_(samples))

        q_first = q_first.group_by(RpkmTable.annotation_id).\
                        order_by(sqlalchemy.func.sum(RpkmTable.rpkm).desc())

        if limit is not None:
            q_first = q_first.limit(limit)

        annotation_ids = [annotation_id_t[0] for annotation_id_t in q_first.all()]

        if not len(annotation_ids):
            return [], {}

        q = db.session.query(RpkmTable).\
                filter(RpkmTable.annotation_id.in_(annotation_ids))

        if samples is not None:
            q = q.filter(RpkmTable.sample_scilifelab_code.in_(samples))

        q = q.order_by(RpkmTable.annotation_id, RpkmTable.sample_id)
        # format to have one row per list item
        rows_unordered = {}
        samples = set()
        fetched_annotations = {}
        for rpkm_table_row in q.all():
            sample = rpkm_table_row.sample
            annotation = rpkm_table_row.annotation
            rpkm_sum = rpkm_table_row.rpkm

            samples.add(sample)
            fetched_annotations[annotation.id] = annotation
            if annotation in rows_unordered:
                rows_unordered[annotation][sample] = rpkm_sum
            else:
                rows_unordered[annotation] = collections.OrderedDict()
                rows_unordered[annotation][sample] = rpkm_sum

        rows = collections.OrderedDict()

        for annotation_id in annotation_ids:
            annotation = fetched_annotations[annotation_id]
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

    @property
    def short_description(self):
        if len(self.description) > 100:
            return "{}...".format(self.description[:100])
        else:
            return self.description

    __mapper_args__ = {
            'polymorphic_identity': 'annotation',
            'polymorphic_on': annotation_type
        }

    def __init__(self, type_identifier, description = None):
        self.type_identifier = type_identifier
        self.description = description

class RpkmTable(MaterializedView):
    # A materialized view that improve the performance

    creation_query = db.select([Annotation.id.label('annotation_id'), Annotation.annotation_type.label('annotation_type'), Sample.id.label('sample_id'), Sample.scilifelab_code.label('sample_scilifelab_code'), sqlalchemy.func.sum(GeneCount.rpkm).label('rpkm')]).\
                    select_from(db.join(Sample, GeneCount).join(Gene).join(GeneAnnotation).join(Annotation)).\
                    group_by(Annotation.id, Sample.id)

    __table__ = create_mat_view("rpkm_table", creation_query)


db.Index('rpkm_table_mv_id_idx', RpkmTable.annotation_id, RpkmTable.sample_id, unique=True)

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

    @property
    def external_link(self):
        return "http://www.ncbi.nlm.nih.gov/Structure/cdd/cddsrv.cgi?uid={}".format(self.type_identifier)

class Pfam(Annotation):
    __tablename__ = 'pfam'
    id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'pfam'
        }

    @property
    def external_link(self):
        external_id = self.type_identifier.replace("pfam", "PF").replace("PFAM", "PF")
        return "http://pfam.xfam.org/family/{}".format(external_id)

class TigrFam(Annotation):
    __tablename__ = 'tigrfam'
    id = db.Column(db.Integer, db.ForeignKey("annotation.id"),
            primary_key=True)

    __mapper_args__ = {
            'polymorphic_identity': 'tigrfam'
        }

    @property
    def external_link(self):
        if self.type_identifier[:4] != 'TIGR':
            external_id = self.type_identifier.replace(self.type_identifier[:4], 'TIGR')
        else:
            external_id = self.type_identifier
        return "http://www.jcvi.org/cgi-bin/tigrfams/HmmReportPage.cgi?acc={}".format(external_id)

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
