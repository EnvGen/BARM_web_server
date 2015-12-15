#!/usr/bin/env python
import os
import subprocess
import argparse

def run_tests(args):
    subprocess.check_call(["python", "-m", "unittest", "test_app.py"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests")
    parser.set_defaults(func=run_tests)
    args = parser.parse_args()

    OLD_APP_SETTINGS=os.environ["APP_SETTINGS"]
    OLD_DATABASE_URL=os.environ["DATABASE_URL"]
    USER = os.environ["USER"]

    try:
        os.environ["APP_SETTINGS"]="config.TestingConfig"
        os.environ["DATABASE_URL"]="postgresql://{}:local_dev_pass@localhost/BARM_web_test".format(USER)
        args.func(args)
    except:
        os.environ["APP_SETTINGS"] = OLD_APP_SETTINGS
        os.environ["DATABASE_URL"] = OLD_DATABASE_URL
        raise
