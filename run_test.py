#!/usr/bin/env python
import os
import subprocess
import argparse

def run_tests(args):
    subprocess.check_call(["python", "-m", "unittest", "test_unit_model.py"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests")
    parser.set_defaults(func=run_tests)
    parser.add_argument("--db", help="Overrule the default database url")
    args = parser.parse_args()

    OLD_APP_SETTINGS=os.environ.get("APP_SETTINGS", None)
    OLD_DATABASE_URL=os.environ.get("DATABASE_URL", None)
    USER = os.environ["USER"]

    try:
        os.environ["APP_SETTINGS"]="config.TestingConfig"
        if args.db is None:
            os.environ["DATABASE_URL"]="postgresql://{}:local_dev_pass@localhost/BARM_web_test".format(USER)
        else:
            os.environ["DATABASE_URL"]=args.db
        args.func(args)
    except:
        if OLD_APP_SETTINGS:
            os.environ["APP_SETTINGS"] = OLD_APP_SETTINGS
        if OLD_DATABASE_URL:
            os.environ["DATABASE_URL"] = OLD_DATABASE_URL
        raise
