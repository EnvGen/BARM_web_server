#!/usr/bin/env python
import os
import subprocess
import argparse

def run_integration_tests(args):
    cmd = ["python", "-m", "unittest", "test_integration.py"]
    if args.test:
        cmd[-1] = cmd[-1].split('.')[0] + '.SampleTestCase.' + args.test

    subprocess.check_call(cmd)

def run_unit_tests(args):
    subprocess.check_call(["python", "-m", "unittest", "test_unit_model.py"])

def run_tests(args):
    run_unit_tests(args)
    run_integration_tests(args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests, by default all.", add_help=False)
    parser.set_defaults(func=run_tests)
    parser.add_argument("--db", help="Overrule the default database url")
    parser.add_argument('--test', help="Specific test")
    subparsers = parser.add_subparsers()

    unit_parser = subparsers.add_parser('unit', parents=[parser])
    unit_parser.set_defaults(func=run_unit_tests)

    integration_parser = subparsers.add_parser('integration', parents=[parser])
    integration_parser.set_defaults(func=run_integration_tests)

    args = parser.parse_args()

    OLD_APP_SETTINGS=os.environ.get("APP_SETTINGS", None)
    OLD_DATABASE_URL=os.environ.get("DATABASE_URL", None)
    USER = os.environ["USER"]

    try:
        os.environ["APP_SETTINGS"]="config.TestingConfig"
        if args.db is None:
            os.environ["DATABASE_URL"]="postgresql://{}:local_dev_pass@localhost/barm_web_test".format(USER)
        else:
            os.environ["DATABASE_URL"]=args.db
        args.func(args)
    except:
        if OLD_APP_SETTINGS:
            os.environ["APP_SETTINGS"] = OLD_APP_SETTINGS
        if OLD_DATABASE_URL:
            os.environ["DATABASE_URL"] = OLD_DATABASE_URL
        raise

    os.environ["APP_SETTINGS"] = OLD_APP_SETTINGS
    os.environ["DATABASE_URL"] = OLD_DATABASE_URL
