/* Live monitor page logic (loaded only by monitor.html). */
(function () {
  'use strict';
  const body = document.getElementById('mon-body');
  if (!body) return;

  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const btn = document.getElementById('mon-toggle');
  const status = document.getElementById('mon-status');
  const counts = { total: 0, normal: 0, attack: 0 };
  const INTERVAL_MS = 2000, MAX_ROWS = 25;
  let timer = null, busy = false;

  function esc(v) {
    const d = document.createElement('div');
    d.textContent = v == null ? '' : String(v);
    return d.innerHTML;
  }

  function render() {
    document.getElementById('m-total').textContent = counts.total;
    document.getElementById('m-normal').textContent = counts.normal;
    document.getElementById('m-attack').textContent = counts.attack;
  }

  function addRow(r) {
    const empty = body.querySelector('.empty');
    if (empty) empty.remove();
    const tr = document.createElement('tr');
    tr.className = 'fresh' + (r.is_attack ? ' attack-row' : '');
    tr.innerHTML =
      '<td class="text-nowrap">' + esc(r.time) + '</td><td>' + esc(r.protocol) +
      '</td><td>' + esc(r.service) + '</td><td>' + esc(r.flag) +
      '</td><td>' + esc(r.src_bytes) + '</td><td>' + esc(r.dst_bytes) +
      '</td><td><span class="badge ' + (r.is_attack ? 'bg-bad' : 'bg-ok') + '">' + esc(r.prediction) +
      '</span></td><td>' + esc(r.confidence) + '%</td>';
    body.prepend(tr);
    while (body.children.length > MAX_ROWS) body.lastElementChild.remove();
  }

  async function tick(count) {
    if (busy) return;
    busy = true;
    try {
      const res = await fetch('/api/monitor/tick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: JSON.stringify({ count: count })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      data.results.forEach(function (r) {
        counts.total++; r.is_attack ? counts.attack++ : counts.normal++;
        addRow(r);
      });
      render();
    } catch (e) {
      stop();
      status.textContent = 'Stopped: ' + e.message + ' (log in again if your session expired)';
    } finally { busy = false; }
  }

  function start() {
    btn.querySelector('span').textContent = 'Stop';
    btn.querySelector('i').className = 'bi bi-pause-fill';
    status.textContent = 'Monitoring…';
    tick(1);
    timer = setInterval(function () { tick(1); }, INTERVAL_MS);
  }
  function stop() {
    clearInterval(timer); timer = null;
    btn.querySelector('span').textContent = 'Start';
    btn.querySelector('i').className = 'bi bi-play-fill';
    status.textContent = 'Stopped';
  }

  btn.addEventListener('click', function () { timer ? stop() : start(); });
  document.getElementById('mon-batch').addEventListener('click', function () { tick(20); });
  document.getElementById('mon-clear').addEventListener('click', function () {
    body.innerHTML = '<tr class="empty"><td colspan="8" class="text-center text-secondary py-4">View cleared. Records stay in the database.</td></tr>';
    counts.total = counts.normal = counts.attack = 0; render();
  });
  window.addEventListener('pagehide', stop);
})();
