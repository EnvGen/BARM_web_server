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

    logging.info("Reading sample information")
    # Add all samples from the sample info file
    sample_info = pd.read_table(args.sample_info, sep=',', index_col=0)

    for sample_set_name, sample_set_df in sample_info.groupby('sample_set'):
        assert len(SampleSet.query.filter_by(name=sample_set_name).all()) == 0

    for sample_id, row in sample_info.iterrows():
        samples_with_code = Sample.query.filter_by(scilifelab_code=sample_id).all()
        assert len(samples_with_code) == 0

    logging.info("Creating sample sets")
    # sample_set
    sample_sets = {}
    for sample_set_name, sample_set_df in sample_info.groupby('sample_set'):
        if len(SampleSet.query.filter_by(name=sample_set_name).all()) == 0:
            sample_set = SampleSet(sample_set_name)
        for sample_id, row in sample_set_df.iterrows():
            sample_sets[sample_id] = sample_set

    logging.info("Creating individual samples")
    sample_properties = []
    all_samples = {}
    time_places = []
    metadata_reference = pd.read_table(args.metadata_reference, index_col=0)
    meta_categories = list(metadata_reference.index)
    default_units = metadata_reference['Unit'].to_dict()
    default_units['filter_lower'] = 'µm'
    default_units['filter_upper'] = 'µm'
    for sample_id, row in sample_info.iterrows():
        samples_with_code = Sample.query.filter_by(scilifelab_code=sample_id).all()
        assert len(samples_with_code) == 0

        meta_data = {}

        for meta_category in meta_categories:
            if meta_category == 'Collection date':
                date = datetime.datetime.strptime(row[meta_category], '%y/%m/%d')
            if meta_category == 'Collection time':
                time = datetime.datetime.strptime(str(row[meta_category]), '%H:%M').time()
            else:
                meta_data[meta_category] = row[meta_category]

        extra_categories = ['filter_lower', 'filter_upper']
        for meta_category in extra_categories:
            meta_data[meta_category] = row[meta_category]

        time_place = TimePlace(datetime.datetime.combine(date, time), meta_data['Latitude'], meta_data['Longitude'])
        time_places.append(time_place)

        all_samples[sample_id] = Sample(sample_id, sample_sets[sample_id], time_place)

        for meta_category in meta_categories:
            if meta_category in ['Latitude', 'Longitude', 'Collection date', 'Collection time']:
                continue
            if meta_data[meta_category] is not None:
                sample_properties.append(SampleProperty(meta_category, meta_data[meta_category], default_units[meta_category], all_samples[sample_id]))

    session.add_all(list(sample_sets.values()) + list(all_samples.values()) + time_places + sample_properties)

    logging.info("Commiting everything except gene counts")
    session.commit()

    commited_genes = dict( session.query(Gene.name, Gene.id).all() )

    # Fetch each gene from the gene count file and create the corresponding gene count
    logging.info("Starting with gene counts")
    gene_counts = pd.read_table(args.gene_counts, index_col=0)
    total_gene_count_len = len(gene_counts)
    val_cols = gene_counts.columns
    nr_columns = len(val_cols)

    filtered_gene_counts = gene_counts[ gene_counts.index.isin(commited_genes.keys()) ].copy()
    filtered_gene_counts['gene_name'] = filtered_gene_counts.index
    filtered_gene_counts['gene_id'] = filtered_gene_counts['gene_name'].apply(lambda x: commited_genes[x])

    all_sample_ids = dict((sample_name, sample.id) for sample_name, sample in all_samples.items())
    filtered_gene_counts.rename(columns=all_sample_ids, inplace=True)

    sample_id_cols = filtered_gene_counts.columns.tolist()
    sample_id_cols.remove('gene_id')
    sample_id_cols.remove('gene_name')
    sample_id_cols.remove('gene_length')

    filtered_gene_counts.index = filtered_gene_counts['gene_id']
    filtered_gene_counts = pd.DataFrame(filtered_gene_counts[sample_id_cols].stack())
    filtered_gene_counts.reset_index(inplace=True)
    filtered_gene_counts.columns = ['gene_id', 'sample_id', 'rpkm']

    tot_nr_samples = len(all_samples.values())
    logging.info("Start adding gene counts")

    for i, sample_t in enumerate(filtered_gene_counts.groupby('sample_id')):
        sample, sample_df = sample_t
        with open(args.tmp_file, 'w') as gene_counts_file:
            sample_df.to_csv(gene_counts_file, index=False, header=False)

        logging.info("Adding gene counts from file. Sample {}/{}".format(i+1, tot_nr_samples))
        session.execute("COPY gene_count (gene_id, sample_id, rpkm) FROM '{}' WITH CSV;".format(args.tmp_file))

    logging.info("{} out of {} are annotated genes".format(len(filtered_gene_counts), total_gene_count_len))
    session.commit()

    logging.info("Refreshing materialized view")
    refresh_all_mat_views()
    session.commit()
    logging.info("Finished!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_info", help="A csv file with all the sample information.")
    parser.add_argument("--gene_counts", help="A tsv file with each sample as a column containing all the gene counts")
    parser.add_argument("--metadata_reference", help="A tsv file with which metadata parameters that are supposed to be added")
    parser.add_argument("--tmp_file", help="A file that will be used to import gene counts to postgres")
    args = parser.parse_args()

    main(args)
