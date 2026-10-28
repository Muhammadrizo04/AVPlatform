/* Chop etish tugmalari: data-chop="summasiz" — qiymat ustunlari (.qiymat-ustun) bosmaga chiqmaydi (panel.css). */
(function () {
  "use strict";
  document.addEventListener("click", function (e) {
    var tugma = e.target.closest("[data-chop]");
    if (!tugma) return;
    document.body.classList.toggle("chop-summasiz", tugma.dataset.chop === "summasiz");
    window.print();
  });
  window.addEventListener("afterprint", function () {
    document.body.classList.remove("chop-summasiz");
  });
})();
