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

  // Monoton kubik egri (Fritsch–Carlson, d3 curveMonotoneX kabi): har nuqtadan o'tadi, ikki nuqta orasida
  // ulardan yuqori/past chiqmaydi — summa sakrashlarida ham yolg'on «tepalik» chizilmaydi. p — [[x, y], ...].
  function egriYol(p) {
    var n = p.length, i;
    if (n < 3) return "M" + p.map(function (q) { return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join(" L");
    var s = [], t = [];
    for (i = 0; i < n - 1; i++) s.push((p[i + 1][1] - p[i][1]) / (p[i + 1][0] - p[i][0]));
    t[0] = s[0];
    t[n - 1] = s[n - 2];
    for (i = 1; i < n - 1; i++) {
      if (s[i - 1] * s[i] <= 0) { t[i] = 0; continue; }
      var h0 = p[i][0] - p[i - 1][0], h1 = p[i + 1][0] - p[i][0];
      var o = (s[i - 1] * h1 + s[i] * h0) / (h0 + h1);
      t[i] = (Math.sign(s[i - 1]) + Math.sign(s[i])) * Math.min(Math.abs(s[i - 1]), Math.abs(s[i]), 0.5 * Math.abs(o));
    }
    var d = "M" + p[0][0].toFixed(1) + "," + p[0][1].toFixed(1);
    for (i = 0; i < n - 1; i++) {
      var dx = (p[i + 1][0] - p[i][0]) / 3;
      d += " C" + (p[i][0] + dx).toFixed(1) + "," + (p[i][1] + t[i] * dx).toFixed(1) + " " +
        (p[i + 1][0] - dx).toFixed(1) + "," + (p[i + 1][1] - t[i + 1] * dx).toFixed(1) + " " +
        p[i + 1][0].toFixed(1) + "," + p[i + 1][1].toFixed(1);
    }
    return d;
  }

  var HARAKATSIZ = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function malumot(blok) {
    var manba = blok.closest(".dinamika").querySelector("#dinamika-malumot");
    return manba ? JSON.parse(manba.textContent) : null;
  }

  function chiz(blok, animatsiya) {
    animatsiya = animatsiya && !HARAKATSIZ;
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
    svg.classList.toggle("animatsiya", !!animatsiya);

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

    // Chiziqlar: monoton egri (oy nuqtalaridan o'tadi, ulardan oshib ketmaydi). 3 tagacha chiziq yoki umumiy
    // ko'rishda — ostida yengil soha. `animatsiya` — faqat yangi ma'lumotda (o'lcham o'zgarganda emas).
    var oxirlar = [], korinadi = m.seriyalar.filter(function (s, si) { return !yashirin[si]; }).length;
    var asos = TEPA + boyi, soha = m.umumiy || korinadi <= 3;
    m.seriyalar.forEach(function (s, si) {
      if (yashirin[si]) return;
      var g = el("g", { "class": "seriya", "data-seriya": si }, svg);
      var egri = egriYol(s.q.map(function (q, i) { return [x(i), y(q)]; }));
      if (soha) {
        var id = "dinamika-soha-" + si;
        var grad = el("linearGradient", { id: id, x1: 0, x2: 0, y1: 0, y2: 1 }, el("defs", {}, g));
        el("stop", { offset: "0%", "stop-color": s.rang, "stop-opacity": m.umumiy ? 0.24 : 0.1 }, grad);
        el("stop", { offset: "100%", "stop-color": s.rang, "stop-opacity": 0 }, grad);
        el("path", { "class": "soha", fill: "url(#" + id + ")",
          d: egri + " L" + x(n - 1).toFixed(1) + "," + asos + " L" + x(0).toFixed(1) + "," + asos + " Z" }, g);
      }
      var chiziq = el("path", { "class": "chiziq" + (m.umumiy ? " qalin" : ""), stroke: s.rang, d: egri }, g);
      if (animatsiya) {
        var uzunlik = chiziq.getTotalLength();
        chiziq.style.strokeDasharray = uzunlik;
        chiziq.style.strokeDashoffset = uzunlik;
        chiziq.getBoundingClientRect();  // boshlang'ich holat qo'llansin, keyin o'tish
        chiziq.style.transition = "stroke-dashoffset .9s cubic-bezier(.3,.7,.2,1) " + (si * 0.06) + "s";
        chiziq.style.strokeDashoffset = 0;
      }
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
      el("circle", { "class": "nuqta", cx: g.x(i), cy: g.y(s.q[i]), r: 5.5, fill: s.rang }, svg);
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
      chiz(blok, true);  // yangi ma'lumot — chiziqlar chizilib chiqadi
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
