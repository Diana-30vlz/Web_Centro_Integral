from pathlib import Path
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-s&7s(!9)mle=gz1y&!npcobj%z8dhr5^2va%^v^j$cz8x-3)_#'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'CentroIntegral.pythonanywhere.com' ]

AUTH_USER_MODEL = 'Pacientes.CustomUser'
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Pacientes',
    'Inventario',
    'InventarioInsumos',
    'widget_tweaks'

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'CentroIntegralTerapeutico.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # ¡Esta línea es la más importante!
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'Pacientes.context_processors.user_roles_processor',

            ],
        },
    },
]

WSGI_APPLICATION = 'CentroIntegralTerapeutico.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/swhettings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cit',
        'USER': 'postgres',      # Tu usuario local de PostgreSQL (suele ser postgres)
        'PASSWORD': 'Mjl41412#',
        'HOST': '127.0.0.1',     # IPv4 local (trust). localhost resuelve a ::1 y falla con SCRAM.
        'PORT': '5432',          # <-- PUERTO LOCAL POR DEFECTO
    }
}


# Configuración de URLs para redirección después de login/logout
LOGIN_REDIRECT_URL = '/doctor_home/' # Redirige aquí después de iniciar sesión con éxito
LOGOUT_REDIRECT_URL = '/'          # Redirige aquí después de cerrar sesión
LOGIN_URL = '/signin/'             # La URL de tu página de inicio de sesión




#URLs FARMACIA
LOGIN_REDIRECT_URL = '/doctor_home/' # Dashboard de doctora; farmacia redirige en su propia vista de login

# URL a la que redirigir si se requiere inicio de sesión
LOGIN_URL = '/signin/' # Login de doctora (no sobreescribir con /login/ de farmacia)


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'es-mx'

TIME_ZONE = 'America/Mexico_City'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'  # o '/staticfiles/' si así lo prefieres, pero '/static/' es más común
                         # ¡Lo importante es que coincida con la URL en tus plantillas!
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'), # Esto es lo que le dice a Django dónde buscar HomeSinInicio.css
]


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR,'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_AGE = 8 * 60 * 60  # 28800 segundos

# 4. Forzar el uso de HTTPS y HSTS
# Django redirigirá todo el tráfico de HTTP a HTTPS.
# 4. Forzar el uso de HTTPS y HSTS
SECURE_SSL_REDIRECT = False  # Cambia a False
SECURE_HSTS_SECONDS = 0      # Cambia a 0

# 5. Proteger las cookies y los tokens de sesión
SESSION_COOKIE_SECURE = False # Cambia a False
CSRF_COOKIE_SECURE = False    # Cambia a False
