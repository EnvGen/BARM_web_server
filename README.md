# BARM_web_server
Baltic sea Reference Metagenome web server

## Dev note
I always forget this, to log in to psql on local mac:

    sudo -u postgres /Library/PostgreSQL/9.4/bin/psql

The first password it asks for is for the sudo. The second password is postgres psql password.

When creating a new database:

    sudo -u postgres /Library/PostgreSQL/9.4/bin/createdb -U $USER --locale=en_US.utf-8 -E utf-8 -O $USER barm_web_dev -T template0

The first password is for sudo, the second is for user $USER (not postgres) for psql. 
