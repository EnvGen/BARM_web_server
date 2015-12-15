import os

class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    if os.environ.get('BARM_SECRET_KEY'):
        SECRET_KEY = os.environ['BARM_SECRET_KEY']
    else:
        raise Exception('The variable BARM_SECRET_KEY is not set')
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(Config):
    DEBUG = False


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
