#!/usr/bin/bash

export APP_SETTINGS="config.DevelopmentConfig"
export DATABASE_URL="postgresql://$USER:local_dev_pass@localhost/barm_web_dev"
export OAUTHLIB_INSECURE_TRANSPORT=1
export OAUTHLIB_RELAX_TOKEN_SCOPE=1
export AA_SEQUENCES="data/test/sequences/proteins_clean.small.faa"
export NUC_SEQUENCES="data/test/sequences/proteins_clean.small.ffn"
