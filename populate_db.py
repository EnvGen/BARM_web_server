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
    # Create materialized view that is not created by manage.py
    app.db.create_all()

    # connect to database
    session = app.db.session()

    logging.info("Reading sample information")
    # Add all samples from the sample info file
    sample_info = pd.read_table(args.sample_info, sep=',', index_col=0)

    logging.info("Creating sample sets")
    # sample_set
    sample_sets = {}
    for sample_set_name, sample_set_df in sample_info.groupby('sample_set'):
        if len(SampleSet.query.filter_by(name=sample_set_name).all()) == 0:
            assert len(sample_set_df.public.unique() == 1)
            public = sample_set_df.public.unique()[0]
            sample_set = SampleSet(sample_set_name, public=public)
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
        samples_with_code = Sample.query.filter_by(scilifelab_code=str(sample_id)).all()
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

        all_samples[str(sample_id)] = Sample(str(sample_id), sample_sets[sample_id], time_place)

        for meta_category in meta_categories:
            if meta_category in ['Latitude', 'Longitude', 'Collection date', 'Collection time']:
                continue
            if meta_data[meta_category] is not None:
                sample_properties.append(SampleProperty(meta_category, meta_data[meta_category], default_units[meta_category], all_samples[str(sample_id)]))

    session.add_all(list(sample_sets.values()) + list(all_samples.values()) + time_places + sample_properties)

    logging.info("Creating the reference assembly")
    # create the reference assembly
    ref_assemblies = ReferenceAssembly.query.filter_by(name=str(args.reference_assembly)).all()
    if len(ref_assemblies) == 0:
        ref_assembly = ReferenceAssembly(args.reference_assembly)
    else:
        assert len(ref_assemblies) == 1
        ref_assembly = ref_assemblies[0]

    session.add(ref_assembly)

    logging.info("Adding annotation information")

    all_annotations = {}
    annotations = []
    if args.pfam_annotation_info:
        # Columns:Id,Name,Description
        annotation_info = pd.read_table(args.pfam_annotation_info, index_col=0)

        for ix, row in annotation_info.iterrows():
            new_object = Pfam(type_identifier=ix, description=row['Description'])
            annotations.append(new_object)

        logging.info("Commiting all PFAM annotation info")
        session.add_all(annotations)
        session.commit()

    categories = []
    if args.eggnog_category_info:
        categories_df = pd.read_table(args.eggnog_category_info, names=['category', 'description'])
        for ix, row in categories_df.iterrows():
            new_object = EggNOGCategory(row['category'], row['description'])
            categories.append(new_object)
        logging.info("Committing all EggNOG category info")
        session.add_all(categories)
        session.commit()

    eggnog_categories = dict( (category.category, category) for category in session.query(EggNOGCategory).all() )

    annotations = []
    if args.eggnog_annotation_info:
        # Id,Categories,Description
        annotation_info = pd.read_table(args.eggnog_annotation_info, index_col=0)

        for ix, row in annotation_info.iterrows():
            categories = [eggnog_categories[category] for category in row['Categories']]
            new_object = EggNOG(type_identifier=str(ix), categories=categories, description=row['Description'])
            annotations.append(new_object)

        logging.info("Commiting all EggNOG annotation info")
        session.add_all(annotations)
        session.commit()

    def parse_ec_numbers(ecnumber):
        assert len(ecnumber.split(".")) == 4
        return_list = []
        for number in ecnumber.split("."):
            if number == '-':
                return_list.append(None)
            else:
                return_list.append(number)
        return tuple(return_list)

    annotations = []
    if args.ec_annotation_info:
        # Columns:Id,Name,Description
        annotation_info = pd.read_table(args.ec_annotation_info, index_col=0)

        for ix, row in annotation_info.iterrows():
            first, second, third, fourth = parse_ec_numbers(ix)
            description = row.Description
            new_object = EcNumber(type_identifier=str(ix), first_digit=first, second_digit=second, third_digit=third, fourth_digit=fourth, description=description)
            annotations.append(new_object)

        logging.info("Commiting all EC annotation info")
        session.add_all(annotations)
        session.commit()

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
    for annotation_type, row in annotation_source_info.iterrows():
        all_annotation_sources[annotation_type] = AnnotationSource(annotation_type, row.db_version, row.algorithm, row.algorithm_parameters)

    session.add_all(list(all_annotation_sources.values()))


    logging.info("Commiting everything except genes and gene counts")
    session.commit()

    def add_genes_with_taxonomy(taxonomy_per_gene, commited_genes):
        gene_annotations = pd.read_table(taxonomy_per_gene, index_col=0)

        gene_annotations['taxclass'] = gene_annotations['class']

        taxonomy_columns = ["superkingdom", "phylum", "taxclass", "order", "family", "genus", "species"]

        # Only add genes with taxonomy given
        annotated_genes = gene_annotations[ ~ gene_annotations[taxonomy_columns].isnull().all(axis=1)]


        def add_taxa(full_taxonomy, taxonomy_columns):

            # We want to make a difference between unnamed phyla and unset phyla
            first = True
            rev_new_taxonomy = []
            for tax_val in reversed(full_taxonomy.split(';')):
                if tax_val == "":
                    if first:
                        tax_val = None
                    else:
                        tax_val = "Unnamed"
                else:
                    first = False
                rev_new_taxonomy.append(tax_val)

            new_taxa_d = dict(zip(taxonomy_columns, reversed(rev_new_taxonomy)))
            new_taxa = Taxon(**new_taxa_d)

            return new_taxa

        added_taxa = {}
        gene_to_taxa = {}
        annotated_genes = annotated_genes.fillna("")
        # The number of taxa is lower than the genes with taxonomic annotation
        annotated_genes['full_taxonomy'] = annotated_genes["superkingdom"] + ';' + \
                annotated_genes['phylum'] + ';' + \
                annotated_genes['taxclass'] + ';' +\
                annotated_genes['order'] + ';' +\
                annotated_genes['family'] + ';' +\
                annotated_genes['genus'] + ';' +\
                annotated_genes['species'] + ';'

        all_taxas = annotated_genes['full_taxonomy'].unique()
        all_taxas_to_be_created = {}
        first_full_taxa_to_real_full_taxa = {}
        for full_taxonomy in all_taxas:
            taxa = add_taxa(full_taxonomy, taxonomy_columns)
            first_full_taxa_to_real_full_taxa[full_taxonomy] = taxa.full_taxonomy
            all_taxas_to_be_created[taxa.full_taxonomy] = taxa

        annotated_genes['real_full_taxonomy'] = annotated_genes['full_taxonomy'].apply(lambda x: first_full_taxa_to_real_full_taxa[x])

        logging.info("Commiting all taxa")
        session.add_all(all_taxas_to_be_created.values())
        session.commit()

        logging.info("Creating genes with taxon information")

        all_created_taxa = dict(session.query(Taxon.full_taxonomy, Taxon.id).all() )

        annotated_genes['taxon_id'] = annotated_genes['real_full_taxonomy'].apply(lambda x: all_created_taxa[x])
        annotated_genes['name'] = annotated_genes.index
        annotated_genes["reference_assembly_id"] = ref_assembly.id

        with open(args.tmp_file, 'w') as gene_file:
            annotated_genes[['name', 'reference_assembly_id', 'taxon_id']].to_csv(gene_file, index=False, header=None)
        session.execute("COPY gene (name, reference_assembly_id, taxon_id) FROM '{}' WITH CSV;".format(args.tmp_file))
        commited_genes.update(dict( session.query(Gene.name, Gene.id).all() ))
        logging.info("{} genes present in database".format(len(commited_genes.keys())))

        return commited_genes


    commited_genes = {}
    commited_genes = add_genes_with_taxonomy(args.taxonomy_per_gene, commited_genes)

    logging.info("Processed {} genes for gene taxonomy, moving on to functional annotation".format(len(commited_genes.keys())))

    def add_genes_with_annotation(annotation_type, gene_annotation_arg, commited_genes, all_annotations, annotation_source):
        logging.info("Adding genes with {} annotations".format(annotation_type))
        gene_annotations = pd.read_table(gene_annotation_arg, header=None, names=["name", "type_identifier", "e_value", "score"])

        # Only add genes once
        new_genes = gene_annotations[ ~ gene_annotations['name'].isin(commited_genes.keys()) ]

        new_genes_uniq = pd.DataFrame([new_genes['name'].unique()])
        new_genes_uniq = new_genes_uniq.transpose()
        new_genes_uniq.columns = ['name']
        new_genes_uniq["reference_assembly_id"] = ref_assembly.id

        logging.info("Commiting all {} genes.".format(annotation_type))

        with open(args.tmp_file, 'w') as gene_file:
            new_genes_uniq[['name', 'reference_assembly_id']].to_csv(gene_file, index=False, header=None)
        session.execute("COPY gene (name, reference_assembly_id) FROM '{}' WITH CSV;".format(args.tmp_file))

        commited_genes.update(dict( session.query(Gene.name, Gene.id).all() ))
        logging.info("{} genes present in database".format(len(commited_genes.keys())))

        gene_annotations['gene_id'] = gene_annotations['name'].apply(lambda x: commited_genes[x])
        gene_annotations['annotation_id'] = gene_annotations['type_identifier'].apply(lambda x: all_annotations[x].id)

        annotation_source = all_annotation_sources[annotation_type]
        gene_annotations['annotation_source_id'] = annotation_source.id

        logging.info("Commiting all {} gene anntations".format(annotation_type))
        with open(args.tmp_file, 'w') as gene_file:
            gene_annotations[['gene_id', 'annotation_id', 'annotation_source_id', 'e_value']].to_csv(gene_file, index=False, header=None)
        session.execute("COPY gene_annotation (gene_id, annotation_id, annotation_source_id, e_value) FROM '{}' WITH CSV;".format(args.tmp_file))
        session.commit()
        return commited_genes

    if args.gene_annotations_cog:
        commited_genes = add_genes_with_annotation("Cog", args.gene_annotations_cog, commited_genes, all_annotations, all_annotation_sources["Cog"])
    if args.gene_annotations_pfam:
        commited_genes = add_genes_with_annotation("Pfam", args.gene_annotations_pfam, commited_genes, all_annotations, all_annotation_sources["Pfam"])
    if args.gene_annotations_tigrfam:
        commited_genes = add_genes_with_annotation("TigrFam", args.gene_annotations_tigrfam, commited_genes, all_annotations, all_annotation_sources["TigrFam"])
    if args.gene_annotations_eggnog:
        commited_genes = add_genes_with_annotation("EggNOG", args.gene_annotations_eggnog, commited_genes, all_annotations, all_annotation_sources["EggNOG"])
    if args.gene_annotations_ec:
        commited_genes = add_genes_with_annotation("EC", args.gene_annotations_ec, commited_genes, all_annotations, all_annotation_sources["EC"])

    logging.info("Processed {} genes in total, moving on to gene counts".format(len(commited_genes.keys())))

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

    logging.info("Refreshing materialized view")
    refresh_all_mat_views()
    session.commit()
    logging.info("Finished!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_info", help="A csv file with all the sample information.")
    parser.add_argument("--ec_annotation_info", help=("A tsv file with all the possible EC annotations."))
    parser.add_argument("--eggnog_annotation_info", help=("A tsv file with all the possible EggNOG annotations."))
    parser.add_argument("--eggnog_category_info", help=("A tsv file with all the possible eggnog categories."))
    parser.add_argument("--pfam_annotation_info", help=("A tsv file with all the possible pfam annotations."))
    parser.add_argument("--tigrfam_annotation_info", help=("A tsv file with all the possible tigrfam annotations."))
    parser.add_argument("--annotation_source_info", help="A csv file with all the annotation source info.")
    parser.add_argument("--gene_annotations_cog", help="A tsv file with all the gene annotations")
    parser.add_argument("--gene_annotations_pfam", help="A tsv file with all the pfam gene annotations")
    parser.add_argument("--gene_annotations_tigrfam", help="A tsv file with all the tigrfam gene annotations")
    parser.add_argument("--gene_annotations_ec", help="A tsv file with all the ec gene annotations")
    parser.add_argument("--gene_annotations_eggnog", help="A tsv file with all the eggnog gene annotations")
    parser.add_argument("--reference_assembly", help="Name of the reference assembly that the genes belong to")
    parser.add_argument("--gene_counts", help="A tsv file with each sample as a column containing all the gene counts")
    parser.add_argument("--taxonomy_per_gene", help="A tsv file with taxonomic annotation per gene")
    parser.add_argument("--metadata_reference", help="A tsv file with which metadata parameters that are supposed to be added")
    parser.add_argument("--tmp_file", help="A file that will be used to import gene counts to postgres")
    args = parser.parse_args()

    main(args)
