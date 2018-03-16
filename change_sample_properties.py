import app
from models import *
import pandas as pd
import argparse
import os
import sys
import logging
import datetime

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

def change_property(session, sample, property_name, new_value):
    sp_all = SampleProperty.query.filter_by(name=property_name, sample_id=sample.id).all()
    if len(sp_all) != 1:
        logging.info("Did not find unique property: {}".format(sp_all))
        sys.exit(-1)
    else:
        logging.info("Jippie!: {0} old_value: {1}, new_value: {2}, for sample {3}".format(sp_all[0].name, sp_all[0].value, new_value, sample.scilifelab_code))

    sp = sp_all[0]
    sp.value = new_value

    session.add(sp)
    return session

def main(args):
    # connect to database
    session = app.db.session()

    logging.info("Searching for sample properties.")

    with open(args.property_vals_file) as ofh:
        for line in ofh:
            line = line.strip()
            scilifelab_code, prop_name, new_val = line.split(',')
            samples = Sample.query.filter_by(scilifelab_code=scilifelab_code).all()

            assert(len(samples) == 1)

            change_property(session, samples[0], prop_name, new_val)

    if args.not_dryrun:
        session.commit()
    logging.info("Finished!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("property_vals_file")
    parser.add_argument("--not_dryrun", action="store_true")
    args = parser.parse_args()

    main(args)
