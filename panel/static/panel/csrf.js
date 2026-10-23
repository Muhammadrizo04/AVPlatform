/* HTMX so'rovlari uchun CSRF tokeni har so'rovda cookie'dan olinadi: boshqa oynada qayta kirilgandan keyin
   (Django tokenni yangilaydi) ochiq turgan eski sahifa ham ishlayveradi. Baribir rad etilsa — Django'ning texnik
   sahifasi o'rniga tushunarli xabar va sahifa qayta yuklanadi. */
(function () {
  "use strict";

  function token() {
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  document.addEventListener("htmx:configRequest", function (e) {
    var t = token();
    if (t) e.detail.headers["X-CSRFToken"] = t;
  });

  document.addEventListener("htmx:beforeSwap", function (e) {
    var xhr = e.detail.xhr;
    if (xhr.status !== 403 || xhr.responseText.indexOf("CSRF") === -1) return;
    e.detail.shouldSwap = false;
    window.alert("Sahifa eskirgan: tizimga boshqa oynada qayta kirilgan bo'lishi mumkin. "
      + "Sahifa yangilanadi — amalni qaytadan bajaring.");
    window.location.reload();
  });
})();
