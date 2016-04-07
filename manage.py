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
            Option('--data', dest='data', help='Data from data/ dir to be loaded into the database')
            )

    def run(self, db, data):
        assert db in ['barm_web_dev2']
        assert data in ['test', 'stage']
        print("Drop db")
        check_call(["sudo", "-u", "postgres", "/Library/PostgreSQL/9.4/bin/psql", "-c", "DROP DATABASE {};".format(db)])
        print("Create db")
        check_call(["sudo", "-u", "postgres", "/Library/PostgreSQL/9.4/bin/createdb", "-U", os.environ["USER"], "--locale=en_US.utf-8", "-E", "utf-8", "-O", os.environ["USER"], db, "-T", "template0"])
        print("Upgrade")
        check_call(["python", "manage.py", "db", "upgrade"])
        print("Populate db")
        check_call(["time", "python", "populate_db.py", "--sample_info",  "data/{0}/samples.csv".format(data), "--all_annotations", "data/{0}/all_annotations.tsv".format(data), "--annotation_source_info", "data/{0}/annotation_source_info.csv".format(data), "--gene_annotations_cog", "data/{0}/megahit_coassembly.0.COG.tsv".format(data), "--gene_annotations_pfam", "data/{0}/megahit_coassembly.0.PFAM.tsv".format(data), "--gene_annotations_tigrfam".format(data), "data/{0}/megahit_coassembly.0.TIGR.tsv".format(data), "--reference_assembly", "megahit_coassembly.0", "--gene_counts", "data/{0}/rpkm_table.tsv".format(data)])

manager.add_command('create_db', CreateDB)

if __name__ == '__main__':
    manager.run()
