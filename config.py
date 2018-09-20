import sys
from datetime import timedelta


class BaseConfig(object):
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@127.0.0.1/mscheduler?charset=utf8'
    DB_RECONNECT_ATTEMPTS = 100
    DB_RECONNECT_ATTEMPTS_DELAY_SEC = 15
    SECRET_KEY = '\xad$\xc6*\x96\xac\x12\x1c\xe4,\xac\x9a\xae\xd5IC\x9e\x8f\x1b\xd6gr\x19\xfa'
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    # The internal database id of the @astrobot provider
    ASTROBOT_PROVIDER_ID = 1


class LocalConfig(BaseConfig):
    ENVIRONMENT = "dev"
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = "./session"
    DEBUG = True


if "dev" in sys.argv:
    config = LocalConfig()
else:
    raise Exception(
        "No environment specified. Use: $ python main.py <env>, where env is either 'dev' or 'aws', or set environment variable DEPLOYMENT_TYPE")

for attr in dir(config):
    globals()[attr] = getattr(config, attr)
