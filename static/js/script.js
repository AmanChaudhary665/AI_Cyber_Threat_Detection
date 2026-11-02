/* CyberShield AI - shared front-end behaviour.
 * NOTE: this is a stand-in written to match the templates. If you have your
 * original static/js/script.js, copy it over this file - everything else
 * keeps working with it (the dashboard also passes window.DASH.trend, which
 * the original simply ignores).
 */
(function () {
  'use strict';
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ---- loader ---- */
  function hideLoader() {
    var l = $('#loader');
    if (l) { l.classList.add('hide'); setTimeout(function () { l.remove(); }, 600); }
  }
  window.addEventListener('load', hideLoader);
  setTimeout(hideLoader, 3000);

  /* ---- toasts ---- */
  window.toast = function (msg, type) {
    var box = $('#toasts'); if (!box) return;
    var el = document.createElement('div');
    el.className = 'toast align-items-center show t-' + (type || 'ok');
    el.innerHTML = '<div class="d-flex"><div class="toast-body"></div><button type="button" class="btn-close btn-close-white me-2 m-auto"></button></div>';
    el.querySelector('.toast-body').textContent = msg;
    el.querySelector('.btn-close').onclick = function () { el.remove(); };
    box.appendChild(el);
    setTimeout(function () { el.remove(); }, 3500);
  };
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-toast]');
    if (t) { e.preventDefault(); window.toast(t.getAttribute('data-toast'), 'ok'); }
    var c = e.target.closest('[data-confirm]');
    if (c && !confirm(c.getAttribute('data-confirm'))) e.preventDefault();
  });

  /* ---- reveal on scroll ---- */
  var items = $$('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { threshold: 0.1 });
    items.forEach(function (el) { io.observe(el); });
  } else { items.forEach(function (el) { el.classList.add('in'); }); }

  /* ---- count-up numbers ---- */
  $$('[data-count]').forEach(function (el) {
    var target = parseFloat(el.getAttribute('data-count')) || 0;
    var dec = parseInt(el.getAttribute('data-dec') || '0', 10);
    var start = null, dur = 1000;
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      el.textContent = (target * p).toFixed(dec);
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });

  /* ---- result timestamp ---- */
  var ts = $('#ts');
  if (ts) {
    var d = ts.getAttribute('data-ts') ? new Date(ts.getAttribute('data-ts')) : new Date();
    if (isNaN(d.getTime())) d = new Date();
    ts.textContent = d.toLocaleString();
  }

  /* ---- form validation + submit spinner ---- */
  $$('.needs-validation').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!form.checkValidity()) { e.preventDefault(); e.stopPropagation(); }
      else {
        var b = $('#pbtn', form);
        if (b) { $('.lbl', b).classList.add('d-none'); $('.spinner-border', b).classList.remove('d-none'); }
      }
      form.classList.add('was-validated');
    });
  });

  /* ---- background: network of drifting points (Three.js) ---- */
  var canvas = $('#bg-canvas');
  if (canvas && window.THREE && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(60, 1, 1, 2000); camera.position.z = 600;
    var N = 70, pos = new Float32Array(N * 3), vel = [];
    for (var i = 0; i < N; i++) {
      pos[i * 3] = (Math.random() - .5) * 1400; pos[i * 3 + 1] = (Math.random() - .5) * 900; pos[i * 3 + 2] = (Math.random() - .5) * 400;
      vel.push([(Math.random() - .5) * .4, (Math.random() - .5) * .4]);
    }
    var pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    scene.add(new THREE.Points(pg, new THREE.PointsMaterial({ color: 0x00d4ff, size: 5 })));
    var lg = new THREE.BufferGeometry();
    var lpos = new Float32Array(N * N * 6); lg.setAttribute('position', new THREE.BufferAttribute(lpos, 3));
    scene.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: 0x7c3aed, transparent: true, opacity: .35 })));
    var resize = function () { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); };
    resize(); addEventListener('resize', resize);
    (function loop() {
      var n = 0;
      for (var a = 0; a < N; a++) {
        pos[a * 3] += vel[a][0]; pos[a * 3 + 1] += vel[a][1];
        if (Math.abs(pos[a * 3]) > 700) vel[a][0] *= -1; if (Math.abs(pos[a * 3 + 1]) > 450) vel[a][1] *= -1;
        for (var b = a + 1; b < N; b++) {
          var dx = pos[a * 3] - pos[b * 3], dy = pos[a * 3 + 1] - pos[b * 3 + 1];
          if (dx * dx + dy * dy < 40000) {
            lpos.set([pos[a * 3], pos[a * 3 + 1], pos[a * 3 + 2], pos[b * 3], pos[b * 3 + 1], pos[b * 3 + 2]], n); n += 6;
          }
        }
      }
      pg.attributes.position.needsUpdate = true;
      lg.setDrawRange(0, n / 3); lg.attributes.position.needsUpdate = true;
      renderer.render(scene, camera); requestAnimationFrame(loop);
    })();
  }

  /* ---- hero particles + lottie (home page only) ---- */
  if ($('#particles') && window.particlesJS) {
    particlesJS('particles', { particles: { number: { value: 40 }, color: { value: '#00D4FF' }, size: { value: 2 },
      line_linked: { enable: true, color: '#7C3AED', opacity: .3 }, move: { speed: 1.2 } }, retina_detect: true });
  }
  var lot = $('#lottie');
  if (lot && window.lottie) {
    var anim = lottie.loadAnimation({ container: lot, renderer: 'svg', loop: true, autoplay: true, path: lot.getAttribute('data-src') });
    anim.addEventListener('data_failed', function () { lot.remove(); });  /* no shield.json -> SVG art stays */
  } else if (lot) { lot.remove(); }

  /* ---- dashboard: charts, filter, pagination ---- */
  if (window.DASH && window.Chart) {
    var D = window.DASH, text = '#94a3b8', grid = 'rgba(255,255,255,.06)';
    Chart.defaults.color = text; Chart.defaults.borderColor = grid;
    var palette = ['#EF4444', '#7C3AED', '#10B981', '#F59E0B', '#00D4FF', '#EC4899', '#14B8A6', '#6366F1'];
    var pie = $('#pie');
    if (pie) new Chart(pie, { type: 'doughnut', data: { labels: D.labels, datasets: [{ data: D.values,
      backgroundColor: D.labels.map(function (_, i) { return palette[i % palette.length]; }), borderWidth: 0 }] },
      options: { plugins: { legend: { position: 'bottom' } }, cutout: '45%' } });
    var line = $('#line'), tr = D.trend || {};
    if (line) new Chart(line, { type: 'line', data: { labels: tr.labels || [], datasets: [
      { label: 'Normal', data: tr.normal || [], borderColor: '#10B981', backgroundColor: '#10B981', tension: .4 },
      { label: 'Attack', data: tr.attack || [], borderColor: '#EF4444', backgroundColor: '#EF4444', tension: .4 }] },
      options: { scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } } });
    var bar = $('#bar');
    if (bar) new Chart(bar, { type: 'bar', data: { labels: ['Normal', 'Attack'], datasets: [{ data: [D.normal, D.attacks],
      backgroundColor: ['#10B981', '#EF4444'], borderRadius: 8 }] },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } } });
  }

  var tb = $('#tb');
  if (tb) {
    var PER = 10, page = 1, flt = $('#flt'), pg = $('#pg');
    var rows = function () { return $$('tr[data-pred]', tb); };
    var draw = function () {
      var want = flt ? flt.value : '';
      var vis = rows().filter(function (r) { return !want || r.getAttribute('data-pred') === want; });
      var pages = Math.max(1, Math.ceil(vis.length / PER)); if (page > pages) page = pages;
      rows().forEach(function (r) { r.style.display = 'none'; });
      vis.slice((page - 1) * PER, page * PER).forEach(function (r) { r.style.display = ''; });
      if (pg) {
        pg.innerHTML = '';
        for (var p = 1; p <= pages && pages > 1; p++) {
          var li = document.createElement('li'); li.className = 'page-item' + (p === page ? ' active' : '');
          li.innerHTML = '<a class="page-link" href="#">' + p + '</a>';
          (function (n) { li.onclick = function (e) { e.preventDefault(); page = n; draw(); }; })(p);
          pg.appendChild(li);
        }
      }
    };
    if (flt) flt.addEventListener('change', function () { page = 1; draw(); });
    draw();
  }
})();
