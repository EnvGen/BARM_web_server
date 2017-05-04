from flask.ext.script import Manager, Command, Option
from flask.ext.migrate import Migrate, MigrateCommand
import os
from subprocess import check_call

from app import app, db
app.config.from_object(os.environ['APP_SETTINGS'])

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

class CreateDB(Command):
    "Creates and populates a db from scratch"

    option_list = (
            Option('--db', dest='db', help='Database name'),
            Option('--data', dest='data', help='Data from data/ dir to be loaded into the database'),
            Option('--sample_set', dest='sample_set', help='Sample set from where sample info and quantification data should be loaded'),
            Option('--root_path', dest='root_path', help='Root path to where data dir is located, needed for populate script')
            )

    def run(self, db, data, sample_set, root_path):
        assert db in ['barm_web_dev', 'barm_web_test_integration']
        assert os.environ['DATABASE_URL'].endswith(db)
        print("Drop db")
        check_call(["sudo", "-u", "postgres", "/Library/PostgreSQL/9.4/bin/psql", "-c", "DROP DATABASE {};".format(db)])
        print("Create db")
        check_call(["sudo", "-u", "postgres", "/Library/PostgreSQL/9.4/bin/createdb", "-U", os.environ["USER"], "--locale=en_US.utf-8", "-E", "utf-8", "-O", os.environ["USER"], db, "-T", "template0"])
        print("Upgrade")
        check_call(["python", "manage.py", "db", "upgrade"])
        print("Migrate")
        check_call(["python", "manage.py", "db", "migrate"])
        print("Populate db")
        check_call(["time", "python", "populate_db.py", \
            "--sample_info",  "data/{0}/{1}/sample_info.csv".format(data, sample_set), \
            "--pfam_annotation_info", "data/{}/annotation_info/all_pfam_annotation_info.tsv".format(data), \
            "--eggnog_category_info", "data/{}/annotation_info/eggnog_categories.tsv".format(data), \
            "--eggnog_annotation_info", "data/{}/annotation_info/all_EggNOG_annotation_info.tsv".format(data), \
            "--ec_annotation_info",  "data/{}/annotation_info/all_EC_annotation_info.tsv".format(data), \
            "--dbcan_annotation_info", "data/{}/annotation_info/all_dbCAN_annotation_info.tsv".format(data), \
            "--tigrfam_annotation_info", "data/{}/annotation_info/all_TIGRFAM_annotation_info.tsv".format(data), \
            "--annotation_source_info", "data/{}/annotation_source_info.csv".format(data), \
            "--gene_annotations_pfam", "data/{}/annotations/all.pfam.standardized.tsv".format(data), \
            "--gene_annotations_eggnog", "data/{}/annotations/all.EggNOG.standardized.tsv".format(data), \
            "--gene_annotations_ec", "data/{}/annotations/all.EC.standardized.tsv".format(data), \
            "--gene_annotations_dbcan", "data/{}/annotations/all.dbCAN.standardized.tsv".format(data), \
            "--gene_annotations_tigrfam", "data/{0}/annotations/all.TIGRFAM.standardized.tsv".format(data), \
            "--gene_counts", "data/{}/{}/all_genes.tpm.tsv.gz".format(data, sample_set), \
            "--metadata_reference", "data/{}/metadata_reference.tsv".format(data), \
            "--reference_assembly", "megahit_coassembly.0", \
            "--tmp_file", "{}/data/{}/tmp_file.csv".format(root_path, data), \
            "--taxonomy_per_gene", "{}/data/{}/lca_megan.tsv".format(root_path, data)])

manager.add_command('create_db', CreateDB)

if __name__ == '__main__':
    manager.run()
