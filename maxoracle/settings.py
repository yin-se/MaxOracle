from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-dev-secret')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [host for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.lotto.apps.LottoConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'maxoracle.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'maxoracle.wsgi.application'
ASGI_APPLICATION = 'maxoracle.asgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'zh-hans'
LANGUAGES = [
    ('zh-hans', '简体中文'),
    ('en', 'English'),
]
TIME_ZONE = 'America/Toronto'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'apps' / 'lotto' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRON_INGEST_TOKEN = os.getenv('CRON_INGEST_TOKEN')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'lottomax-analysis',
        'TIMEOUT': 60 * 15,
    }
}

LOTTO_CONFIG = {
    'DATA_SOURCES': {
        'olg': {
            'past_results_url': 'https://www.olg.ca/en/lotto-max/past-results.html',
            'enabled': True,
        },
        'lotto8': {
            'past_results_url': 'https://www.lotto-8.com/canada/listltoCAMAX.asp',
            'enabled': True,
        },
        'lotterypost': {
            'past_results_url': 'https://www.lotterypost.com/results/zz/lottomax/past',
            'enabled': True,
        },
    },
    'DEFAULT_WINDOW': int(os.getenv('LOTTO_WINDOW', '1000')),
    'DEFAULT_ROLLING_WINDOW': int(os.getenv('LOTTO_ROLLING_WINDOW', '100')),
    'RECOMMENDATION_COUNT': int(os.getenv('LOTTO_RECOMMENDATION_COUNT', '5')),
    'RECOMMENDATION_SEED': os.getenv('LOTTO_RECOMMENDATION_SEED'),
    'MIN_REQUIRED_DRAWS': int(os.getenv('LOTTO_MIN_DRAWS', '1000')),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'lotto': {
            'handlers': ['console'],
            'level': os.getenv('LOTTO_LOG_LEVEL', 'INFO'),
        },
    },
}
