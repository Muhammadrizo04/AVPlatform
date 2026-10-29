// «Bir sahifada N qator» (panel/_sahifalash.html): qiymat o'zgarsa forma yuboriladi (Enter shart emas).
document.addEventListener("change", function (e) {
  var input = e.target;
  if (!input.matches || !input.matches("form[data-sahifa-hajmi] input[name=hajm]")) return;
  if (input.value && input.checkValidity()) input.form.requestSubmit();
});
