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

def main(args):
    # connect to database
    session = app.db.session()

    # Fetch each gene from the gene count file and create the corresponding gene count
    logging.info("Starting with gene counts")
    gene_counts = pd.read_table(args.gene_counts, index_col=0)
    total_gene_count_len = len(gene_counts)
    val_cols = gene_counts.columns
    nr_columns = len(val_cols)

    commited_genes = {}
    commited_genes.update(dict( session.query(Gene.name, Gene.id).all() ))

    filtered_gene_counts = gene_counts
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
    parser.add_argument("--gene_counts", help="The gene counts, probably for all samples and sample sets")
    parser.add_argument("--tmp_file", help="A file that will be used to import gene counts to postgres")
    args = parser.parse_args()

    main(args)
