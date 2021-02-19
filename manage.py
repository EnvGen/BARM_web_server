from flask_script import Manager, Command, Option
from flask_migrate import Migrate, MigrateCommand
import os
from subprocess import check_call

from app import app, db
app.config.from_object(os.environ['APP_SETTINGS'])

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)


def _drop_and_recreate_db(db):
    print("Drop db")
    check_call(["sudo", "-u", "postgres", "psql", "-c", "DROP DATABASE IF EXISTS {};".format(db)], env=os.environ)
    print("Create db")
    check_call(["sudo", "-u", "postgres", "createdb", "-U", os.environ["USER"], "--locale=en_US.utf-8", "-E", "utf-8", "-O", os.environ["USER"], db, "-T", "template0"])


class CreateEmpty(Command):
    "Creates an empty db from scratch"
    option_list = (
            Option('--db', dest='db', help='Database name'),
            )

    def run(self, db):
        _drop_and_recreate_db(db)


class CreateAndPopulateDB(Command):
    "Creates and populates a db from scratch"

    option_list = (
            Option('--db', dest='db', help='Database name'),
            Option('--data', dest='data', help='Data from data/ dir to be loaded into the database'),
            Option('--sample_set', dest='sample_set', help='Sample set from where sample info and quantification data should be loaded'),
            Option('--root_path', dest='root_path', help='Root path to where data dir is located, needed for populate script')
            )

    def run(self, db, data, sample_set, root_path):
        assert os.environ['DATABASE_URL'].endswith(db)
        _drop_and_recreate_db(db)
        print("Upgrade")
        check_call(["python", "manage.py", "db", "upgrade"])
        print("Migrate")
        check_call(["python", "manage.py", "db", "migrate"])
        print("Upgrade")
        check_call(["python", "manage.py", "db", "upgrade"])
        print("Populate db")
        check_call(["time", "python", "populate_db.py", \
            "--sample_info",  "data/{0}/{1}/sample_info.csv".format(data, sample_set), \
            "--pfam_annotation_info", "data/{}/annotation_info/all_pfam_annotation_info.tsv".format(data), \
            "--eggnog_category_info", "data/{}/annotation_info/eggnog_categories.tsv".format(data), \
            "--eggnog_annotation_info", "data/{}/annotation_info/all_EggNOG_annotation_info.tsv".format(data), \
            "--ec_annotation_info",  "data/{}/annotation_info/all_EC_annotation_info.tsv".format(data), \
            "--tigrfam_annotation_info", "data/{}/annotation_info/all_TIGRFAM_annotation_info.tsv".format(data), \
            "--annotation_source_info", "data/{}/annotation_source_info.csv".format(data), \
            "--gene_annotations_pfam", "data/{}/annotations/all.pfam.standardized.tsv".format(data), \
            "--gene_annotations_eggnog", "data/{}/annotations/all.EggNOG.standardized.tsv".format(data), \
            "--gene_annotations_ec", "data/{}/annotations/all.EC.standardized.tsv".format(data), \
            "--gene_annotations_tigrfam", "data/{0}/annotations/all.TIGRFAM.standardized.tsv".format(data), \
            "--gene_counts", "data/{}/{}/all_genes.tpm.tsv.gz".format(data, sample_set), \
            "--metadata_reference", "data/{}/metadata_reference.tsv".format(data), \
            "--reference_assembly", "megahit_coassembly.0", \
            "--tmp_file", "{}/data/{}/tmp_file.csv".format(root_path, data), \
            "--taxonomy_per_gene", "{}/data/{}/lca_megan.tsv".format(root_path, data)])

class AddSampleSetCounts(Command):
    "Populates a db with new sample set counts"

    option_list = (
            Option('--db', dest='db', help='Database name'),
            Option('--data', dest='data', help='Data from data/ dir to be loaded into the database'),
            Option('--sample_set', dest='sample_set', help='Sample set from where sample info and quantification data should be loaded'),
            Option('--root_path', dest='root_path', help='Root path to where data dir is located, needed for populate script')
            )

    def run(self, db, data, sample_set, root_path):
        assert db in ['barm_web_dev', 'barm_web_test_integration']
        assert os.environ['DATABASE_URL'].endswith(db)
        print("Populate db")
        check_call(["time", "python", "add_sample_set_to_db.py", \
            "--sample_info",  "data/{0}/{1}/sample_info.csv".format(data, sample_set), \
            "--gene_counts", "data/{}/{}/all_genes.tpm.tsv.gz".format(data, sample_set), \
            "--metadata_reference", "data/{}/metadata_reference.tsv".format(data), \
            "--tmp_file", "{}/data/{}/tmp_file.csv".format(root_path, data)])

manager.add_command('create_db', CreateAndPopulateDB)
manager.add_command('create_empty', CreateEmpty)
manager.add_command('add_sample_set_counts', AddSampleSetCounts)

if __name__ == '__main__':
    manager.run()
