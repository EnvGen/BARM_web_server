time python populate_db.py --sample_info data/test/lmo/sample_info.csv \
    --pfam_annotation_info data/test/annotation_info/all_pfam_annotation_info.tsv \
    --eggnog_category_info data/test/annotation_info/eggnog_categories.tsv \
    --eggnog_annotation_info data/test/annotation_info/all_EggNOG_annotation_info.tsv \
    --ec_annotation_info data/test/annotation_info/all_EC_annotation_info.tsv \
    --tigrfam_annotation_info data/test/annotation_info/all_TIGRFAM_annotation_info.tsv \
    --annotation_source_info data/test/annotation_source_info.csv \
    --gene_annotations_pfam data/test/annotations/all.pfam.standardized.tsv \
    --gene_annotations_eggnog data/test/annotations/all.EggNOG.standardized.tsv \
    --gene_annotations_ec data/test/annotations/all.EC.standardized.tsv \
    --gene_annotations_tigrfam data/test/annotations/all.TIGRFAM.standardized.tsv \
    --reference_assembly "megahit_coassembly.0" \
    --gene_counts data/test/lmo/all_genes.tpm.tsv.gz \
    --metadata_reference data/test/metadata_reference.tsv \
    --tmp_file /Users/johannesalneberg/repos/BARM_web_server/data/test/tmp_file.csv \
    --taxonomy_per_gene ~/repos/BARM_web_server/data/test/lca_megan.tsv

time python add_sample_set_to_db.py --sample_info data/test/baltic_redox_cline_2014/sample_info.csv \
    --gene_counts data/test/baltic_redox_cline_2014/all_genes.tpm.tsv.gz \
    --metadata_reference data/test/metadata_reference.tsv \
    --tmp_file /Users/johannesalneberg/repos/BARM_web_server/data/test/tmp_file.csv
