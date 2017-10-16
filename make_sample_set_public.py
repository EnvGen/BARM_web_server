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

    logging.info("Searching for sample set.")

    if len(SampleSet.query.filter_by(name=args.sample_set_name).all()) == 0:
        logging.info("No sample set found with that name")
        sys.exit(-1)

    ss = SampleSet.query.filter_by(name=args.sample_set_name).first()
    ss.public = True

    session.add(ss)

    session.commit()
    logging.info("Finished!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_set_name", help="The sample set name.")
    args = parser.parse_args()

    main(args)
