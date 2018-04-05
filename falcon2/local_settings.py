# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '_&s3zbjykus5ydsl39^lbxnaz7)9%v+oda#ph2fhw!^n7b5qhr'

ALLOWED_HOSTS = [
    u'igskgacgvmdevwb.cr.usgs.gov',
    u'vmdevwb.cr.usgs.gov',
    u'localhost',
    u'0.0.0.0',
    u'vmdevwb',
]

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASE_ROUTERS = ['falcon2.routers.FalconRouter', ]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'auth_db',
        'USER': 'ambaker',
        'PASSWORD': 'gopher',
        'HOST': 'vmdevdb.cr.usgs.gov',
        'PORT': '5432',
    },
    'falcon_db': {
        'NAME': 'falcon2',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': 'falcon_owner',
        'PASSWORD': 'falcondev',
        'HOST': '136.177.124.17',
        'PORT': '5432',
    }
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
# STATIC_ROOT = '/var/www/html/static'