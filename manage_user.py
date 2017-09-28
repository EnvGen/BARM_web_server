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

    # Search for user in db
    user_from_db = User.get_from_email(args.email)
    if user_from_db:
        logging.info("User exists. Exiting")
        sys.exit()

    logging.info("Creating user {}".format(args.email))
    user = User(args.email)
    session.add(user)
    session.commit()
    logging.info("Finished!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", help="A csv file with all the sample information.")
    args = parser.parse_args()

    main(args)
