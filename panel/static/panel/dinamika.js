// Bosh sahifa: AV summasi dinamikasi grafigi (panel/_dinamika.html, ma'lumot — panel/dinamika.py `_grafik`).
// Grafik konteyner kengligida chiziladi (yozuvlar har ekranda bir xil o'lchamda), o'lcham o'zgarsa qayta chiziladi.
// Hover: kursor chizig'i, nuqtalar va tooltip. HTMX bo'lakni almashtirsa ham ishlaydi.
(function () {
  var NS = "http://www.w3.org/2000/svg";
  var BALANDLIK = 300, CHAP = 64, ONG = 12, TEPA = 12, PAST = 28;

  function el(nom, attr, ota) {
    var e = document.createElementNS(NS, nom);
    for (var k in attr) e.setAttribute(k, attr[k]);
    if (ota) ota.appendChild(e);
    return e;
  }

  function malumot(blok) {
    var manba = blok.closest(".dinamika").querySelector("#dinamika-malumot");
    return manba ? JSON.parse(manba.textContent) : null;
  }

  function chiz(blok) {
    var m = malumot(blok), svg = blok.querySelector("svg");
    if (!m || !m.oylar.length) return;
    var kenglik = Math.max(blok.clientWidth, 280), n = m.oylar.length;
    var eni = kenglik - CHAP - ONG, boyi = BALANDLIK - TEPA - PAST, yuqori = m.y[m.y.length - 1].q || 1;
    var x = function (i) { return CHAP + (n > 1 ? eni * i / (n - 1) : eni / 2); };
    var y = function (q) { return TEPA + boyi - Math.max(q, 0) / yuqori * boyi; };
    svg.setAttribute("viewBox", "0 0 " + kenglik + " " + BALANDLIK);
    svg.setAttribute("width", kenglik);
    svg.setAttribute("height", BALANDLIK);
    svg.textContent = "";

    m.y.forEach(function (b) {
      el("line", { "class": "tor", x1: CHAP, x2: kenglik - ONG, y1: y(b.q), y2: y(b.q) }, svg);
      el("text", { "class": "o-q y", x: CHAP - 8, y: y(b.q) }, svg).textContent = b.matn;
    });
    // X o'qi: yozuvlar ustma-ust tushmasin — har ~90px ga bitta, oxirgisi doim
    var qadam = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(eni / 90))));
    m.oylar.forEach(function (oy, i) {
      if (i % qadam && i !== n - 1) return;
      if (i === n - 1 && i % qadam && x(i) - x(i - i % qadam) < 70) return;
      el("text", { "class": "o-q x", x: x(i), y: TEPA + boyi + 20 }, svg).textContent = oy;
    });
    el("line", { "class": "kursor", x1: 0, x2: 0, y1: TEPA, y2: TEPA + boyi, visibility: "hidden" }, svg);
    m.seriyalar.forEach(function (s) {
      el("polyline", {
        "class": "chiziq", stroke: s.rang,
        points: s.q.map(function (q, i) { return x(i).toFixed(1) + "," + y(q).toFixed(1); }).join(" "),
      }, svg);
    });
    blok._grafik = { m: m, x: x, y: y, kenglik: kenglik };
  }

  function yashir(blok) {
    var svg = blok.querySelector("svg"), kursor = svg.querySelector(".kursor");
    if (kursor) kursor.setAttribute("visibility", "hidden");
    svg.querySelectorAll(".nuqta").forEach(function (n) { n.remove(); });
    blok.querySelector(".dinamika-tooltip").hidden = true;
  }

  function korsat(blok, e) {
    var g = blok._grafik;
    if (!g) return;
    var svg = blok.querySelector("svg"), m = g.m;
    var px = e.clientX - svg.getBoundingClientRect().left, i = 0;
    for (var j = 1; j < m.oylar.length; j++) if (Math.abs(g.x(j) - px) < Math.abs(g.x(i) - px)) i = j;

    var kursor = svg.querySelector(".kursor");
    kursor.setAttribute("x1", g.x(i));
    kursor.setAttribute("x2", g.x(i));
    kursor.setAttribute("visibility", "visible");
    svg.querySelectorAll(".nuqta").forEach(function (n) { n.remove(); });
    m.seriyalar.forEach(function (s) {
      el("circle", { "class": "nuqta", cx: g.x(i), cy: g.y(s.q[i]), r: 4.5, fill: s.rang }, svg);
    });

    var tip = blok.querySelector(".dinamika-tooltip");
    tip.textContent = "";
    var sarlavha = document.createElement("b");
    sarlavha.textContent = m.oylar[i];
    tip.appendChild(sarlavha);
    m.seriyalar.slice().sort(function (a, b) { return b.q[i] - a.q[i]; }).forEach(function (s) {
      var qator = document.createElement("div"), belgi = document.createElement("i");
      var nomi = document.createElement("span"), qiymat = document.createElement("strong");
      belgi.style.background = s.rang;
      nomi.textContent = s.nomi;
      qiymat.textContent = s.matn[i];
      qator.append(belgi, nomi, qiymat);
      tip.appendChild(qator);
    });
    tip.hidden = false;
    var chapda = g.x(i) > g.kenglik / 2;  // tooltip kursorning bo'sh tomonida
    tip.style.left = chapda ? "" : g.x(i) + 14 + "px";
    tip.style.right = chapda ? g.kenglik - g.x(i) + 14 + "px" : "";
  }

  var kuzatuvchi = window.ResizeObserver ? new ResizeObserver(function (yozuvlar) {
    yozuvlar.forEach(function (y) {
      if (y.target._grafik && Math.abs(y.target.clientWidth - y.target._grafik.kenglik) < 2) return;
      chiz(y.target);
    });
  }) : null;

  function boshla(ildiz) {
    (ildiz || document).querySelectorAll("[data-dinamika]").forEach(function (blok) {
      chiz(blok);
      if (kuzatuvchi) kuzatuvchi.observe(blok);
    });
  }

  document.addEventListener("DOMContentLoaded", function () { boshla(); });
  document.addEventListener("htmx:afterSwap", function (e) { boshla(e.detail.elt.parentNode || document); });
  document.addEventListener("mousemove", function (e) {
    var blok = e.target.closest && e.target.closest("[data-dinamika]");
    if (blok) korsat(blok, e);
  });
  document.addEventListener("mouseout", function (e) {
    var blok = e.target.closest && e.target.closest("[data-dinamika]");
    if (blok && !blok.contains(e.relatedTarget)) yashir(blok);
  });
})();
