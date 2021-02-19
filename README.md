# BARM_web_server
Baltic sea Reference Metagenome web server

running at https://barm.scilifelab.se

## Installation instructions

```
conda create -n barm_run_env python=3.9
conda activate barm_run_env
git clone https://github.com/EnvGen/BARM_web_server.git
cd BARM_web_server/
conda install psycopg2
pip install -r requirements.txt
```

Install postgresql locally: https://www.postgresql.org/download/

Log in with default postgres user:

    sudo -u postgres /Library/PostgreSQL/13/bin/psql

The first password it asks for is for the sudo. The second password is postgres psql password.

Create database user for local user:
    sudo -u postgres /Library/PostgreSQL/13/bin/createuser --createdb --password --role=pg_read_server_files $USER

Sudo and then postgres password.

    sudo -u postgres /Library/PostgreSQL/13/bin/psql

postgres password.

    ALTER ROLE "<username>" WITH PASSWORD '<password>';
    \q;

Then create an empty database for unit tests:

    python manage.py create_empty --db barm_web_test

Run unittests:

    python run_test.py unit

Integration tests exist and should work, but they are a bit difficult to set up so that's not done currently.

## Dev note
I always forget this, to log in to psql on local mac:

    sudo -u postgres /Library/PostgreSQL/13/bin/psql

The first password it asks for is for the sudo. The second password is postgres psql password.

When creating a new database:

    sudo -u postgres /Library/PostgreSQL/13/bin/createdb -U $USER --locale=en_US.utf-8 -E utf-8 -O $USER barm_web_dev -T template0

The first password is for sudo, the second is for user $USER (not postgres) for psql.


### Drop stage database and recreate it with new data:
Check the manage.py or the setup_test_database.py files for useful commands.

### Export database to the server:

    pg_dump dbname >file.sql

    scp file.sql username.login@barm.scilifelab.se:~/

### On the actual server
Loading in a new databse:

    createdb -U db_user -O db_owner barm_web_prod -T template0
    psql -U db_user -d barm_web_prod -f file.sql

Shutdown current process:

    pkill -f runserver

Start running the server manually:

    bash /home/<user>/starta_barm.sh  >>  /var/log/barm.log  2>&1 &
