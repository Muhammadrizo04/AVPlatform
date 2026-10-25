/* Revizor skan ekrani (kutubxonasiz): BarcodeDetector + orqa kamera, −/+ tugmalar, kartochkani yopish, qolganlar filtri.
   Kamera faqat xavfsiz kontekstda (HTTPS yoki localhost); aks holda tugma yashirin, [data-xavfsiz] izohi ko'rinadi. */
(function () {
  "use strict";
  var quti = document.getElementById("kamera");
  var tugma = document.getElementById("kamera-tugma");
  var video = document.getElementById("kamera-video");
  var izoh = quti && quti.querySelector("[data-xavfsiz]");
  var oqim = null, taymer = null;

  function toxtat() {
    if (taymer) { clearInterval(taymer); taymer = null; }
    if (oqim) { oqim.getTracks().forEach(function (t) { t.stop(); }); oqim = null; }
    video.hidden = true;
    tugma.textContent = "Kamera — QR skanerlash";
  }

  function topildi(matn) {
    toxtat();
    matn = String(matn || "").split(String.fromCharCode(0)).join("");  // NUL bayt — server 400 qaytaradi
    var url = quti.dataset.topish + "?qr=" + encodeURIComponent(matn) + "&bolim=" + encodeURIComponent(quti.dataset.bolim);
    htmx.ajax("GET", url, "#kartochka");
  }

  function izohKorsat(matn) {
    if (matn) izoh.textContent = matn;
    izoh.hidden = false;
  }

  function boshla() {
    var detektor;
    try {
      detektor = new BarcodeDetector({ formats: ["qr_code"] });
    } catch (e) {
      toxtat();
      tugma.hidden = true;
      izohKorsat("Bu brauzer QR kodni o'qiy olmaydi — inv. raqamni kiriting");
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }).then(function (s) {
      oqim = s;
      video.srcObject = s;
      video.hidden = false;
      tugma.textContent = "Kamerani to'xtatish";
      return video.play();
    }).then(function () {
      var band = false;
      taymer = setInterval(function () {
        if (band || !oqim) return;
        band = true;
        detektor.detect(video).then(function (natija) {
          if (natija.length && oqim) topildi(natija[0].rawValue);
        }).catch(function () {}).then(function () { band = false; });
      }, 300);
    }).catch(function () {
      toxtat();
      izohKorsat("Kameraga ruxsat berilmadi — inv. raqamni kiriting");
    });
  }

  var qidiruv = document.getElementById("qidiruv");
  var kameraYoq = true;  // kamera tugmasi ko'rinmaguncha — klaviatura / USB skaner bilan ishlanadi
  // Faqat sichqonchali qurilmada (kompyuter) avtofokus: telefonda klaviatura o'z-o'zidan ochilmasin
  var klaviatura = !!(window.matchMedia && window.matchMedia("(pointer: fine)").matches);

  function qidiruvgaQayt() {
    // Kamerasiz (kompyuter) rejimda kursor doim qidiruvda: inv. raqam yoki USB skaner -> Enter
    if (klaviatura && kameraYoq && qidiruv) { qidiruv.value = ""; qidiruv.focus(); }
  }

  // HTTPS bor, lekin brauzerda QR o'quvchi yo'q (masalan, kompyuterdagi Chrome/Edge) — izoh aniqroq
  if (izoh && window.isSecureContext) {
    izoh.textContent = "Bu brauzerda kamera bilan skanerlash yo'q — inv. raqamni kiriting yoki USB skanerdan foydalaning";
  }
  qidiruvgaQayt();

  // Tugma faqat brauzer `qr_code` formatini qo'llasa ko'rinadi; aks holda HTTPS/inv. raqam izohi qoladi
  if (quti && "BarcodeDetector" in window && window.isSecureContext && navigator.mediaDevices) {
    Promise.resolve().then(function () {
      return BarcodeDetector.getSupportedFormats ? BarcodeDetector.getSupportedFormats() : [];
    }).then(function (formatlar) {
      if (formatlar.indexOf("qr_code") === -1) return;
      kameraYoq = false;
      tugma.hidden = false;
      izoh.hidden = true;
      tugma.addEventListener("click", function () { if (oqim) toxtat(); else boshla(); });
    }).catch(function () {});
  }

  document.addEventListener("click", function (e) {
    var qadam = e.target.closest("[data-qadam]");
    if (qadam) {
      var maydon = qadam.parentNode.querySelector("input[name=soni]");
      var joriy = parseFloat((maydon.value || "0").replace(",", ".")) || 0;
      maydon.value = String(Math.max(1, joriy + Number(qadam.dataset.qadam)));
    } else if (e.target.closest("[data-yop]")) {
      document.getElementById("kartochka").innerHTML = "";
    }
  });

  document.addEventListener("keydown", function (e) {
    // Esc — ochiq kartochkani yopib, qidiruvga qaytish
    var k = document.getElementById("kartochka");
    if (e.key === "Escape" && k && k.innerHTML.trim()) { k.innerHTML = ""; qidiruvgaQayt(); }
  });

  // МОЛ biriktirish: xodimni ism bo'yicha qidirish (ko'pi bilan 15 ta natija), tanlangani yashirin maydonga
  var XODIM_NATIJALARI = 15;
  document.addEventListener("input", function (e) {
    if (!e.target.matches("[data-xodim-qidir]")) return;
    var forma = e.target.closest("form");
    var soz = e.target.value.trim().toLowerCase();
    var korsatildi = 0;
    forma.querySelectorAll("[data-xodim-ism]").forEach(function (li) {
      var mos = soz.length >= 2 && korsatildi < XODIM_NATIJALARI && li.dataset.xodimIsm.indexOf(soz) !== -1;
      li.hidden = !mos;
      if (mos) korsatildi++;
    });
    var izoh = forma.querySelector("[data-xodim-izoh]");
    izoh.textContent = soz.length < 2 ? "Kamida 2 harf yozing." : (korsatildi ? "" : "Bunday xodim topilmadi.");
  });
  document.addEventListener("click", function (e) {
    var tugma = e.target.closest("[data-xodim]");
    var bekor = e.target.closest("[data-xodim-bekor]");
    if (!tugma && !bekor) return;
    var forma = (tugma || bekor).closest("form");
    var chip = forma.querySelector("[data-xodim-tanlangan]");
    var qidir = forma.querySelector("[data-xodim-qidir]");
    forma.querySelector("[data-xodim-id]").value = tugma ? tugma.dataset.xodim : "";
    chip.hidden = !tugma;
    chip.innerHTML = "";
    if (tugma) {
      var nom = document.createElement("b");
      nom.textContent = tugma.dataset.xodimNomi;
      var x = document.createElement("button");
      x.type = "button"; x.className = "m-ikon"; x.dataset.xodimBekor = "1"; x.setAttribute("aria-label", "Boshqa xodim"); x.textContent = "×";
      chip.append(nom, x);
    }
    qidir.hidden = !!tugma;
    qidir.value = "";
    forma.querySelectorAll("[data-xodim-ism]").forEach(function (li) { li.hidden = true; });
    forma.querySelector("[data-xodim-izoh]").textContent = tugma ? "" : "Kamida 2 harf yozing.";
    if (!tugma) qidir.focus();
  });

  document.addEventListener("input", function (e) {
    if (!e.target.matches("[data-qolgan-filtr]")) return;
    var soz = e.target.value.trim().toLowerCase();
    document.querySelectorAll("[data-qolgan]").forEach(function (li) {
      li.hidden = soz !== "" && li.dataset.qolgan.indexOf(soz) === -1;
    });
  });

  document.addEventListener("htmx:afterSwap", function (e) {
    if (e.detail.target.id !== "kartochka") return;
    var soni = e.detail.target.querySelector("input[name=soni]");
    if (soni && klaviatura) soni.select();  // kartochka ochildi: son tayyor, Enter — saqlash
    if (e.detail.target.querySelector(".m-ok")) {
      qidiruvgaQayt();
      setTimeout(function () {
        var k = document.getElementById("kartochka");
        if (k.querySelector(".m-ok")) k.innerHTML = "";
      }, 2500);
    }
  });
})();
