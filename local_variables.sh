#!/usr/bin/bash

export APP_SETTINGS="config.DevelopmentConfig"
export BARM_SECRET_KEY="totallyMadeUp"
export DATABASE_URL="postgresql://$USER:local_dev_pass@localhost/barm_web_dev"
export BARM_GOOGLE_CLIENT_ID="madeup_lets_see_if_it_works.apps.googleusercontent.com"
export BARM_GOOGLE_CLIENT_SECRET="This1ismadeup2"
export OAUTHLIB_INSECURE_TRANSPORT=1
export OAUTHLIB_RELAX_TOKEN_SCOPE=1
export AA_SEQUENCES="data/test/sequences/proteins_clean.small.faa"
export NUC_SEQUENCES="data/test/sequences/proteins_clean.small.ffn"
