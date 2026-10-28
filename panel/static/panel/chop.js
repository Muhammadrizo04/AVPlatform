/* Qaydnomalarni chop etish rejimi (?chop=…): sahifa ochilgach chop etish oynasi o'zi chiqadi; [data-chop] — qayta. */
(function () {
  "use strict";
  document.addEventListener("click", function (e) {
    if (e.target.closest("button[data-chop]")) window.print();
  });
  window.addEventListener("load", function () {
    if (document.querySelector("[data-avto-chop]")) window.print();
  });
})();
