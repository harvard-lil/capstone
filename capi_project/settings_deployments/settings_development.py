INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django_extensions',
    'rest_framework',
    'rest_framework.authtoken',
    'capi_project',
]

PIPELINE = {
    'CSS_COMPRESSOR':'pipeline.compressors.cssmin.CSSMinCompressor',
    'CSSMIN_BINARY':'cssmin',
    'COMPILERS' : (
        'pipeline.compilers.sass.SASSCompiler',
    ),

    'STYLESHEETS': {
        'base': {
            'source_filenames': (
              'css/raw/_normalize.css',
              'css/raw/_variables.css/raw',
              'css/raw/base.sass',
            ),
            'output_filename': 'css/base.css',
        },
        'docs': {
            'source_filenames': (
              'css/raw/docs.sass',
            ),
            'output_filename': 'css/docs.css',
        },
        'api': {
            'source_filenames': (
              'css/raw/api.sass',
            ),
            'output_filename': 'css/api.css',
        },

    },
}
