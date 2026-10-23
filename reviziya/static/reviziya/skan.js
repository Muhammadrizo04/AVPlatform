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
    var url = quti.dataset.topish + "?qr=" + encodeURIComponent(matn) + "&bolim=" + encodeURIComponent(quti.dataset.bolim);
    htmx.ajax("GET", url, "#kartochka");
  }

  function boshla() {
    var detektor = new BarcodeDetector({ formats: ["qr_code"] });
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
      izoh.textContent = "Kameraga ruxsat berilmadi — inv. raqamni kiriting";
      izoh.hidden = false;
    });
  }

  if (quti && "BarcodeDetector" in window && window.isSecureContext && navigator.mediaDevices) {
    tugma.hidden = false;
    izoh.hidden = true;
    tugma.addEventListener("click", function () { if (oqim) toxtat(); else boshla(); });
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

  document.addEventListener("input", function (e) {
    if (!e.target.matches("[data-qolgan-filtr]")) return;
    var soz = e.target.value.trim().toLowerCase();
    document.querySelectorAll("[data-qolgan]").forEach(function (li) {
      li.hidden = soz !== "" && li.dataset.qolgan.indexOf(soz) === -1;
    });
  });

  document.addEventListener("htmx:afterSwap", function (e) {
    if (e.detail.target.id === "kartochka" && e.detail.target.querySelector(".m-ok")) {
      setTimeout(function () {
        var k = document.getElementById("kartochka");
        if (k.querySelector(".m-ok")) k.innerHTML = "";
      }, 2500);
    }
  });
})();
