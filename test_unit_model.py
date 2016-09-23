import unittest
import app
from models import Sample, SampleSet, TimePlace, SampleProperty, ReferenceAssembly, Gene, \
    GeneCount, AnnotationSource, Annotation, GeneAnnotation, Cog, Pfam, TigrFam, EcNumber, \
    RpkmTable, Taxon, TaxonRpkmTable
import sqlalchemy

import itertools
import datetime

from materialized_view_factory import refresh_all_mat_views

class SampleTestCase(unittest.TestCase):
    """Test that a sample in the database has the correct relations"""
    def setUp(self):
        self.db = app.db
        self.db.create_all()

        self.session = self.db.session

        self.connection = self.session.connection()

        self.trans = self.connection.begin()

    def tearDown(self):
        # clear the database
        self.session.close()

        self.trans.rollback()

        self.connection.close()

        self.db.drop_all()

    def test_sample(self):
        all_samples_before = Sample.query.all()
        assert len(all_samples_before) == 0
        sample = Sample("P1993_101", None, None)
        self.session.add(sample)
        self.session.commit()

        all_samples_after = Sample.query.all()
        assert len(all_samples_after) == 1

    def test_sample_sampleset(self):
        #Test that sample and sample set references each other properly
        sample_set = SampleSet("first_sampleset")
        sample1 = Sample("P1993_101", sample_set, None)

        self.session.add(sample1)
        self.session.add(sample_set)

        # Sample sets relations are created
        assert Sample.query.filter_by(scilifelab_code='P1993_101').first().sample_set is sample_set

        sample_set2 = SampleSet("second_sampleset")
        sample2 = Sample("P1993_102", sample_set2, None)
        sample3 = Sample("P1993_103", sample_set, None)
        self.session.add(sample2)
        self.session.add(sample3)

        self.session.commit()

        # Sample2 should have sample set 2
        assert Sample.query.filter_by(scilifelab_code='P1993_102').first().sample_set is sample_set2

        # There should be 2 sample sets and 3 samples in the db
        assert len(SampleSet.query.all()) == 2
        assert len(Sample.query.all()) == 3

        # The reverse relationship for sample set 2 should have sample1 and sample3
        assert len(sample_set.samples) == 2

        assert sample2 not in sample_set.samples
        assert sample1 in sample_set.samples
        assert sample3 in sample_set.samples

        assert len(Sample.all_from_sample_sets(['first_sampleset'])) == 2
        assert sample1 in Sample.all_from_sample_sets(['first_sampleset'])
        assert sample3 in Sample.all_from_sample_sets(['first_sampleset'])
        assert sample2 not in Sample.all_from_sample_sets(['first_sampleset'])

        assert len(Sample.all_from_sample_sets(['second_sampleset'])) == 1
        assert sample1 not in Sample.all_from_sample_sets(['second_sampleset'])
        assert sample3 not in Sample.all_from_sample_sets(['second_sampleset'])
        assert sample2 in Sample.all_from_sample_sets(['second_sampleset'])

        assert len(Sample.all_from_sample_sets(['second_sampleset', 'first_sampleset'])) == 3
        assert sample1 in Sample.all_from_sample_sets(['second_sampleset', 'first_sampleset'])
        assert sample3 in Sample.all_from_sample_sets(['second_sampleset', 'first_sampleset'])
        assert sample2 in Sample.all_from_sample_sets(['second_sampleset', 'first_sampleset'])

    def test_sample_timeplace(self):
        sample_set = SampleSet("first_sampleset")
        sample1 = Sample("P1993_101", sample_set, None)
        time_place1 = TimePlace(datetime.datetime.now(), "52.3820818", "18.0233369")
        sample1.timeplace = time_place1
        self.session.add(sample1)
        self.session.add(time_place1)
        # The sample should have the correct time place
        assert Sample.query.first().timeplace == time_place1

        # One can also add it after sample creation
        sample2 = Sample("P1993_102", sample_set, None)
        sample2.timeplace = time_place1

        self.session.add(sample2)
        self.session.commit()

        # The only existing time place should contain exactly sample1 and sample2
        assert len(TimePlace.query.first().samples) == 2
        assert sample1 in TimePlace.query.first().samples
        assert sample2 in TimePlace.query.first().samples

        time_place2 = TimePlace(datetime.date(1999,3,21), "42.3820818", "108.0233369")

        sample3 = Sample("P1993_103", sample_set, None)
        sample3.timeplace = time_place2

        self.session.add(sample3)
        self.session.add(time_place2)
        self.session.commit()

        assert len(TimePlace.query.all()) == 2
        assert sample3.timeplace.latitude < sample2.timeplace.latitude
        assert sample3.timeplace.longitude > sample2.timeplace.longitude

        assert sample3.timeplace.time < sample2.timeplace.time

        assert sample3.timeplace.date_formatted() == '1999-03-21'


    def test_sample_sample_property(self):
        sample1 = Sample("P1993_101", None, None)
        sample_prop = SampleProperty(name="Salinity", value="16", unit="PSU", sample=sample1)
        self.session.add(sample_prop)
        self.session.commit()

        assert sample_prop in sample1.properties

    def test_reference_assembly(self):
        ref_assembly = ReferenceAssembly("Version 1")
        self.session.add(ref_assembly)
        self.session.commit()

        assert ReferenceAssembly.query.first() is ref_assembly
        assert len(ref_assembly.genes) == 0

    def test_gene(self):
        ref_assembly = ReferenceAssembly("Version 1")
        gene1 = Gene("gene1", ref_assembly)

        self.session.add(gene1)
        self.session.commit()

        # Test gene creation
        assert Gene.query.first() is gene1

        # Test gene reference assembly membership
        ref_assembly2 = ReferenceAssembly("Version 2")
        gene2 = Gene("gene1", ref_assembly2)
        self.session.add(gene2)
        self.session.commit()

        assert gene1 in ReferenceAssembly.query.filter_by(name="Version 1").first().genes
        assert len(ReferenceAssembly.query.filter_by(name="Version 1").first().genes) == 1

        assert gene2 in ReferenceAssembly.query.filter_by(name="Version 2").first().genes
        assert len(ReferenceAssembly.query.filter_by(name="Version 1").first().genes) == 1

        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            # Only one gene per name and reference assembly
            gene3 = Gene("gene1", ref_assembly)
            self.session.add(gene3)
            self.session.commit()

    def test_gene_count(self):
        sample1 = Sample("P1993_101", None, None)
        reference_assembly = ReferenceAssembly("version 1")
        gene1 = Gene("gene1", reference_assembly)
        gene_count1 = GeneCount(gene1, sample1, 0.001)

        self.session.add(gene_count1)
        self.session.commit()

        assert GeneCount.query.first() is gene_count1

        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            # Only one gene count per gene and sample
            gene_count2 = GeneCount(gene1, sample1, 0.12)
            self.session.add(gene_count2)
            self.session.commit()

        self.session.rollback()


        # Test sample count retreival
        sample2 = Sample("P1993_102", None, None)
        self.session.add(sample2)
        self.session.commit()

        gene1 = Gene.query.filter_by(name="gene1").first()
        assert len(gene1.sample_counts) == 1
        assert gene1.rpkm == {sample1: 0.001}

        gene_count2 = GeneCount(gene1, sample2, 0.2)
        self.session.add(gene_count2)
        self.session.commit()
        assert gene1.rpkm == {sample1: 0.001, sample2: 0.2}

    def test_taxon(self):
        ref_assembly = ReferenceAssembly("Version 1")
        gene1 = Gene("gene1", ref_assembly)

        sample1 = Sample("P1993_101", None, None)
        reference_assembly = ReferenceAssembly("version 1")
        gene_count1 = GeneCount(gene1, sample1, 0.001)
        taxon1 = Taxon(superkingdom="Bacteria", phylum="Proteobacteria")
        gene1.taxon = taxon1
        self.session.add(gene1)
        self.session.add(taxon1)
        self.session.add(sample1)
        self.session.add(gene_count1)
        self.session.commit()

        gene1 = Gene.query.first()
        taxon1 = Taxon.query.first()

        assert gene1.taxon == taxon1
        assert gene1 in taxon1.genes
        assert taxon1.superkingdom == 'Bacteria'
        assert taxon1.phylum == 'Proteobacteria'
        assert taxon1.taxclass == ''
        assert taxon1.full_taxonomy == 'Bacteria;Proteobacteria;;;;;;'
        refresh_all_mat_views()

        # Test sample count retreival
        sample2 = Sample("P1993_102", None, None)
        self.session.add(sample2)
        self.session.commit()
        refresh_all_mat_views()
        assert taxon1.rpkm == {sample1: 0.001}

        gene_count2 = GeneCount(gene1, sample2, 0.2)
        self.session.add(gene_count2)
        self.session.commit()
        refresh_all_mat_views()
        assert taxon1.rpkm == {sample1: 0.001, sample2: 0.2}

        gene2 = Gene("gene2", ref_assembly)
        gene_count3 = GeneCount(gene2, sample2, 0.1)

        self.session.add(gene2)
        self.session.add(gene_count3)
        self.session.commit()
        refresh_all_mat_views()

        # taxon1.rpkm should still be the same since the new gene is not connected to taxon1
        assert taxon1.rpkm == {sample1: 0.001, sample2: 0.2}

        taxon2 = Taxon(superkingdom="Eukaryota", phylum="Chlorophyta")
        gene2.taxon = taxon2
        self.session.add(taxon2)
        self.session.add(gene2)
        self.session.commit()
        refresh_all_mat_views()

        # Taxon2 should have gene_count3 stats only
        assert taxon2.rpkm == {sample2: 0.1}

        gene3 = Gene("gene3", ref_assembly, taxon_id=taxon1.id)
        gene_count4 = GeneCount(gene3, sample1, 1.0)

        self.session.add(gene3)
        self.session.add(gene_count4)
        self.session.commit()

        # Taxon1 should now have the original stats plus gene_count4
        assert taxon1.rpkm == {sample1: 1.001, sample2: 0.2}


        taxon3 = Taxon(superkingdom="Eukaryota", phylum="Unnamed", taxclass="Dinophyceae")
        self.session.add(taxon3)
        self.session.commit()
        gene4 = Gene("gene4", ref_assembly, taxon_id=taxon3.id)
        gene_count5 = GeneCount(gene4, sample2, 0.003)

        self.session.add(gene4)
        self.session.add(gene_count5)
        self.session.commit()
        refresh_all_mat_views()

        # theoretical rpkm_table:
        # samples = [sample1, sample2]
        # rpkm_table = {"Bacteria": {"P1993_101": 1.001, "P1993_102": 0.2}, "Eukaryota": {"P1993_102": 0.103}}
        samples, rpkm_table, complete_val_to_val = Taxon.rpkm_table()
        assert samples == [sample1, sample2]
        assert [complete_val_to_val[complete_level_val] for complete_level_val in rpkm_table.keys()] == ["Bacteria", "Eukaryota"] # Sorted by summed rpkm
        assert rpkm_table[("Bacteria")] == {sample1: 1.001, sample2: 0.2}
        assert rpkm_table[("Eukaryota")] == {sample2: 0.103}

        samples, rpkm_table, complete_val_to_val= Taxon.rpkm_table(level='phylum')
        assert samples == [sample1, sample2]
        assert [complete_val_to_val[complete_level_val] for complete_level_val in rpkm_table.keys()] == ["Proteobacteria", "Chlorophyta", "Unnamed"] # Sorted by summed rpkm

        assert rpkm_table[("Bacteria;Proteobacteria")] == {sample1: 1.001, sample2: 0.2}
        assert rpkm_table[("Eukaryota;Chlorophyta")] == {sample2: 0.1}
        assert rpkm_table[("Eukaryota;Unnamed")] == {sample2: 0.003}


    def test_taxon_large_scale_rpkm_table(self):
        sample1 = Sample("P1993_101", None, None)
        sample2 = Sample("P1993_102", None, None)
        nr_samples = 2
        taxons = []
        for euk_i in range(2):
            for ph_i in range(3):
                for tc_i in range(20):
                    taxons.append(Taxon(superkingdom="sk_{}".format(euk_i),
                        phylum="ph_{}".format(ph_i),
                        taxclass="tc_{}".format(tc_i)))

        self.session.add_all(taxons)
        self.session.commit()
        refresh_all_mat_views()

        for i,taxon in enumerate(taxons):
            count_mode = i % 3
            gene_counts = []

            gene1 = Gene("gene1{}".format(i), None, taxon_id=taxon.id)
            gene2 = Gene("gene2{}".format(i), None, taxon_id=taxon.id)

            if count_mode in [0,1]:
                gene_counts.append(GeneCount(gene1, sample1, 0.001))
                gene_counts.append(GeneCount(gene1, sample2, 0.01))
            if count_mode in [1,2]:
                gene_counts.append(GeneCount(gene2, sample1, 0.002))
                gene_counts.append(GeneCount(gene2, sample2, 0.02))

            self.session.add_all(gene_counts)

            self.session.add(gene1)
            self.session.add(gene2)

        self.session.commit()
        refresh_all_mat_views()

        samples, rows, complete_val_to_val = Taxon.rpkm_table()
        assert len(samples) == 2
        assert len(rows) == 2 # Number of unique superkingdoms

        samples, rows, complete_val_to_val = Taxon.rpkm_table(level="phylum")
        assert len(samples) == 2
        assert len(rows) == 6 # Number of unique down to phylum

        samples, rows, complete_val_to_val = Taxon.rpkm_table(level="taxclass")
        assert len(samples) == 2
        assert len(rows) == 20 # Default limit

        samples, rows, complete_val_to_val = Taxon.rpkm_table(level="taxclass", limit=None)
        assert len(samples) == 2
        assert len(rows) == 120 # Number of unique down to taxclass

        samples, rows, complete_val_to_val = Taxon.rpkm_table(level="taxclass", limit=None)

        for taxon, sample_d in rows.items():
            # sample_d should be a ordered dict
            assert ["P1993_101", "P1993_102"] == [sample.scilifelab_code for sample in sample_d.keys()]
        rpkms = [[rpkm for sample, rpkm in sample_d.items()] for taxon, sample_d in rows.items()]

        rpkms_flat = []
        for rpkm_row in rpkms:
            rpkms_flat += rpkm_row

        assert len(rpkms_flat) == 2 * 3 * 20 * nr_samples

        # Annotations sorted by total rpkm over all samples
        # and the rpkm values should be summed over all genes for that taxon
        # there should be roughly equal numbers of the three different counts
        for i, row in enumerate(rpkms[:40]):
            assert row == [0.003, 0.03]
        for row in rpkms[40:80]:
            assert row == [0.002, 0.02]
        for row in rpkms[80:120]:
            assert row == [0.001, 0.01]

        # possible to filter on specific level values at superkingdom
        for level_val in ["sk_0", "sk_1"]:
            samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=[level_val], top_level="superkingdom", level="phylum")
            assert len(rows) == 3
            level_vals = [complete_val_to_val[complete_val] for complete_val in rows.keys()]
            assert level_vals == ["ph_2", "ph_0", "ph_1"]
            samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=[level_val], top_level="superkingdom", level="taxclass")
            assert len(rows) == 3*20


        # possible to filter on specific level values at phylum
        for sk_level_val in ["sk_0", "sk_1"]:
            for ph_level_val in ["ph_0", "ph_1", "ph_2"]:
                top_level_complete_value="{};{}".format(sk_level_val, ph_level_val)
                samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=[top_level_complete_value], top_level="phylum", level="phylum")
                assert len(rows) == 1
                level_vals = [complete_val_to_val[complete_val] for complete_val in rows.keys()]
                assert level_vals == [ph_level_val]
                samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=[top_level_complete_value], top_level="phylum", level="taxclass")
                assert len(rows) == 20

        # possible to filter on multiple specific level values at phylum
        for sk_level_val in ["sk_0", "sk_1"]:
            for ph_level_vals in itertools.combinations(["ph_0", "ph_1", "ph_2"], 2):
                top_level_complete_values = []
                for ph_level_val in ph_level_vals:
                    top_level_complete_values.append("{};{}".format(sk_level_val, ph_level_val))
                samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=top_level_complete_values, top_level="phylum", level="phylum")
                assert len(rows) == 2
                level_vals = [complete_val_to_val[complete_val] for complete_val in rows.keys()]
                assert sorted(level_vals) == sorted(list(ph_level_vals))
                samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=top_level_complete_values, top_level="phylum", level="taxclass")
                assert len(rows) == 40

        # possible to filter on specific level values at taxclass
        for sk_level_val in ["sk_0", "sk_1"]:
            for ph_level_val in ["ph_0", "ph_1", "ph_2"]:
                for tc_level_val in ["tc_{}".format(i) for i in range(20)]:
                    top_level_complete_value="{};{};{}".format(sk_level_val, ph_level_val, tc_level_val)
                    samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=[top_level_complete_value], top_level="taxclass", level="taxclass")
                    assert len(rows) == 1

        # possible to filter on specific level values at taxclass
        for sk_level_val in ["sk_0", "sk_1"]:
            for ph_level_val in ["ph_0", "ph_1", "ph_2"]:
                for tc_level_vals in itertools.combinations(["tc_{}".format(i) for i in range(5)], 4):
                    top_level_complete_values = []
                    for tc_level_val in tc_level_vals:
                        top_level_complete_values.append("{};{};{}".format(sk_level_val, ph_level_val, tc_level_val))
                    samples, rows, complete_val_to_val = Taxon.rpkm_table(limit=None, top_level_complete_values=top_level_complete_values, top_level="taxclass", level="taxclass")
                    assert len(rows) == 4

        # possible to filter on samples
        for sample in [sample1, sample2]:
            samples, rows, complete_val_to_val = Taxon.rpkm_table(samples=[sample.scilifelab_code], level="taxclass", limit=None)
            assert len(rows) == 120
            assert len(samples) == 1
            assert samples[0] == sample
            for taxon, sample_d in rows.items():
                assert list(sample_d.keys()) == [sample]

            rpkms = [[rpkm for sample, rpkm in sample_d.items()] for taxon, sample_d in rows.items()]
            if sample.scilifelab_code == "P1993_101":
                for i, row in enumerate(rpkms[:40]):
                    assert row == [0.003]
                for row in rpkms[40:80]:
                    assert row == [0.002]
                for row in rpkms[80:120]:
                    assert row == [0.001]
            else:
                for row in rpkms[:40]:
                    assert row == [0.03]
                for row in rpkms[40:80]:
                    assert row == [0.02]
                for row in rpkms[80:120]:
                    assert row == [0.01]

        # possible to filter on sample and taxon at the same time
        for sample in [sample1, sample2]:
            for sk_level_val in ["sk_0", "sk_1"]:
                top_level_complete_value = sk_level_val
                samples, rows, complete_val_to_val = Taxon.rpkm_table(samples=[sample.scilifelab_code], limit=None, top_level_complete_values=[top_level_complete_value], top_level="superkingdom", level="phylum")
                assert len(samples) == 1
                assert samples[0] == sample
                for taxon, sample_d in rows.items():
                    assert list(sample_d.keys()) == [sample]

                assert len(rows) == 3
                level_vals = [complete_val_to_val[complete_val] for complete_val in rows.keys()]
                assert level_vals == ["ph_2", "ph_0", "ph_1"]
                samples, rows, complete_val_to_val = Taxon.rpkm_table(samples=[sample.scilifelab_code], limit=None, top_level_complete_values=[top_level_complete_value], top_level="superkingdom", level="taxclass")
                assert len(rows) == 3*20


                rpkms = [[rpkm for sample, rpkm in sample_d.items()] for annotation, sample_d in rows.items()]
                if sample.scilifelab_code == "P1993_101":
                    for row in rpkms[:20]:
                        assert row == [0.003]
                    for row in rpkms[20:40]:
                        assert row == [0.002]
                    for row in rpkms[40:60]:
                        assert row == [0.001]
                else:
                    for row in rpkms[:20]:
                        assert row == [0.03]
                    for row in rpkms[20:40]:
                        assert row == [0.02]
                    for row in rpkms[40:80]:
                        assert row == [0.01]




    def test_annotation_source(self):
        annotation_source = AnnotationSource("Cog", "v1.0", "rpsblast", "e_value=0.000001")
        self.session.add(annotation_source)
        self.session.commit()

        assert AnnotationSource.query.first() is annotation_source
        assert len(annotation_source.annotations) == 0

    def test_annotation(self):
        annotation = Annotation("COG0001")
        self.session.add(annotation)
        self.session.commit()

        assert Annotation.query.first() is annotation

        #Test the many to many relationship
        reference_assembly = ReferenceAssembly("version 1")
        gene = Gene("gene1", reference_assembly)
        gene2 = Gene("gene2", reference_assembly)
        gene3 = Gene("gene3", reference_assembly)

        annotation2 = Annotation("COG0002", description="This cog is really really good")
        # Test having multiple genes to one annotation
        annotation_source = AnnotationSource("Cog", "v1.0", "rpsblast", "e_value=0.000001")
        gene_annotation1 = GeneAnnotation(annotation_source = annotation_source, e_value=0.0000001)
        gene_annotation2 = GeneAnnotation(annotation_source = annotation_source)

        gene_annotation1.gene = gene
        gene_annotation2.gene = gene2

        gene_annotation1.annotation = annotation
        gene_annotation2.annotation = annotation

        self.session.add(annotation)
        self.session.add(gene3)
        self.session.add(gene_annotation1)
        self.session.add(gene_annotation2)
        self.session.commit()

        annotation_01 = Annotation.query.filter_by(type_identifier="COG0001").first()
        assert len(annotation_01.genes) == 2
        assert gene in annotation_01.genes
        assert gene2 in annotation_01.genes
        assert annotation in Gene.query.filter_by(name="gene1").first().annotations
        assert annotation in Gene.query.filter_by(name="gene2").first().annotations
        assert len(Gene.query.filter_by(name="gene3").first().annotations) == 0

        # Genes for annotation method
        genes_for_annotation = Annotation.genes_per_annotation([annotation.id])
        assert len(genes_for_annotation) == 2
        assert (gene, annotation) in genes_for_annotation
        assert (gene2, annotation)  in genes_for_annotation

        # Add the second annotation
        self.session.add(annotation2)
        self.session.commit()
        q =  Annotation.query.filter(Annotation.description.contains("good"))
        annotation_02 = q.all()
        assert len(annotation_02) == 1
        assert annotation_02[0] == annotation2

        # Test having multiple annotations to one gene
        gene_annotation3 = GeneAnnotation(annotation2, gene, annotation_source, e_value = 1e-14)
        self.session.add(gene_annotation3)
        self.session.commit()

        assert len(Gene.query.filter_by(name="gene1").first().annotations) == 2
        assert annotation in Gene.query.filter_by(name="gene1").first().annotations
        assert annotation2 in Gene.query.filter_by(name="gene1").first().annotations

        assert gene_annotation1.e_value > gene_annotation3.e_value
        assert gene.e_value_for(annotation) > gene.e_value_for(annotation2)

        # gene -> annotation
        # gene2 -> annotation
        # gene -> annotation2

        # Genes for annotation method
        genes_for_annotation = Annotation.genes_per_annotation([annotation.id])
        assert len(genes_for_annotation) == 2
        assert (gene, annotation) in genes_for_annotation
        assert (gene2, annotation) in genes_for_annotation

        genes_for_annotation = Annotation.genes_per_annotation([annotation2.id])
        assert len(genes_for_annotation) == 1
        assert (gene, annotation2) in genes_for_annotation

        genes_for_annotation = Annotation.genes_per_annotation([annotation.id, annotation2.id])
        assert len(genes_for_annotation) == 3
        assert (gene, annotation) in genes_for_annotation
        assert (gene, annotation2) in genes_for_annotation
        assert (gene2, annotation) in genes_for_annotation

        annotation3 = Annotation("COG0003", description=("This cog is really really good. I assure you, "
            "really quite good. Among its capabilities I have to mention that its utterly suitable for "
            "testing the description string, including the short description."))

        assert len(annotation3.description) > 103
        assert annotation3.short_description[-3:] == "..."
        assert len(annotation3.short_description) == 103
        assert annotation3.description[:100] == annotation3.short_description[:100]


    def test_annotation_type_inheritance(self):
        annotation2 = Pfam("pfam00002")
        annotation = Cog("COG0001", "H")
        annotation3 = TigrFam("TIGR00004")

        assert annotation2.annotation_type == 'pfam'
        assert annotation.annotation_type == 'cog'
        assert annotation3.annotation_type == 'tigrfam'

        gene = Gene("gene1", None)
        annotation_source1 = AnnotationSource("Cog", "v1.0", "rpsblast", "e_value=0.00001")
        annotation_source2 = AnnotationSource("Pfam", "v1.0", "rpsblast", "e_value=0.00001")
        gene_annotation = GeneAnnotation(annotation, gene, annotation_source1)
        self.session.add(gene)
        self.session.add(annotation)
        self.session.add(annotation2)
        self.session.add(gene_annotation)
        self.session.commit()

        # category is defined on cog class
        assert annotation.category == "H"
        # Genes is defined on the annotation base class
        assert gene in annotation.genes

        for subclass, type_ident in [(Cog, "COG0001"), (Pfam, "pfam00002")]:
            # The same type identifier can only be in the db once,
            # per subcategory
            with self.assertRaises(sqlalchemy.exc.IntegrityError):
                if subclass == Cog:
                    annotation = subclass(type_ident, "G")
                else:
                    annotation = subclass(type_ident)
                self.session.add(annotation)
                self.session.commit()

            self.session.rollback()

        # Multiple GeneAnnotations for the same subclass is only
        # possible when different sources are used
        # Annotation source column values can be identical
        annotation_source3 = AnnotationSource("Cog", "v1.0", "rpsblast", "e_value=0.00001")
        annotation = Cog.query.filter_by(type_identifier="COG0001").first()
        gene_annotation = GeneAnnotation(annotation, gene, annotation_source3)
        self.session.add(gene_annotation)
        self.session.commit()

        assert len(GeneAnnotation.query.filter_by(gene = gene,
            annotation = annotation).all()) == 2

        # Identical connection between genes and annotations is ok
        gene_annotation_fail = GeneAnnotation(annotation, gene, annotation_source1)
        self.session.add(gene_annotation_fail)
        self.session.commit()

        assert len(GeneAnnotation.query.filter_by(gene = gene,
            annotation = annotation).all()) == 3

        # A different annotation_type is either not sufficient to
        # have the same type_identifier twice
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            annotation4 = Pfam("COG0001")
            self.session.add(annotation4)
            self.session.commit()

        self.session.rollback()
        assert len(Annotation.query.filter_by(type_identifier="COG0001").all()) == 1

        assert annotation.external_link == "http://www.ncbi.nlm.nih.gov/Structure/cdd/cddsrv.cgi?uid=COG0001"
        assert annotation2.external_link == "http://pfam.xfam.org/family/PF00002"
        assert annotation3.external_link == "http://www.jcvi.org/cgi-bin/tigrfams/HmmReportPage.cgi?acc=TIGR00004"

    def test_annotation_rpkm(self):
        annotation1 = Annotation("COG0001")
        annotation2 = Annotation("COG0002")
        annotation3 = Annotation("Pfam0001")
        gene1 = Gene("gene1", None)
        gene2 = Gene("gene2", None)
        annotation_source = AnnotationSource("Cog", "v1.0", "rpsblast", "e_value=0.000001")
        gene_annotation1 = GeneAnnotation(annotation1, gene1, annotation_source)
        gene_annotation2 = GeneAnnotation(annotation1, gene2, annotation_source)
        gene_annotation3 = GeneAnnotation(annotation2, gene1, annotation_source)
        gene_annotation4 = GeneAnnotation(annotation3, gene2, annotation_source)
        sample1 = Sample("P1993_101", None, None)
        sample2 = Sample("P1993_102", None, None)
        gene_count1 = GeneCount(gene1, sample1, 0.001)
        gene_count2 = GeneCount(gene1, sample2, 0.01)
        gene_count3 = GeneCount(gene2, sample1, 0.002)
        gene_count4 = GeneCount(gene2, sample2, 0.02)
        self.session.add(gene1)
        self.session.add(gene2)
        self.session.add_all([gene_annotation1, gene_annotation2,
            gene_annotation3, gene_annotation4])
        self.session.commit()

        assert len(annotation1.rpkm.keys()) == 2
        assert annotation1.rpkm == { sample1: 0.003, sample2: 0.03 }
        assert annotation2.rpkm == { sample1: 0.001, sample2: 0.01 }
        assert annotation3.rpkm == { sample1: 0.002, sample2: 0.02 }

    def test_annotation_type_rpkm(self):
        # Test rpkm for the subclasses as well

        annotation_types = [("Cog", {'class': Cog}),
                ("Pfam", {'class': Pfam}),
                ("TigrFam", {'class': TigrFam}),
                ("EcNumber", {'class': EcNumber})]
        for annotation_type, type_d in annotation_types:
            if annotation_type == 'Cog':
                annotation1 = type_d['class'](annotation_type.upper() + "0001", "H")
                annotation2 = type_d['class'](annotation_type.upper() + "0002", "G")
                annotation3 = type_d['class'](annotation_type.upper() + "0003", "E")
            elif annotation_type == 'EcNumber':
                annotation1 = type_d['class']("0.0.0.1")
                annotation2 = type_d['class']("0.0.0.2")
                annotation3 = type_d['class']("0.0.0.3")
            else:
                annotation1 = type_d['class'](annotation_type.upper() + "0001")
                annotation2 = type_d['class'](annotation_type.upper() + "0002")
                annotation3 = type_d['class'](annotation_type.upper() + "0003")

            gene1 = Gene("gene1", None)
            gene2 = Gene("gene2", None)

            annotation_source = AnnotationSource(annotation_type, "v1.0", "rpsblast", "e_value=0.000001")
            gene_annotation1 = GeneAnnotation(annotation1, gene1, annotation_source)
            gene_annotation2 = GeneAnnotation(annotation1, gene2, annotation_source)
            gene_annotation3 = GeneAnnotation(annotation2, gene1, annotation_source)
            gene_annotation4 = GeneAnnotation(annotation3, gene2, annotation_source)

            sample1 = Sample("P1993_101", None, None)
            sample2 = Sample("P1993_102", None, None)
            gene_count1 = GeneCount(gene1, sample1, 0.001)
            gene_count2 = GeneCount(gene1, sample2, 0.01)
            gene_count3 = GeneCount(gene2, sample1, 0.002)
            gene_count4 = GeneCount(gene2, sample2, 0.02)
            self.session.add_all([gene_annotation1, gene_annotation2,
                gene_annotation3, gene_annotation4])
            self.session.add(gene1)
            self.session.add(gene2)
            self.session.commit()

            assert len(annotation1.rpkm.keys()) == 2
            assert annotation1.rpkm == { sample1: 0.003, sample2: 0.03 }
            assert annotation2.rpkm == { sample1: 0.001, sample2: 0.01 }
            assert annotation3.rpkm == { sample1: 0.002, sample2: 0.02 }

    def test_annotation_rpkm_table(self):
        annotation_types = [("Cog", {'class': Cog}),
                ("Pfam", {'class': Pfam}),
                ("TigrFam", {'class': TigrFam}),
                ("EcNumber", {'class': EcNumber})]

        nr_annotation_types = len(annotation_types)
        annotation_sources = {}
        for annotation_type, type_d in annotation_types:
            annotation_sources[annotation_type]= AnnotationSource(
                    annotation_type,
                    "v1.0",
                    "rpsblast",
                    "e_value=0.000001"
                )

        sample1 = Sample("P1993_101", None, None)
        sample2 = Sample("P1993_102", None, None)
        nr_samples = 2
        for i in range(50):
            gene1 = Gene("gene1{}".format(i), None)
            gene2 = Gene("gene2{}".format(i), None)

            gene_count1 = GeneCount(gene1, sample1, 0.001)
            gene_count2 = GeneCount(gene1, sample2, 0.01)
            gene_count3 = GeneCount(gene2, sample1, 0.002)
            gene_count4 = GeneCount(gene2, sample2, 0.02)

            for annotation_type, type_d in annotation_types:
                if annotation_type == 'Cog':
                    type_id = str(i)
                    type_id = "0"*(4-len(type_id))+type_id
                    annotation = type_d['class'](annotation_type.upper() + type_id, "H")
                elif annotation_type == 'EcNumber':
                    if i > 25:
                        type_id = "0.0.2.{}".format(i)
                    else:
                        type_id = "0.0.0.{}".format(i)
                    annotation = type_d['class'](type_id)
                else:
                    type_id = str(i)
                    type_id = "0"*(4-len(type_id))+type_id
                    annotation = type_d['class'](annotation_type.upper() + type_id)

                annotation_mode = i % 3
                gene_annotations = []
                if annotation_mode in [0,1]:
                    gene_annotations.append(GeneAnnotation(
                            annotation,
                            gene1,
                            annotation_sources[annotation_type]
                        ))
                if annotation_mode in [1,2]:
                    gene_annotations.append(GeneAnnotation(
                            annotation,
                            gene2,
                            annotation_sources[annotation_type]
                        ))
                self.session.add_all(gene_annotations)

            self.session.add(gene1)
            self.session.add(gene2)
        self.session.commit()
        refresh_all_mat_views()
        samples, rows = Annotation.rpkm_table()
        assert len(samples) == 2
        assert len(rows) == 20 # Default limit
        samples, rows = Annotation.rpkm_table(limit=100)
        assert len(samples) == 2
        assert len(rows) == 100
        samples, rows = Annotation.rpkm_table(limit=None)
        assert len(samples) == 2
        assert len(rows) == nr_annotation_types * 50

        for annotation, sample_d in rows.items():
            # sample_d should be a ordered dict
            assert ["P1993_101", "P1993_102"] == [sample.scilifelab_code for sample in sample_d.keys()]
        rpkms = [[rpkm for sample, rpkm in sample_d.items()] for annotation, sample_d in rows.items()]

        rpkms_flat = []
        for rpkm_row in rpkms:
            rpkms_flat += rpkm_row

        assert len(rpkms_flat) == nr_annotation_types * nr_samples * 50

        # Annotations sorted by total rpkm over all samples
        # and the rpkm values should be summed over all genes for that annotation
        # there should be roughly equal numbers of the three different counts
        for i, row in enumerate(rpkms[:67]):
            assert row == [0.003, 0.03]
        for row in rpkms[69:130]:
            assert row == [0.002, 0.02]
        for row in rpkms[150:200]:
            assert row == [0.001, 0.01]

        # possible to filter on function classes
        for annotation_type, type_d in annotation_types:
            samples, rows = Annotation.rpkm_table(limit=None, function_class=annotation_type.lower())
            assert len(rows) == 50
            for key in rows.keys():
                assert annotation_type[:3].lower() == key.annotation_type[:3]

        # possible to filter on samples
        for sample in [sample1, sample2]:
            samples, rows = Annotation.rpkm_table(samples=[sample.scilifelab_code], limit=None)
            assert len(rows) == 200
            assert len(samples) == 1
            assert samples[0] == sample
            for annotation, sample_d in rows.items():
                assert list(sample_d.keys()) == [sample]

            rpkms = [[rpkm for sample, rpkm in sample_d.items()] for annotation, sample_d in rows.items()]
            if sample.scilifelab_code == "P1993_101":
                for i, row in enumerate(rpkms[:65]):
                    assert row == [0.003]
                for row in rpkms[69:130]:
                    assert row == [0.002]
                for row in rpkms[150:200]:
                    assert row == [0.001]
            else:
                for row in rpkms[:67]:
                    assert row == [0.03]
                for row in rpkms[69:130]:
                    assert row == [0.02]
                for row in rpkms[150:200]:
                    assert row == [0.01]

        # possible to filter on sample and function class at the same time
        for annotation_type, type_d in annotation_types:
            for sample in [sample1, sample2]:
                samples, rows = Annotation.rpkm_table(limit=None, function_class=annotation_type.lower(), samples=[sample.scilifelab_code])
                assert len(rows) == 50
                for key in rows.keys():
                    assert annotation_type.lower()[:3] == key.annotation_type[:3]

                assert len(samples) == 1
                assert samples[0] == sample
                for annotation, sample_d in rows.items():
                    assert list(sample_d.keys()) == [sample]

                rpkms = [[rpkm for sample, rpkm in sample_d.items()] for annotation, sample_d in rows.items()]
                if sample.scilifelab_code == "P1993_101":
                    for row in rpkms[:9]:
                        assert row == [0.003]
                    for row in rpkms[19:29]:
                        assert row == [0.002]
                    for row in rpkms[39:]:
                        assert row == [0.001]
                else:
                    for row in rpkms[:9]:
                        assert row == [0.03]
                    for row in rpkms[19:29]:
                        assert row == [0.02]
                    for row in rpkms[39:]:
                        assert row == [0.01]

        # possible to filter on individual annotations
        annotation_ids = ["COG0001", "TIGRFAM0004", "COG0003", "PFAM0002", "0.0.2.26"]

        for r in range(5):
            for type_identifiers in itertools.combinations(annotation_ids, r+1):

                samples, rows = Annotation.rpkm_table(limit=None, type_identifiers=list(type_identifiers))
                assert len(samples) == 2
                assert len(rows) == len(type_identifiers)
                assert set([key.type_identifier for key in rows.keys()]) == set(type_identifiers)
