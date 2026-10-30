// Bosh sahifa: AV summasi dinamikasi grafigi (panel/_dinamika.html, ma'lumot — panel/dinamika.py `_grafik`).
// Grafik konteyner kengligida chiziladi (yozuvlar har ekranda bir xil o'lchamda), o'lcham o'zgarsa qayta chiziladi.
// Chiziq oxirida qiymat yozuvi; «Umumiy ko'rish» da chiziq ostida yengil soha. Hover: kursor, nuqtalar, tooltip.
// Legend: ustiga kelinsa shu chiziq ajraladi, bosilsa yashiriladi/ko'rsatiladi. HTMX almashtirsa ham ishlaydi.
(function () {
  var NS = "http://www.w3.org/2000/svg";
  var BALANDLIK = 320, CHAP = 64, ONG = 76, TEPA = 14, PAST = 30, YORLIQ_ORASI = 15;

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
    var yashirin = blok._yashirin || (blok._yashirin = {});
    var kenglik = Math.max(blok.clientWidth, 300), n = m.oylar.length;
    var eni = kenglik - CHAP - ONG, boyi = BALANDLIK - TEPA - PAST, yuqori = m.y[m.y.length - 1].q || 1;
    var x = function (i) { return CHAP + (n > 1 ? eni * i / (n - 1) : eni / 2); };
    var y = function (q) { return TEPA + boyi - Math.max(q, 0) / yuqori * boyi; };
    svg.setAttribute("viewBox", "0 0 " + kenglik + " " + BALANDLIK);
    svg.setAttribute("width", kenglik);
    svg.setAttribute("height", BALANDLIK);
    svg.textContent = "";

    // To'r va o'qlar
    m.y.forEach(function (b, i) {
      el("line", { "class": i ? "tor" : "asos", x1: CHAP, x2: kenglik - ONG, y1: y(b.q), y2: y(b.q) }, svg);
      el("text", { "class": "o-q y", x: CHAP - 10, y: y(b.q) }, svg).textContent = b.matn;
    });
    var qadam = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(eni / 90))));
    m.oylar.forEach(function (oy, i) {
      if (i % qadam && i !== n - 1) return;
      if (i === n - 1 && i % qadam && x(i) - x(i - i % qadam) < 70) return;
      el("line", { "class": "belgi", x1: x(i), x2: x(i), y1: TEPA + boyi, y2: TEPA + boyi + 4 }, svg);
      el("text", { "class": "o-q x", x: x(i), y: TEPA + boyi + 20 }, svg).textContent = oy;
    });
    el("line", { "class": "kursor", x1: 0, x2: 0, y1: TEPA, y2: TEPA + boyi, visibility: "hidden" }, svg);

    // Chiziqlar (umumiy ko'rishda ostida soha)
    var oxirlar = [];
    m.seriyalar.forEach(function (s, si) {
      if (yashirin[si]) return;
      var g = el("g", { "class": "seriya", "data-seriya": si }, svg);
      var nuqtalar = s.q.map(function (q, i) { return x(i).toFixed(1) + "," + y(q).toFixed(1); });
      if (m.umumiy) {
        var id = "dinamika-soha-" + si;
        var grad = el("linearGradient", { id: id, x1: 0, x2: 0, y1: 0, y2: 1 }, el("defs", {}, g));
        el("stop", { offset: "0%", "stop-color": s.rang, "stop-opacity": 0.22 }, grad);
        el("stop", { offset: "100%", "stop-color": s.rang, "stop-opacity": 0.02 }, grad);
        el("polygon", { "class": "soha", fill: "url(#" + id + ")",
          points: x(0) + "," + (TEPA + boyi) + " " + nuqtalar.join(" ") + " " + x(n - 1) + "," + (TEPA + boyi) }, g);
      }
      el("polyline", { "class": "chiziq" + (m.umumiy ? " qalin" : ""), stroke: s.rang, points: nuqtalar.join(" ") }, g);
      el("circle", { "class": "oxiri", cx: x(n - 1), cy: y(s.q[n - 1]), r: 3.5, fill: s.rang }, g);
      oxirlar.push({ si: si, y: y(s.q[n - 1]), matn: s.matn[n - 1], g: g });
    });

    // Oxirgi qiymat yozuvlari: ustma-ust tushmasin (yuqoridan pastga, kamida YORLIQ_ORASI)
    oxirlar.sort(function (a, b) { return a.y - b.y; });
    var oldingi = -Infinity;
    oxirlar.forEach(function (o) {
      var ty = Math.min(Math.max(o.y, oldingi + YORLIQ_ORASI), TEPA + boyi);
      oldingi = ty;
      el("text", { "class": "oxiri-matn", x: x(n - 1) + 8, y: ty }, o.g).textContent = o.matn;
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
    var svg = blok.querySelector("svg"), m = g.m, yashirin = blok._yashirin || {};
    var px = e.clientX - svg.getBoundingClientRect().left, i = 0;
    for (var j = 1; j < m.oylar.length; j++) if (Math.abs(g.x(j) - px) < Math.abs(g.x(i) - px)) i = j;
    var korinadi = m.seriyalar.filter(function (s, si) { return !yashirin[si]; });
    if (!korinadi.length) return;

    var kursor = svg.querySelector(".kursor");
    kursor.setAttribute("x1", g.x(i));
    kursor.setAttribute("x2", g.x(i));
    kursor.setAttribute("visibility", "visible");
    svg.querySelectorAll(".nuqta").forEach(function (n) { n.remove(); });
    korinadi.forEach(function (s) {
      el("circle", { "class": "nuqta", cx: g.x(i), cy: g.y(s.q[i]), r: 5, fill: s.rang }, svg);
    });

    var tip = blok.querySelector(".dinamika-tooltip");
    tip.textContent = "";
    var sarlavha = document.createElement("b");
    sarlavha.textContent = m.oylar[i];
    tip.appendChild(sarlavha);
    korinadi.slice().sort(function (a, b) { return b.q[i] - a.q[i]; }).forEach(function (s) {
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

  // Legend: ustiga kelinsa — shu chiziq ajraladi, qolganlari xiralashadi
  function fokus(karta, si) {
    var svg = karta.querySelector("[data-dinamika] svg");
    if (!svg) return;
    svg.classList.toggle("fokusda", si !== null);
    svg.querySelectorAll(".seriya").forEach(function (g) { g.classList.toggle("faol", g.dataset.seriya === si); });
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
  document.addEventListener("mouseover", function (e) {
    var b = e.target.closest && e.target.closest(".dinamika-legend [data-seriya]");
    if (b && b.getAttribute("aria-pressed") === "true") fokus(b.closest(".dinamika"), b.dataset.seriya);
  });
  document.addEventListener("mouseout", function (e) {
    var b = e.target.closest && e.target.closest(".dinamika-legend [data-seriya]");
    if (b && !b.contains(e.relatedTarget)) fokus(b.closest(".dinamika"), null);
  });
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest(".dinamika-legend [data-seriya]");
    if (!b) return;
    var karta = b.closest(".dinamika"), blok = karta.querySelector("[data-dinamika]");
    var yashirin = blok._yashirin || (blok._yashirin = {}), si = b.dataset.seriya;
    yashirin[si] = !yashirin[si];
    b.setAttribute("aria-pressed", yashirin[si] ? "false" : "true");
    fokus(karta, null);
    chiz(blok);
  });
})();
