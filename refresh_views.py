import app
from models import *
import pandas as pd
import argparse
import os
import sys
import logging
import datetime

from materialized_view_factory import refresh_all_mat_views

def main():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    session = app.db.session()

    logging.info("Refreshing materialized view")
    refresh_all_mat_views()
    session.commit()
    logging.info("Finished!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="This will refresh the materialized views. Useful if data have been added but refreshing failed")
    main()
