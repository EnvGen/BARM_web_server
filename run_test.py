#!/usr/bin/env python
import os
import subprocess

def main():
    OLD_APP_SETTINGS=os.environ["APP_SETTINGS"]
    OLD_DATABASE_URL=os.environ["DATABASE_URL"]
    USER = os.environ["USER"]

    try:
        os.environ["APP_SETTINGS"]="config.DevelopmentConfig"
        os.environ["DATABASE_URL"]="postgresql://{}:local_dev_pass@localhost/barm_web_dev".format(USER)
        subprocess.check_call(["python", "-m", "unittest", "test_app.py"])
    except:
        os.environ["APP_SETTINGS"] = OLD_APP_SETTINGS
        os.environ["DATABASE_URL"] = OLD_DATABASE_URL
        raise

if __name__ == "__main__":
    main()
