// 1) Oy tanlagich (panel/_oy_tanlov.html): maydonning istalgan joyi bosilsa — yil (‹ ›) va 12 oy paneli;
//    data-min / data-max dan tashqaridagi oylar o'chiq. Tanlansa yashirin maydonga YYYY-MM yoziladi va forma yuboriladi.
// 2) Filiallar ro'yxati (data-filial-tanlov): belgilash yopmaydi; «Hammasi» / «Tozalash»; ro'yxat yopilganda
//    tanlov o'zgargan bo'lsa forma yuboriladi. Tashqariga bosish yoki Escape — ikkalasini ham yopadi.
(function () {
  var QISQA = ["Yan", "Fev", "Mar", "Apr", "May", "Iyun", "Iyul", "Avg", "Sen", "Okt", "Noy", "Dek"];
  var TOLIQ = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];

  function yuborish(forma) {
    if (forma.requestSubmit) forma.requestSubmit(); else forma.submit();
  }

  function oyYop(blok) {
    blok.querySelector(".oy-tanlov-panel").hidden = true;
    blok.querySelector(".oy-tanlov-tugma").setAttribute("aria-expanded", "false");
  }

  function oyChiz(blok, yil) {
    var panel = blok.querySelector(".oy-tanlov-panel");
    var qiymat = blok.querySelector("input[type=hidden]").value;
    var min = blok.dataset.min || "0000-00", max = blok.dataset.max || "9999-99";
    panel.dataset.yil = yil;
    panel.textContent = "";

    var bosh = document.createElement("div");
    bosh.className = "oy-tanlov-bosh";
    var oldingi = document.createElement("button"), keyingi = document.createElement("button"), sarlavha = document.createElement("b");
    oldingi.type = keyingi.type = "button";
    oldingi.className = keyingi.className = "oy-tanlov-yil";
    oldingi.textContent = "‹";
    keyingi.textContent = "›";
    oldingi.setAttribute("aria-label", "Oldingi yil");
    keyingi.setAttribute("aria-label", "Keyingi yil");
    oldingi.disabled = String(yil - 1) + "-12" < min;
    keyingi.disabled = String(yil + 1) + "-01" > max;
    oldingi.dataset.yilQadam = -1;
    keyingi.dataset.yilQadam = 1;
    sarlavha.textContent = yil;
    bosh.append(oldingi, sarlavha, keyingi);
    panel.appendChild(bosh);

    var tor = document.createElement("div");
    tor.className = "oy-tanlov-tor";
    QISQA.forEach(function (nom, i) {
      var oy = yil + "-" + String(i + 1).padStart(2, "0");
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = nom;
      b.dataset.oy = oy;
      b.disabled = oy < min || oy > max;
      if (oy === qiymat) { b.classList.add("tanlangan"); b.setAttribute("aria-pressed", "true"); }
      tor.appendChild(b);
    });
    panel.appendChild(tor);
  }

  function oyOch(blok) {
    document.querySelectorAll("[data-oy-tanlov]").forEach(function (b) { if (b !== blok) oyYop(b); });
    var qiymat = blok.querySelector("input[type=hidden]").value;
    oyChiz(blok, Number(qiymat.slice(0, 4)) || new Date().getFullYear());
    blok.querySelector(".oy-tanlov-panel").hidden = false;
    blok.querySelector(".oy-tanlov-tugma").setAttribute("aria-expanded", "true");
    var tanlangan = blok.querySelector(".oy-tanlov-tor .tanlangan") || blok.querySelector(".oy-tanlov-tor button:not(:disabled)");
    if (tanlangan) tanlangan.focus();
  }

  // Tanlov serverdan kelgan holatdan (defaultChecked) farq qiladimi
  function filialOzgardi(details) {
    return Array.prototype.some.call(details.querySelectorAll("input[name=f]"), function (c) { return c.checked !== c.defaultChecked; });
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    var blok = t.closest && t.closest("[data-oy-tanlov]");
    if (blok) {
      if (t.closest(".oy-tanlov-tugma")) {
        if (blok.querySelector(".oy-tanlov-panel").hidden) oyOch(blok); else oyYop(blok);
      } else if (t.dataset.yilQadam) {
        oyChiz(blok, Number(blok.querySelector(".oy-tanlov-panel").dataset.yil) + Number(t.dataset.yilQadam));
      } else if (t.dataset.oy && !t.disabled) {
        var oy = t.dataset.oy;
        blok.querySelector("input[type=hidden]").value = oy;
        blok.querySelector(".oy-tanlov-tugma span").textContent = TOLIQ[Number(oy.slice(5)) - 1] + " " + oy.slice(0, 4);
        oyYop(blok);
        yuborish(blok.closest("form"));
      }
    }
    document.querySelectorAll("[data-oy-tanlov]").forEach(function (b) { if (!b.contains(t)) oyYop(b); });

    var details = t.closest && t.closest("[data-filial-tanlov]");
    if (details && (t.matches("[data-filial-hammasi]") || t.matches("[data-filial-tozala]"))) {
      var belgi = t.matches("[data-filial-hammasi]");
      details.querySelectorAll("input[name=f]").forEach(function (c) { c.checked = belgi; });
    }
    document.querySelectorAll("[data-filial-tanlov][open]").forEach(function (d) { if (!d.contains(t)) d.open = false; });
  });

  // Ro'yxat yopilganda tanlov o'zgargan bo'lsa — grafik yangilanadi
  document.addEventListener("toggle", function (e) {
    var d = e.target;
    if (d.matches && d.matches("[data-filial-tanlov]") && !d.open && filialOzgardi(d)) yuborish(d.closest("form"));
  }, true);

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    document.querySelectorAll("[data-oy-tanlov]").forEach(function (b) {
      if (!b.querySelector(".oy-tanlov-panel").hidden) { oyYop(b); b.querySelector(".oy-tanlov-tugma").focus(); }
    });
    document.querySelectorAll("[data-filial-tanlov][open]").forEach(function (d) { d.open = false; });
  });
})();
