# 1C kengaytmasi «AVSinxron»

Asosiy vositalar platformasi (Django) 1C «КСБ» bazasidan ma'lumotni shu kengaytma orqali oladi.
Kengaytma **faqat o'qiydi** (faqat `Запрос`; `Записать`/`Провести` yo'q), xavfsiz rejimda ishlashga mo'ljallangan.
Platforma 8.3.13, moslik rejimi 8.3.9, prefiks `АВС_`, HTTP-servis `АВС_AV`, kontekst `/hs/av/`.

| Endpoint (GET) | Javob |
|---|---|
| `/versiya` | `{"versiya":"1.0.0","baza":..,"server_vaqti":..}` |
| `/spravochniklar` | `{"tashkilotlar":[..],"filiallar":[..],"av_turlari":[..],"xodimlar":[..]}` |
| `/vositalar` | `{"vositalar":[..],"qoldiqlar":[..]}` |
| `/harakatlar?dan=YYYYMMDDhhmmss&gacha=YYYYMMDDhhmmss` | `{"harakatlar":[..]}` |

To'liq kontrakt: `docs/superpowers/plans/2026-10-17-av-platforma-1-bosqich.md`, Task 1. Xato → 400/500 + `{"xato":".."}`.

Javob tanasi UTF-8, BOM'siz (`ИспользованиеByteOrderMark.НеИспользовать`). Baribir Django klienti himoya uchun
`resp.content` ni `utf-8-sig` bilan dekodlashi shart (`json.loads(resp.content.decode("utf-8-sig"))`), `resp.json()` emas:
BOM bo'lsa `requests` `.json()` `JSONDecodeError: Unexpected UTF-8 BOM` beradi. Skript har `*.raw.json` uchun
BOM bor-yo'qligini (EF BB BF) chiqaradi.

## Fayllar

- `AVSinxron/` — kengaytma, `DumpConfigToFiles` formatida (Configuration.xml, Languages, HTTPServices, ConfigDumpInfo.xml).
- `AVSinxron/HTTPServices/АВС_AV/Ext/Module.bsl` — servis moduli; `AVSinxron_HTTP_modul.bsl` — uning aynan nusxasi
  (o'qish/ko'rib chiqish uchun). Modulni o'zgartirsangiz — ikkalasini ham yangilang.
- `TestClaude_ornatish.ps1` — yuklash, tekshirish va endpointlarni chaqirish skripti.

Fayllar UTF-8 (BOM bilan), CRLF — 1C dampi formatida. Ularni boshqa kodlashda saqlamang.

## 1. Yuklash va tekshirish (Windows, 1C server kompyuterida)

1. TestClaude uchun Konfigurator ochiq bo'lsa — yoping.
2. Repo ildizida PowerShell:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\1c\TestClaude_ornatish.ps1
   ```
   Skript: ochiq Konfiguratorni tekshiradi → `/LoadConfigFromFiles 1c\AVSinxron -Extension AVSinxron` →
   `/UpdateDBCfg -Extension AVSinxron` → `/CheckModules -Server -Extension AVSinxron` (har biri logi ekranga
   chiqadi, xato bo'lsa to'xtaydi) → `AVSinxron` paroli so'raladi → 4 ta endpoint chaqiriladi, xom javob
   `onec\tests\namunalar\{versiya,spravochniklar,vositalar,harakatlar}.raw.json` ga yoziladi (harakatlar — oxirgi 10 yil).
   **`*.raw.json` da haqiqiy ma'lumot bor — git'ga qo'shmang.**
3. Foydali parametrlar: `-Parol "..."` (so'ramaslik uchun), `-KonfiguratorParol "..."` (Claude foydalanuvchisi
   paroli bo'lsa), `-BazaUrl http://<host>/TestClaude/hs/av`, `-FaqatEndpointlar` (faqat 3-qadam),
   `-EndpointlarsizYuklash` (faqat yuklash), `-Platforma <1cv8.exe yo'li>`.
4. Konfigurator → Конфигурация → Расширения конфигурации: AVSinxron **Активно** va **Безопасный режим** belgilangan
   bo'lsin («Защита от опасных действий» ham).

## 2. `AVSinxron` foydalanuvchisi (faqat o'qish)

Konfigurator yoki 1C:Предприятие → Администрирование → Пользователи → Добавить:

- Имя: `AVSinxron`; «Аутентификация 1С:Предприятия» — kuchli parol; «Показывать в списке выбора» — o'chiq;
  OS-autentifikatsiya — o'chiq.
- Rol: faqat **o'qish** huquqi bor rol (Чтение/Просмотр). Kerakli o'qish huquqlari: Справочник.Организация, Филиал,
  ГруппаОС, Ходимлар, ОсновныеСредства, РегистрНакопления.УчетОС va **УчетОС registratori bo'lgan barcha hujjatlar**
  (hujjat raqami o'qiladi). Bazada mos rol bo'lmasa — mavjud eng tor rolni bering va izohga yozing; modul baribir
  hech narsa yozmaydi. Administrator/Полные права **bermang**.
- Parol Django `.env` ga (`ONEC_LOGIN`, `ONEC_PAROL`) yoziladi, repo'ga emas.

## 3. Publikatsiya (`C:\inetpub\wwwroot\TestClaude\default.vrd`)

Kengaytma HTTP-servislari yoqilganini va sessiyalar qayta ishlatilishini tekshiring:

```xml
<point xmlns="http://v8.1c.ru/8.2/virtual-resource-system" ... base="/TestClaude" ib="Srvr=&quot;localhost&quot;;Ref=&quot;TestClaude&quot;;">
	<httpServices publishByDefault="true" publishExtensionsByDefault="true">
		<!-- agar servislar alohida sanab o'tilgan bo'lsa: -->
		<service name="АВС_AV" rootUrl="av" enable="true" reuseSessions="autouse" sessionMaxAge="20" poolSize="10" poolTimeout="5"/>
	</httpServices>
</point>
```

- `publishExtensionsByDefault="true"` — bo'lmasa kengaytma servislari 404 beradi.
- `reuseSessions="autouse"` — har so'rovda yangi seans ochilmasligi (litsenziya va tezlik) uchun.
- O'zgartirgandan keyin: `iisreset` (yoki TestClaude app pool'ini qayta ishga tushiring).
- Tekshiruv: `curl -u "AVSinxron:<parol>" http://<host>/TestClaude/hs/av/versiya` → 200 va `"versiya":"1.0.0"`.

## 4. 404 bo'lsa

1. Avval: kengaytma «Активно»mi, `publishExtensionsByDefault="true"`, `iisreset` qilinganmi, URL'da `/hs/av/` to'g'rimi.
2. Shunda ham 404 — servisni **MobilOstatka kengaytmasi ichiga alohida HTTP-servis** sifatida ko'chiring (spec §6.1):
   Konfigurator → MobilOstatka kengaytmasi → HTTP-сервисы → Добавить (nomi MobilOstatka prefiksi bilan,
   masalan `Расш1_AV`), Корневой URL `av`, `Повторное использование сеансов` = «Автоматически использовать»,
   4 ta URL-shablon (`/versiya`, `/spravochniklar`, `/vositalar`, `/harakatlar`, har birida GET, obrabotchiklar
   `VersiyaGET`, `SpravochniklarGET`, `VositalarGET`, `HarakatlarGET`), modulga `AVSinxron_HTTP_modul.bsl` matnini
   to'liq qo'ying. MobilOstatka'ni yangilang, `iisreset`, qayta tekshiring. URL o'zgarmaydi: `/hs/av/...`
   (AVSinxron'dagi servis bilan bir vaqtda faol bo'lmasin — `rootUrl` to'qnashadi).
3. Qaysi yechim ishlaganini `docs/1c-farazlar.md` 4-qatoriga yozing.

## 5. Farazlarni tekshirish (spec §13) → `docs/1c-farazlar.md`

Har birini TestClaude'da bajaring va natijani (✔/✖) jadvalga yozing. **Biror faraz ✖ — to'xtang**, xabar bering;
spec qayta kelishilmaguncha keyingi tasklarga o'tilmaydi.

1. Sinov `ПеремещениеОС` (filial A → B, bitta AV, qisman soni bilan). Oldin va keyin `/vositalar`: `filial`
   (rekvizit) o'zgarmagan, `qoldiqlar`da A kamaygan, B paydo bo'lgan; `/harakatlar`da ikki qator (chiqim A, kirim B).
2. ПоступлениеОС, СписаниеОС, ВводНачальныхОстатковОС, ПереоценкаОС bo'yicha ham `/harakatlar` qator beradi.
3. `xodimlar` ro'yxati bo'sh emas, `ism`/`filial` to'ldirilgan.
4. 3-bo'lim tekshiruvi (200 va `"versiya":"1.0.0"`; 404 bo'lsa — 4-bo'lim).
5. Kengaytma «Безопасный режим» yoqilgan holda 4 ta endpoint 200 qaytaradi.

Jadval shabloni (`docs/1c-farazlar.md` da tayyor):

| # | Faraz | Tekshiruv usuli | Natija | Izoh |
|---|---|---|---|---|
| 1 | ПеремещениеОС rekvizitni o'zgartirmaydi | ... | ✔ / ✖ | hujjat raqami, AV kodi |
