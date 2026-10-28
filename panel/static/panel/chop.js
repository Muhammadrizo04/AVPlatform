/* Qaydnomalarni chop etish (?chop=…): tugma bosilsa sahifa ko'rinmas iframe'da yuklanadi va chop etish oynasi shu
   sahifada chiqadi — yangi tab ochilmaydi. Chop etish sahifasi to'g'ridan-to'g'ri ochilsa ([data-avto-chop]) — o'zi
   chop etadi; [data-chop] tugmasi — qayta chop etish. */
(function () {
  "use strict";
  var ramka = null;
  document.addEventListener("click", function (e) {
    var havola = e.target.closest("a[data-chop-url]");
    if (havola) {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      if (!ramka) {
        ramka = document.createElement("iframe");
        ramka.title = "Chop etish";
        ramka.setAttribute("aria-hidden", "true");
        ramka.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden";
        document.body.appendChild(ramka);
      }
      ramka.src = havola.href;
      return;
    }
    if (e.target.closest("button[data-chop]")) window.print();
  });
  window.addEventListener("load", function () {
    if (!document.querySelector("[data-avto-chop]")) return;
    window.focus();
    window.print();
  });
})();
