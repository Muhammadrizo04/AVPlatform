// Yuqori paneldagi sana va soat: server vaqtidan hisoblanadi (kompyuter soati noto'g'ri bo'lsa ham to'g'ri chiqadi).
(function () {
  "use strict";

  const joy = document.getElementById("av-vaqt");
  if (!joy) return;

  const farq = Number(joy.dataset.hozir) - Date.now();
  const zona = Number(joy.dataset.zona) * 60000;
  const oylar = joy.dataset.oylar.split(",");
  const kunlar = joy.dataset.kunlar.split(",");
  const soat = joy.querySelector("[data-soat]");
  const sana = joy.querySelector("[data-sana]");
  const ikki = (n) => String(n).padStart(2, "0");

  function yangila() {
    const v = new Date(Date.now() + farq + zona); // getUTC* endi mahalliy (Toshkent) vaqtni beradi
    soat.textContent = `${ikki(v.getUTCHours())}:${ikki(v.getUTCMinutes())}`;
    sana.textContent = `${v.getUTCDate()}-${oylar[v.getUTCMonth()]}, ${kunlar[(v.getUTCDay() + 6) % 7]}`;
    joy.dateTime = v.toISOString().slice(0, 16);
  }

  yangila();
  setInterval(yangila, 10000);
})();
