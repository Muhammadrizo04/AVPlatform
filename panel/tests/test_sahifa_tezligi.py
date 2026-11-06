"""`manage.py sahifa_tezligi`: ishchi serverda ham ishlatiladi — bazaga hech narsa yozmasligi shart."""
import io

import pytest
from django.contrib.sessions.models import Session
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db


def test_olchaydi_va_hech_narsa_yozmaydi(foydalanuvchi):
    user = foydalanuvchi("admin")
    chiqish = io.StringIO()
    call_command("sahifa_tezligi", user.username, "/", "/av/", stdout=chiqish)
    matn = chiqish.getvalue()
    assert "/av/" in matn and " 200 " in matn and "SQL so'rovlari" in matn
    user.refresh_from_db()
    assert Session.objects.count() == 0 and user.last_login is None


def test_nomalum_foydalanuvchi():
    with pytest.raises(CommandError):
        call_command("sahifa_tezligi", "yoq-odam")
