// AV kartochkasi qo'shimcha maydonlari (vositalar/kartochka.html):
// 1) [data-qatiy-tanlov] — uzun ro'yxatdan qidiruvli tanlov: yozilgan har so'z bo'yicha filtrlanadigan menyu
//    (oddiy tanlov menyusi ko'rinishida; manba — data-royxat dagi datalist). Ro'yxatda yo'q qiymat — xato,
//    forma yuborilmaydi.
// 2) [data-xotira] — Storage: turi + hajmi qatorlari, «Qo'shish» (ko'pi bilan data-maks), qiymat yashirin maydonga.
(function () {
  var XABAR = "Ro'yxatdan tanlang — o'zingiz yozgan qiymat qabul qilinmaydi.";

  function qiymatlar(input) {
    var list = document.getElementById(input.dataset.royxat);
    return list ? Array.prototype.map.call(list.options, function (o) { return o.value; }) : [];
  }

  function tanlovniTekshir(input) {
    var ok = !input.value || qiymatlar(input).indexOf(input.value) !== -1;
    input.setCustomValidity(ok ? "" : XABAR);
    input.classList.toggle("is-invalid", !ok);
  }

  function menyu(input) { return document.getElementById(input.getAttribute("aria-controls")); }

  function yop(input) {
    menyu(input).hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  function faollashtir(input, li) {
    var ul = menyu(input);
    ul.querySelectorAll(".faol").forEach(function (x) { x.classList.remove("faol"); x.setAttribute("aria-selected", "false"); });
    if (!li) return;
    li.classList.add("faol");
    li.setAttribute("aria-selected", "true");
    input.setAttribute("aria-activedescendant", li.id);
    li.scrollIntoView({ block: "nearest" });
  }

  function och(input, hammasi) {
    var ul = menyu(input), sozlar = hammasi ? [] : input.value.toLowerCase().split(/\s+/).filter(Boolean);
    var mos = qiymatlar(input).filter(function (v) {
      var kichik = v.toLowerCase();
      return sozlar.every(function (s) { return kichik.indexOf(s) !== -1; });
    });
    ul.innerHTML = "";
    mos.forEach(function (v, i) {
      var li = document.createElement("li");
      li.id = ul.id + "-" + i;
      li.setAttribute("role", "option");
      li.dataset.qiymat = v;
      li.textContent = v;
      if (v === input.value) li.classList.add("tanlangan");
      ul.appendChild(li);
    });
    if (!mos.length) {
      var bosh = document.createElement("li");
      bosh.className = "bosh";
      bosh.textContent = "Topilmadi — boshqacha yozib ko'ring";
      ul.appendChild(bosh);
    }
    ul.hidden = false;
    input.setAttribute("aria-expanded", "true");
    faollashtir(input, ul.querySelector(".tanlangan") || null);
  }

  function tanla(input, li) {
    input.value = li.dataset.qiymat;
    tanlovniTekshir(input);
    yop(input);
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function xotiraYangila(blok) {
    var qatorlar = blok.querySelectorAll("[data-xotira-qator]"), qismlar = [];
    qatorlar.forEach(function (q) {
      var tur = q.querySelector("[data-xotira-tur]"), hajm = q.querySelector("[data-xotira-hajm]");
      var chala = !!tur.value !== !!hajm.value;
      tur.setCustomValidity(chala && !tur.value ? "Turini tanlang." : "");
      hajm.setCustomValidity(chala && !hajm.value ? "Hajmini tanlang." : "");
      if (tur.value && hajm.value) qismlar.push(tur.value + " " + hajm.value);
    });
    blok.querySelector("[data-xotira-qiymat]").value = qismlar.join(" + ");
    blok.querySelector("[data-xotira-qosh]").hidden = qatorlar.length >= Number(blok.dataset.maks || 4);
  }

  document.addEventListener("input", function (e) {
    if (!e.target.matches || !e.target.matches("[data-qatiy-tanlov]")) return;
    tanlovniTekshir(e.target);
    och(e.target, false);
  });
  document.addEventListener("focusin", function (e) {
    if (e.target.matches && e.target.matches("[data-qatiy-tanlov]")) och(e.target, true);
  });
  document.addEventListener("focusout", function (e) {
    if (e.target.matches && e.target.matches("[data-qatiy-tanlov]")) { tanlovniTekshir(e.target); yop(e.target); }
  });
  document.addEventListener("keydown", function (e) {
    var input = e.target;
    if (!input.matches || !input.matches("[data-qatiy-tanlov]")) return;
    var ul = menyu(input);
    if (e.key === "Escape") { yop(input); return; }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (ul.hidden) och(input, true);
      var variantlar = Array.prototype.slice.call(ul.querySelectorAll("[role=option]"));
      var i = variantlar.indexOf(ul.querySelector(".faol"));
      i = e.key === "ArrowDown" ? Math.min(i + 1, variantlar.length - 1) : Math.max(i - 1, 0);
      faollashtir(input, variantlar[i]);
    } else if (e.key === "Enter" && !ul.hidden) {
      var faol = ul.querySelector(".faol") || (ul.querySelectorAll("[role=option]").length === 1 && ul.querySelector("[role=option]"));
      if (faol) { e.preventDefault(); tanla(input, faol); }
    }
  });
  // mousedown — input fokusni yo'qotib menyu yopilishidan oldin
  document.addEventListener("mousedown", function (e) {
    var li = e.target.closest && e.target.closest(".tanlov-menyu [role=option]");
    if (!li) return;
    e.preventDefault();
    tanla(document.querySelector('[aria-controls="' + li.parentNode.id + '"]'), li);
  });

  document.addEventListener("change", function (e) {
    if (!e.target.matches) return;
    var blok = e.target.closest("[data-xotira]");
    if (blok) xotiraYangila(blok);
  });
  document.addEventListener("click", function (e) {
    var tugma = e.target.closest && e.target.closest("[data-xotira-qosh], [data-xotira-ochir]");
    if (!tugma) return;
    var blok = tugma.closest("[data-xotira]");
    var qatorlar = blok.querySelectorAll("[data-xotira-qator]");
    if (tugma.matches("[data-xotira-qosh]")) {
      var yangi = qatorlar[0].cloneNode(true);
      yangi.querySelectorAll("select").forEach(function (s) { s.value = ""; });
      tugma.before(yangi);
      yangi.querySelector("select").focus();
    } else if (qatorlar.length > 1) {
      tugma.closest("[data-xotira-qator]").remove();
    } else {
      qatorlar[0].querySelectorAll("select").forEach(function (s) { s.value = ""; });
    }
    xotiraYangila(blok);
  });
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-qatiy-tanlov]").forEach(tanlovniTekshir);
    document.querySelectorAll("[data-xotira]").forEach(xotiraYangila);
  });
})();
