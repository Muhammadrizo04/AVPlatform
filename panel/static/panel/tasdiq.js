/* Tasdiqlash oynasi: brauzerning tizim confirm() o'rniga ekran o'rtasidagi o'z oynamiz (<dialog>, kutubxonasiz).
   Oddiy forma: <form data-tasdiq="Matn" [data-tasdiq-tugma="Yopish"] [data-tasdiq-xavfli]>;
   matndagi {n} — forma ichida [data-tasdiq-sanoq] selektoriga mos elementlar soni.
   HTMX: hx-confirm="Matn" ham shu oyna bilan so'raladi. */
(function () {
  "use strict";
  var oyna = null;

  function yarat() {
    oyna = document.createElement("dialog");
    oyna.className = "tasdiq-oyna";
    oyna.setAttribute("aria-labelledby", "tasdiq-sarlavha");
    oyna.innerHTML =
      '<h2 id="tasdiq-sarlavha">Tasdiqlang</h2><p data-matn></p>' +
      '<div class="tasdiq-tugmalar"><button type="button" class="t-yoq" data-yoq>Bekor qilish</button>' +
      '<button type="button" class="t-ha" data-ha>Tasdiqlash</button></div>';
    document.body.appendChild(oyna);
    oyna.addEventListener("click", function (e) {
      if (e.target === oyna) oyna.close("yoq");  // fonga bosish — bekor
    });
    oyna.querySelector("[data-yoq]").addEventListener("click", function () { oyna.close("yoq"); });
    oyna.querySelector("[data-ha]").addEventListener("click", function () { oyna.close("ha"); });
  }

  function sora(matn, tugma, xavfli, davomi) {
    if (!oyna) yarat();
    if (!oyna.showModal) { if (window.confirm(matn)) davomi(); return; }  // juda eski brauzer
    oyna.querySelector("[data-matn]").textContent = matn;
    var ha = oyna.querySelector("[data-ha]");
    ha.textContent = tugma || "Tasdiqlash";
    ha.className = xavfli ? "t-ha t-xavfli" : "t-ha";
    oyna.returnValue = "";
    oyna.onclose = function () { if (oyna.returnValue === "ha") davomi(); };
    oyna.showModal();
    ha.focus();
  }

  document.addEventListener("submit", function (e) {
    var forma = e.target;
    if (!forma.dataset || forma.dataset.tasdiq === undefined) return;
    if (forma._tasdiqlandi) { forma._tasdiqlandi = false; return; }
    e.preventDefault();
    e.stopImmediatePropagation();
    var matn = forma.dataset.tasdiq;
    if (forma.dataset.tasdiqSanoq) matn = matn.replace("{n}", forma.querySelectorAll(forma.dataset.tasdiqSanoq).length);
    var yuboruvchi = e.submitter;
    sora(matn, forma.dataset.tasdiqTugma, forma.dataset.tasdiqXavfli !== undefined, function () {
      forma._tasdiqlandi = true;
      if (forma.requestSubmit) forma.requestSubmit(yuboruvchi || undefined); else forma.submit();
    });
  }, true);

  document.addEventListener("htmx:confirm", function (e) {
    if (!e.detail.question) return;
    e.preventDefault();
    sora(e.detail.question, null, false, function () { e.detail.issueRequest(true); });
  });
})();
