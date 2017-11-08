import app
from models import *
import pandas as pd
import argparse
import os
import sys
import logging
import datetime

from materialized_view_factory import refresh_all_mat_views

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

def check_existing_annotation(annotation_class):
    return bool(annotation_class.query.first())

def main(args):
    # connect to database
    session = app.db.session()

    logging.info("Adding annotation information")

    # find the reference assembly
    ref_assemblies = ReferenceAssembly.query.filter_by(name=str(args.reference_assembly)).all()
    assert len(ref_assemblies) == 1
    ref_assembly = ref_assemblies[0]

    annotations = []
    if args.tigrfam_annotation_info:
        # Columns:Id,Name,Description
        annotation_info = pd.read_table(args.tigrfam_annotation_info, index_col=0)

        for ix, row in annotation_info.iterrows():
            new_object = TigrFam(type_identifier=str(ix), description= row['Description'])
            annotations.append(new_object)

        logging.info("Commiting all TigrFam annotation info")
        session.add_all(annotations)
        session.commit()

    all_annotations = dict( (annotation.type_identifier, annotation) for annotation in session.query(Annotation).all() )

    logging.info("Adding annotation source")
    # Create annotation source
    annotation_source_info = pd.read_table(args.annotation_source_info, sep=',', header=None, names=["annotation_type", "db_version", "algorithm", "algorithm_parameters"], index_col = 0)
    all_annotation_sources = {}
    row = annotation_source_info.loc['TigrFam']
    annotation_source = AnnotationSource('TigrFam', row.db_version, row.algorithm, row.algorithm_parameters)

    session.add(annotation_source)

    def add_genes_with_annotation(annotation_type, gene_annotation_arg, commited_genes, all_annotations, annotation_source):
        logging.info("Adding genes with {} annotations".format(annotation_type))
        gene_annotations = pd.read_table(gene_annotation_arg, header=None, names=["name", "type_identifier", "e_value", "score"])

        # Only add genes once
        new_genes = gene_annotations[ ~ gene_annotations['name'].isin(commited_genes.keys()) ]

        new_genes_uniq = pd.DataFrame([new_genes['name'].unique()])
        new_genes_uniq = new_genes_uniq.transpose()
        new_genes_uniq.columns = ['name']
        new_genes_uniq["reference_assembly_id"] = ref_assembly.id

        logging.info("Commiting all {} new {} genes.".format(len(new_genes_uniq), annotation_type))

        with open(args.tmp_file, 'w') as gene_file:
            new_genes_uniq[['name', 'reference_assembly_id']].to_csv(gene_file, index=False, header=None)
        session.execute("COPY gene (name, reference_assembly_id) FROM '{}' WITH CSV;".format(args.tmp_file))

        commited_genes.update(dict( session.query(Gene.name, Gene.id).all() ))
        logging.info("{} genes present in database".format(len(commited_genes.keys())))

        gene_annotations['gene_id'] = gene_annotations['name'].apply(lambda x: commited_genes[x])
        gene_annotations['annotation_id'] = gene_annotations['type_identifier'].apply(lambda x: all_annotations[x].id)

        gene_annotations['annotation_source_id'] = annotation_source.id

        logging.info("Commiting all {} {} gene annotations".format(len(gene_annotations), annotation_type))
        with open(args.tmp_file, 'w') as gene_file:
            gene_annotations[['gene_id', 'annotation_id', 'annotation_source_id', 'e_value']].to_csv(gene_file, index=False, header=None)
        session.execute("COPY gene_annotation (gene_id, annotation_id, annotation_source_id, e_value) FROM '{}' WITH CSV;".format(args.tmp_file))
        session.commit()
        return commited_genes, new_genes_uniq

    commited_genes = dict( session.query(Gene.name, Gene.id).all() )
    commited_genes, new_genes_uniq = add_genes_with_annotation("TigrFam", args.gene_annotations_tigrfam, commited_genes, all_annotations, annotation_source)
    logging.info("Processed {} genes in total, moving on to gene counts".format(len(commited_genes.keys())))

    # Fetch each gene from the gene count file and create the corresponding gene count
    logging.info("Starting with gene counts")
    gene_counts = pd.read_table(args.gene_counts, index_col=0)
    total_gene_count_len = len(gene_counts)
    val_cols = gene_counts.columns
    nr_columns = len(val_cols)

    filtered_gene_counts = gene_counts[ gene_counts.index.isin(new_genes_uniq.name) ].copy()
    filtered_gene_counts['gene_name'] = filtered_gene_counts.index
    filtered_gene_counts['gene_id'] = filtered_gene_counts['gene_name'].apply(lambda x: commited_genes[x])
    
    all_samples = {}
    for sample in session.query(Sample).all():
        all_samples[sample.scilifelab_code] = sample

    all_sample_ids = dict((sample_name, sample.id) for sample_name, sample in all_samples.items())
    filtered_gene_counts.rename(columns=all_sample_ids, inplace=True)

    sample_id_cols = filtered_gene_counts.columns.tolist()
    sample_id_cols.remove('gene_id')
    sample_id_cols.remove('gene_name')
    sample_id_cols.remove('gene_length')
    tot_nr_samples = len(sample_id_cols)

    filtered_gene_counts.index = filtered_gene_counts['gene_id']
    filtered_gene_counts = pd.DataFrame(filtered_gene_counts[sample_id_cols].stack())
    filtered_gene_counts.reset_index(inplace=True)
    filtered_gene_counts.columns = ['gene_id', 'sample_id', 'rpkm']

    logging.info("Start adding gene counts")

    for i, sample_t in enumerate(filtered_gene_counts.groupby('sample_id')):
        sample, sample_df = sample_t
        with open(args.tmp_file, 'w') as gene_counts_file:
            sample_df.to_csv(gene_counts_file, index=False, header=None)

        logging.info("Adding gene counts from file. Sample {} ({}/{})".format(sample, i+1, tot_nr_samples))
        session.execute("COPY gene_count (gene_id, sample_id, rpkm) FROM '{}' WITH CSV;".format(args.tmp_file))

    logging.info("{} out of {} are annotated genes".format(len(filtered_gene_counts), total_gene_count_len))
    session.commit()
    logging.info("Commiting everything")
    session.commit()
    logging.info("Refreshing materialized view")
    refresh_all_mat_views()
    session.commit()
    logging.info("Finished!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotation_source_info", help="A csv file with all the annotation source info.")
    parser.add_argument("--tigrfam_annotation_info", help=("A tsv file with all the possible tigrfam annotations."))
    parser.add_argument("--gene_annotations_tigrfam", help="A tsv file with all the tigrfam gene annotations")
    parser.add_argument("--reference_assembly", help="Name of the reference assembly that the genes belong to")
    parser.add_argument("--gene_counts", help="The gene counts, probably for all samples and sample sets")
    parser.add_argument("--tmp_file", help="A file that will be used to import gene counts to postgres")
    args = parser.parse_args()

    main(args)
