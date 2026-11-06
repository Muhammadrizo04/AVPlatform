/* Qidiruv maydonidagi «×»: matn bor paytda ko'rinadi; bosilsa — so'z o'chadi, natija (data-tozala-natija selektori)
   yopiladi, kursor yana maydonda. Brauzerning o'z mayda «×» belgisi CSS'da yashirilgan (panel.css). */
(function () {
  "use strict";

  function yangila(maydon) {
    var quti = maydon.closest(".qidiruv-quti");
    var tugma = quti && quti.querySelector("[data-tozala]");
    if (tugma) tugma.hidden = !maydon.value;
  }

  document.addEventListener("input", function (e) {
    if (e.target.matches(".qidiruv-quti input")) yangila(e.target);
  });

  document.addEventListener("click", function (e) {
    var tugma = e.target.closest("[data-tozala]");
    if (!tugma) return;
    var maydon = tugma.closest(".qidiruv-quti").querySelector("input");
    maydon.value = "";
    tugma.hidden = true;
    var natija = tugma.dataset.tozalaNatija && document.querySelector(tugma.dataset.tozalaNatija);
    if (natija) natija.innerHTML = "";
    maydon.focus();
  });

  // Sahifa boshqa yo'l bilan tozalaganda (masalan, saqlangach) ham «×» holati to'g'ri bo'lsin
  document.addEventListener("htmx:afterSwap", function () {
    document.querySelectorAll(".qidiruv-quti input").forEach(yangila);
  });
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".qidiruv-quti input").forEach(yangila);
  });
})();
