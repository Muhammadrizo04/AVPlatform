"""Asosiy vositalar platformasi sozlamalari. Maxfiy qiymatlar faqat .env dan."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")  # .env bo'lmasa jim o'tadi; haqiqiy muhit o'zgaruvchilari ustun

DEBUG = env.bool("DEBUG", default=False)

# Standart qiymatlar faqat DEBUG da; ishlab chiqarishda .env da bo'lishi shart.
SECRET_KEY = env.str("SECRET_KEY", default="dev-faqat-ishlab-chiqish-uchun" if DEBUG else environ.Env.NOTSET)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# nginx ortida bo'lsa mijoz IP'si X-Forwarded-For dan olinadi (1 ta proksi); aks holda REMOTE_ADDR.
PROXY_ORQASIDA = env.bool("PROXY_ORQASIDA", default=False)

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://av:av@localhost:5432/av" if DEBUG else environ.Env.NOTSET,
    )
}

# 1C HTTP-xizmati (faqat o'qish)
ONEC_URL = env.str("ONEC_URL", default="")
ONEC_LOGIN = env.str("ONEC_LOGIN", default="")
ONEC_PAROL = env.str("ONEC_PAROL", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "onec",
    "hisoblar",
    "jurnal",
    "vositalar",
    "mol",
    "yorliqlar",
    "panel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "panel.context_processors.sinxron_holati",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "hisoblar:kirish"
LOGIN_REDIRECT_URL = "panel:bosh"
LOGOUT_REDIRECT_URL = "hisoblar:kirish"

# Sessiya: 8 soat harakatsizlikdan keyin tugaydi
SESSION_COOKIE_AGE = 8 * 3600
SESSION_SAVE_EVERY_REQUEST = True

# Kirish: 5 noto'g'ri urinish -> 15 daqiqa blok
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25  # soat
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]  # bir foydalanuvchining xatosi boshqalarni bloklamaydi
AXES_RESET_ON_SUCCESS = True  # muvaffaqiyatli kirishdan keyin xato hisobi nolga tushadi
if PROXY_ORQASIDA:
    AXES_IPWARE_PROXY_COUNT = 1
    AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]
AXES_LOCKOUT_TEMPLATE = "hisoblar/blok.html"

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = env.str("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
