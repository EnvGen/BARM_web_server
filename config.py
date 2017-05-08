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


def check_oauth_variables(config_class):
    if config_class == "ProductionConfig":
        if os.environ.get('OAUTHLIB_INSECURE_TRANSPORT'):
            raise Exception('The variable OAUTHLIB_INSECURE_TRANSPORT is set')

        if os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE'):
            raise Exception('The variable OAUTHLIB_RELAX_TOKEN_SCOPE is set')

    else:
        if not os.environ.get('OAUTHLIB_INSECURE_TRANSPORT'):
            raise Exception('The variable OAUTHLIB_INSECURE_TRANSPORT is not set')

        if not os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE'):
            raise Exception('The variable OAUTHLIB_RELAX_TOKEN_SCOPE is not set')
