"""Ishga tushirish fayllarini (systemd, nginx, backup.sh) Windows'da ham tekshiradi.

Haqiqiy tekshiruv VM'da: `systemd-analyze verify deploy/*.service deploy/*.timer` (docs/ishga-tushirish.md).
"""
import configparser
import re
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent
BIRLIKLAR = [
    "av-gunicorn.service",
    "av-sinxron.service",
    "av-sinxron.timer",
    "av-sinxron-toliq.service",
    "av-sinxron-toliq.timer",
    "av-backup.service",
    "av-backup.timer",
]


def oqi(nom):
    p = configparser.ConfigParser(strict=False, interpolation=None)
    p.optionxform = str
    p.read_string((DEPLOY / nom).read_text(encoding="utf-8"))
    return p


@pytest.mark.parametrize("nom", BIRLIKLAR + ["nginx-av.conf", "backup.sh"])
def test_fayl_mavjud_va_lf(nom):
    xom = (DEPLOY / nom).read_bytes()
    assert xom
    assert b"\r\n" not in xom


@pytest.mark.parametrize(
    "nom,oncalendar",
    [
        ("av-sinxron.timer", "*-*-* *:00:00"),
        ("av-sinxron-toliq.timer", "*-*-* 03:02:30"),
        ("av-backup.timer", "*-*-* 02:30:00"),
    ],
)
def test_timer(nom, oncalendar):
    p = oqi(nom)
    assert p["Timer"]["OnCalendar"] == oncalendar
    assert p["Timer"]["Persistent"] == "true"
    assert p["Install"]["WantedBy"] == "timers.target"
    assert p["Timer"]["Unit"] == nom.replace(".timer", ".service")


@pytest.mark.parametrize(
    "nom", ["av-gunicorn.service", "av-sinxron.service", "av-sinxron-toliq.service", "av-backup.service"]
)
def test_service_kalitlari(nom):
    s = oqi(nom)["Service"]
    for kalit in ("ExecStart", "User", "WorkingDirectory"):
        assert s.get(kalit), f"{nom}: {kalit} yo'q"
    if nom != "av-backup.service":
        assert s["EnvironmentFile"].endswith(".env")
    assert oqi(nom)["Unit"]["Description"]


@pytest.mark.parametrize("nom", ["av-sinxron.service", "av-sinxron-toliq.service", "av-backup.service"])
def test_oneshot(nom):
    assert oqi(nom)["Service"]["Type"] == "oneshot"


def test_sinxron_buyruqlari():
    oddiy = oqi("av-sinxron.service")["Service"]["ExecStart"]
    toliq = oqi("av-sinxron-toliq.service")["Service"]["ExecStart"]
    assert oddiy.endswith("manage.py sinxron")
    assert "--toliq" not in oddiy
    assert toliq.endswith("manage.py sinxron --toliq")


def test_gunicorn():
    s = oqi("av-gunicorn.service")["Service"]
    assert "--timeout 120" in s["ExecStart"]
    assert "config.wsgi" in s["ExecStart"]
    assert s["Restart"] == "always"


def test_backup_service():
    assert oqi("av-backup.service")["Service"]["ExecStart"].endswith("backup.sh")


def test_nginx():
    t = (DEPLOY / "nginx-av.conf").read_text(encoding="utf-8")
    assert "client_max_body_size 16m;" in t
    assert "proxy_read_timeout 120s;" in t
    assert re.search(r"location /static/ \{[^}]*alias [^;]*staticfiles/;", t)
    assert "X-Forwarded-For" in t and "X-Forwarded-Proto" in t
    assert "location /media/" not in t
    assert "PROXY_ORQASIDA=True" in t


def test_backup_sh():
    t = (DEPLOY / "backup.sh").read_text(encoding="utf-8")
    assert t.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in t
    assert re.search(r"^umask 077$", t, re.M)
    assert "pg_dump -Fc" in t
    assert "/var/backups/av" in t
    assert "-mtime +14" in t
    assert "DATABASE_URL" in t and "MEDIA_ROOT" in t
    assert not re.search(r"postgres(ql)?://\S+:\S+@", t), "parol qattiq yozilgan"


WINDOWS = DEPLOY / "windows"


@pytest.mark.parametrize("nom", ["sozlamalar.ps1", "xizmat_ornatish.ps1", "iis_sozla.ps1", "vazifalar_ornatish.ps1", "zaxira.ps1"])
def test_windows_skriptlari_bom_va_crlf(nom):
    """PowerShell 5.1 BOM'siz UTF-8 ni ANSI deb o'qiydi (o'zbekcha belgilar buziladi)."""
    xom = (WINDOWS / nom).read_bytes()
    assert xom.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in xom.replace(b"\r\n", b"")


def test_windows_sozlamalari_bir_xil():
    s = (WINDOWS / "sozlamalar.ps1").read_text(encoding="utf-8-sig")
    assert '$Domen     = "av.dsyuksak.uz"' in s and "$Port      = 8092" in s and "$IchkiPort = 8000" in s
    web = (WINDOWS / "web.config").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8000/{R:1}" in web and 'name="HTTP_X_FORWARDED_PROTO" value="https"' in web
    assert 'maxAllowedContentLength="16777216"' in web


def test_windows_vazifalar_jadvali():
    v = (WINDOWS / "vazifalar_ornatish.ps1").read_text(encoding="utf-8-sig")
    assert "-RepetitionInterval (New-TimeSpan -Hours 1)" in v  # sinxron har soatda
    assert '(New-ScheduledTaskTrigger -Daily -At (Vaqt 3 2 30))' in v and '"sinxron --toliq"' in v
    assert '(New-ScheduledTaskTrigger -Daily -At (Vaqt 2 30))' in v and "zaxira.ps1" in v
    x = (WINDOWS / "xizmat_ornatish.ps1").read_text(encoding="utf-8-sig")
    assert '"--listen=127.0.0.1:$IchkiPort"' in x and '"--channel-timeout=130"' in x and "config.wsgi:application" in x


def test_waitress_talablarda():
    assert any(q.startswith("waitress") for q in (DEPLOY.parent / "requirements.txt").read_text().splitlines())
