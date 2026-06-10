"""Observability dashboard — a single self-contained HTML page.

No build step, no npm, no external CDN: just vanilla JS that polls /metrics
and renders. Served at GET /dashboard by http_app.py. Pure module.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude IA Local — Panel</title>
<style>
  :root {
    --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
    --dim: #8b949e; --green: #3fb950; --blue: #58a6ff; --yellow: #d29922;
    --red: #f85149; --purple: #bc8cff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    padding: 24px; line-height: 1.4;
  }
  header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
  h1 { font-size: 20px; margin: 0; font-weight: 600; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); }
  .meta { color: var(--dim); font-size: 13px; }
  .meta strong { color: var(--text); font-weight: 500; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .card {
    background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px;
  }
  .card .label { color: var(--dim); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
  .card .value { font-size: 26px; font-weight: 600; margin-top: 4px; font-variant-numeric: tabular-nums; }
  .card .sub { color: var(--dim); font-size: 12px; margin-top: 2px; }
  .v-blue { color: var(--blue); } .v-green { color: var(--green); }
  .v-yellow { color: var(--yellow); } .v-red { color: var(--red); } .v-purple { color: var(--purple); }
  section { margin-bottom: 24px; }
  h2 { font-size: 14px; color: var(--dim); text-transform: uppercase; letter-spacing: .04em; margin: 0 0 10px; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 720px) { .cols { grid-template-columns: 1fr; } }
  .bar-row { display: flex; align-items: center; gap: 8px; margin: 5px 0; font-size: 13px; }
  .bar-row .name { width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); }
  .bar-track { flex: 1; background: #21262d; border-radius: 4px; height: 16px; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--blue); border-radius: 4px; }
  .bar-fill.rec { background: var(--yellow); }
  .bar-row .num { width: 44px; text-align: right; color: var(--dim); font-variant-numeric: tabular-nums; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  th { color: var(--dim); font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  td.tools { white-space: normal; }
  .tag { display: inline-block; background: #21262d; border: 1px solid var(--border); border-radius: 5px; padding: 1px 6px; margin: 1px; font-size: 11px; }
  .badge { font-size: 11px; padding: 1px 7px; border-radius: 10px; font-weight: 500; }
  .badge.code { background: rgba(88,166,255,.15); color: var(--blue); }
  .badge.browser { background: rgba(188,140,255,.15); color: var(--purple); }
  .badge.plain { background: #21262d; color: var(--dim); }
  .badge.err { background: rgba(248,81,73,.15); color: var(--red); }
  .empty { color: var(--dim); font-style: italic; padding: 8px 0; }
  .err-banner { background: rgba(248,81,73,.1); border: 1px solid var(--red); color: var(--red);
    padding: 10px 14px; border-radius: 8px; margin-bottom: 16px; font-size: 13px; word-break: break-word; }
  footer { color: var(--dim); font-size: 12px; margin-top: 8px; }
</style>
</head>
<body>
  <header>
    <span class="dot" id="dot"></span>
    <h1>Claude IA Local</h1>
    <span class="meta">Panel de observabilidad · MLX en Apple Silicon</span>
  </header>
  <div class="meta" id="topline" style="margin-bottom:18px;">Conectando…</div>

  <div id="err"></div>

  <div class="grid" id="cards"></div>

  <div class="cols">
    <section>
      <h2>Tool-calls por herramienta</h2>
      <div id="tools"></div>
    </section>
    <section>
      <h2>Recuperaciones por herramienta</h2>
      <div id="recoveries"></div>
    </section>
  </div>

  <section>
    <h2>Actividad reciente</h2>
    <table>
      <thead><tr>
        <th>Hora</th><th>Modo</th><th>Prompt</th><th>Salida</th><th>tok/s</th>
        <th>Tiempo</th><th>Fin</th><th>Cache</th><th>Tools</th>
      </tr></thead>
      <tbody id="recent"></tbody>
    </table>
  </section>

  <footer id="footer"></footer>

<script>
function fmtUptime(s) {
  s = Math.floor(s);
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60;
  if (h) return h+"h "+m+"m";
  if (m) return m+"m "+sec+"s";
  return sec+"s";
}
function fmtTime(epoch) {
  const d = new Date(epoch*1000);
  return d.toLocaleTimeString();
}
function el(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }

function card(label, value, cls, sub) {
  return `<div class="card"><div class="label">${label}</div>`
       + `<div class="value ${cls||''}">${value}</div>`
       + (sub ? `<div class="sub">${sub}</div>` : '') + `</div>`;
}

function bars(obj, cls) {
  const entries = Object.entries(obj || {}).sort((a,b)=>b[1]-a[1]);
  if (!entries.length) return '<div class="empty">Ninguna todavía</div>';
  const max = Math.max(...entries.map(e=>e[1]));
  return entries.map(([name,n]) => {
    const pct = max ? Math.round(n/max*100) : 0;
    return `<div class="bar-row"><span class="name" title="${name}">${name}</span>`
         + `<span class="bar-track"><span class="bar-fill ${cls||''}" style="width:${pct}%"></span></span>`
         + `<span class="num">${n}</span></div>`;
  }).join('');
}

async function tick() {
  let m;
  try {
    const r = await fetch('/metrics', {cache:'no-store'});
    m = await r.json();
  } catch (e) {
    document.getElementById('dot').style.background = 'var(--red)';
    document.getElementById('topline').textContent = 'Servidor no alcanzable — reintentando…';
    return;
  }
  document.getElementById('dot').style.background = m.in_flight > 0 ? 'var(--yellow)' : 'var(--green)';
  document.getElementById('topline').innerHTML =
    `Modelo: <strong>${m.model || '—'}</strong> · Activo desde hace <strong>${fmtUptime(m.uptime_seconds)}</strong>`;

  document.getElementById('err').innerHTML = m.last_error
    ? `<div class="err-banner">Último error: ${m.last_error}</div>` : '';

  document.getElementById('cards').innerHTML =
      card('Requests', m.total_requests, 'v-blue', (m.in_flight||0)+' en vuelo')
    + card('tok/s promedio', m.avg_tps, 'v-green', m.total_output_tokens+' tokens generados')
    + card('Cache hit rate', Math.round(m.cache_hit_rate*100)+'%', 'v-purple', m.cache_hits+' / '+(m.cache_hits+m.cache_misses))
    + card('Tool-calls', m.tool_calls_total, 'v-blue')
    + card('Recuperaciones', m.recoveries_total, m.recoveries_total>0?'v-yellow':'', 'JSON corrupto rescatado')
    + card('Reintentos', m.retries_total, m.retries_total>0?'v-yellow':'')
    + card('Errores', m.total_errors, m.total_errors>0?'v-red':'', '');

  document.getElementById('tools').innerHTML = bars(m.tool_calls_by_name);
  document.getElementById('recoveries').innerHTML = bars(m.recoveries_by_name, 'rec');

  const rows = (m.recent || []).slice().reverse().map(r => {
    if (!r.ok) {
      return `<tr><td>${fmtTime(r.ts)}</td><td><span class="badge err">error</span></td>`
           + `<td colspan="7">${r.error||''}</td></tr>`;
    }
    const tools = (r.tools||[]).map(t=>`<span class="tag">${t}</span>`).join(' ') || '<span class="meta">—</span>';
    return `<tr><td>${fmtTime(r.ts)}</td>`
         + `<td><span class="badge ${r.mode}">${r.mode}</span></td>`
         + `<td>${r.prompt_tokens}</td><td>${r.output_tokens}</td><td>${r.tps}</td>`
         + `<td>${r.elapsed}s</td><td>${r.finish_reason}</td>`
         + `<td>${r.cache_hit?'✓':'·'}</td><td class="tools">${tools}</td></tr>`;
  }).join('');
  document.getElementById('recent').innerHTML = rows || '<tr><td colspan="9" class="empty">Sin actividad todavía. Haz una petición desde Claude Code.</td></tr>';

  document.getElementById('footer').textContent = 'Actualizado ' + fmtTime(m.now) + ' · refresca cada 2 s';
}

tick();
setInterval(tick, 2000);
</script>
</body>
</html>"""
