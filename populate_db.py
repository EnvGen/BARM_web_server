import app
from models import *
import pandas as pd
import argparse
import os

def main(args):
    # connect to database
    session = app.db.session()
    with session.no_autoflush:

        print("Reading sample information")
        # Add all samples from the sample info file
        sample_info = pd.read_table(args.sample_info, sep=',', index_col=0)

        print("Creating sample sets")
        # sample_set
        sample_sets = {}
        for sample_set_name, sample_set_df in sample_info.groupby('sample_set'):
            if len(SampleSet.query.filter_by(name=sample_set_name).all()) == 0:
                sample_set = SampleSet(sample_set_name)
            for sample_id, row in sample_set_df.iterrows():
                sample_sets[sample_id] = sample_set

        print("Creating individual samples")
        all_samples = {}
        for sample_id, row in sample_info.iterrows():
            samples_with_code = Sample.query.filter_by(scilifelab_code=sample_id).all()
            assert len(samples_with_code) == 0
            all_samples[sample_id] = Sample(sample_id, sample_sets[sample_id], None)

        session.add_all(list(sample_sets.values()) + list(all_samples.values()))

        print("Creating the reference assembly")
        # create the reference assembly
        ref_assemblies = ReferenceAssembly.query.filter_by(name=args.reference_assembly).all()
        if len(ref_assemblies) == 0:
            ref_assembly = ReferenceAssembly(args.reference_assembly)
        else:
            assert len(ref_assemblies) == 1
            ref_assembly = ref_assemlbies[0]

        session.add(ref_assembly)

        print("Adding annotation information")
        # Make sure annotations are present
        annotation_info = pd.read_table(args.all_annotations, index_col=0, header=None, names=["gene_id", "gene_name", "description"])
        annotation_models = {'COG': Cog, 'TIG': TigrFam, 'pfa': Pfam}

        all_annotations = {}
        for annotation_id, row in annotation_info.iterrows():
            annotation_in_db = Annotation.query.filter_by(type_identifier=annotation_id).first()
            assert annotation_in_db is None
            annotation_type = annotation_id[0:3]
            if annotation_type == 'COG':
                all_annotations[annotation_id] = annotation_models[annotation_type](annotation_id, None, description=row.description)
            else:
                all_annotations[annotation_id] = annotation_models[annotation_type](annotation_id, description=row.description)

        session.add_all(list(all_annotations.values()))

        print("Adding annotation source")
        # Create annotation source
        annotation_source_info = pd.read_table(args.annotation_source_info, sep=',', header=None, names=["annotation_type", "db_version", "algorithm", "algorithm_parameters"], index_col = 0)
        all_annotation_sources = {}
        for annotation_type, row in annotation_source_info.iterrows():
            all_annotation_sources[annotation_type] = AnnotationSource(annotation_type, row.db_version, row.algorithm, row.algorithm_parameters)

        session.add_all(list(all_annotation_sources.values()))
        all_genes = {}
        all_gene_annotations = []


        annotation_type_translation = {'COG': 'Cog', 'TIG': 'TigrFam', 'pfa': 'Pfam'}
        print("Adding genes with cog annotations")
        # For each gene present in the annotation file, create gene and annotation
        cog_gene_annotations = pd.read_table(args.gene_annotations_cog, index_col=0, header=None, names=["gene_id", "annotation_id"])
        for gene_id, row in cog_gene_annotations.iterrows():
            annotation = all_annotations[row.annotation_id]
            assert annotation is not None
            if gene_id not in all_genes:
                all_genes[gene_id] = Gene(gene_id, ref_assembly)
            annotation_type = annotation_type_translation[row.annotation_id[0:3]]
            annotation_source = all_annotation_sources[annotation_type]
            all_gene_annotations.append(GeneAnnotation(annotation, all_genes[gene_id], annotation_source))

        print("Adding genes with pfam annotations")
        # For each gene present in the annotation file, create gene and annotation
        pfam_gene_annotations = pd.read_table(args.gene_annotations_pfam, index_col=0, header=None, names=["gene_id", "annotation_id"])
        for gene_id, row in pfam_gene_annotations.iterrows():
            annotation = all_annotations[row.annotation_id]
            assert annotation is not None
            if gene_id not in all_genes:
                all_genes[gene_id] = Gene(gene_id, ref_assembly)
            annotation_type = annotation_type_translation[row.annotation_id[0:3]]
            annotation_source = all_annotation_sources[annotation_type]
            all_gene_annotations.append(GeneAnnotation(annotation, all_genes[gene_id], annotation_source))


        print("Adding genes with tigrfam annotations")
        # For each gene present in the annotation file, create gene and annotation
        tigrfam_gene_annotations = pd.read_table(args.gene_annotations_tigrfam, index_col=0, header=None, names=["gene_id", "annotation_id"])
        for gene_id, row in tigrfam_gene_annotations.iterrows():
            annotation = all_annotations[row.annotation_id]
            assert annotation is not None
            if gene_id not in all_genes:
                all_genes[gene_id] = Gene(gene_id, ref_assembly)
            annotation_type = annotation_type_translation[row.annotation_id[0:3]]
            annotation_source = all_annotation_sources[annotation_type]
            all_gene_annotations.append(GeneAnnotation(annotation, all_genes[gene_id], annotation_source))

        session.add_all(all_gene_annotations)

        # Fetch each gene from the gene count file and create the corresponding gene count
        print("Adding gene counts")
        all_gene_counts = []
        for fn in args.gene_counts:
            cov_df = pd.read_table(fn, index_col=0)
            nr_unannotated = 0
            sample_id = ".".join(os.path.basename(fn).split('.')[0:-1])
            sample = all_samples[sample_id]
            for gene_id, row in cov_df.iterrows():
                # Only annotated genes are added
                if gene_id in all_genes:
                    gene = all_genes[gene_id]
                    all_gene_counts.append(GeneCount(gene, sample, row.avg_coverage))
                else:
                    nr_unannotated += 1
            print("Number of unannotated genes for sample {} is {}".format(sample_id, nr_unannotated))
        session.add_all(all_gene_counts)

    session.commit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_info", help="A csv file with all the sample information.")
    parser.add_argument("--all_annotations", help=("A tsv file with all the possible annotations."
            "The three columns should be ['type_id', 'gene_id', 'description']"))
    parser.add_argument("--annotation_source_info", help="A csv file with all the annotation source info.")
    parser.add_argument("--gene_annotations_cog", help="A tsv file with all the gene annotations")
    parser.add_argument("--gene_annotations_pfam", help="A tsv file with all the pfam gene annotations")
    parser.add_argument("--gene_annotations_tigrfam", help="A tsv file with all the tigrfam gene annotations")
    parser.add_argument("--reference_assembly", help="Name of the reference assembly that the genes belong to")
    parser.add_argument("--gene_counts", nargs='*', help="One tsv file for each sample with all the gene counts")
    args = parser.parse_args()
    main(args)
