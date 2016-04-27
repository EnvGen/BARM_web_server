# BARM_web_server
Baltic sea Reference Metagenome web server

## Dev note
I always forget this, to log in to psql on local mac:

    sudo -u postgres /Library/PostgreSQL/9.4/bin/psql

The first password it asks for is for the sudo. The second password is postgres psql password.

When creating a new database:

    sudo -u postgres /Library/PostgreSQL/9.4/bin/createdb -U $USER --locale=en_US.utf-8 -E utf-8 -O $USER barm_web_dev -T template0

The first password is for sudo, the second is for user $USER (not postgres) for psql.


### Drop stage database and recreate it with new data:
Drop the stage database with all the tables:

    sudo -u postgres /Library/PostgreSQL/9.4/bin/psql
    postgres=# DROP DATABASE barm_web_dev;
    postgres=# \q

Recreate the empty stage database:

    sudo -u postgres /Library/PostgreSQL/9.4/bin/createdb -U $USER --locale=en_US.utf-8 -E utf-8 -O $USER barm_web_dev -T template0

Recreate all the tables:

    source activate BARM_web
    source local_variables.sh
    python manage.py db upgrade

Populate the tables:

    time python populate_db.py --sample_info data/stage/samples.csv --all_annotations data/stage/all_annotations.tsv --annotation_source_info data/stage/annotation_source_info.csv --gene_annotations_cog data/stage/megahit_coassembly.0.COG.tsv --gene_annotations_pfam data/stage/megahit_coassembly.0.PFAM.tsv --gene_annotations_tigrfam data/stage/megahit_coassembly.0.TIGR.tsv --reference_assembly "megahit_coassembly.0" --gene_counts data/stage/rpkm_table.tsv --metadata_reference data/stage/metadata_reference.tsv --tmp_file /Users/johannesalneberg/repos/BARM_web_server/data/stage/tmp_file.csv
