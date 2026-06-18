import json
from collections import Counter
from datetime import datetime


def _contar(actores, campo):
    return dict(Counter(
        (a.get(campo) or "Sin clasificar") for a in actores
        if a.get(campo)
    ).most_common(10))


def _verificacion_counts(actores):
    dentro = sum(1 for a in actores if (a.get("verificacion") or "").startswith("✅"))
    fuera  = sum(1 for a in actores if (a.get("verificacion") or "").startswith("⚠️"))
    sin    = sum(1 for a in actores if (a.get("verificacion") or "").startswith("❓"))
    return dentro, fuera, sin


COLORES = {
    "Empresas privadas":          "#1D6FA8",
    "Academia":                   "#6B4FA8",
    "Administración pública":     "#1A7A4A",
    "Sociedad civil organizada":  "#A85A1A",
    "Incubadoras y aceleradoras": "#00695C",
}

ICONOS = {
    "Empresas privadas":          "🏢",
    "Academia":                   "🎓",
    "Administración pública":     "🏛️",
    "Sociedad civil organizada":  "🤝",
    "Incubadoras y aceleradoras": "🚀",
}


def exportar_html(resultados: dict, zona: str, meta: dict = None) -> str:
    fecha = (meta or {}).get("fecha", datetime.now().strftime("%d/%m/%Y %H:%M"))
    provider = (meta or {}).get("provider", "")
    motor = (meta or {}).get("motor", "")
    total = sum(len(v) for v in resultados.values())

    # Preparar datos para Plotly por categoría
    secciones = []
    for cat, actores in resultados.items():
        if not actores:
            continue
        color = COLORES.get(cat, "#444444")
        icono = ICONOS.get(cat, "📋")

        sectores   = _contar(actores, "sector")
        tipos      = _contar(actores, "tipo")
        presencias = _contar(actores, "presencia")
        dentro, fuera, sin_datos = _verificacion_counts(actores)

        secciones.append({
            "cat": cat,
            "icono": icono,
            "color": color,
            "total": len(actores),
            "sectores": sectores,
            "tipos": tipos,
            "presencias": presencias,
            "verificacion": {"✅ Dentro": dentro, "⚠️ Fuera": fuera, "❓ Sin datos": sin_datos},
            "actores": [
                {
                    "nombre": a.get("nombre",""),
                    "tipo": a.get("tipo",""),
                    "sector": a.get("sector",""),
                    "web": a.get("web",""),
                    "ubicacion": a.get("ubicacion","") or a.get("direccion",""),
                    "verificacion": a.get("verificacion",""),
                    "presencia": a.get("presencia",""),
                }
                for a in actores
            ]
        })

    data_json = json.dumps(secciones, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ecosistema — {zona}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f4f6f9; color: #1a1a2e; }}

  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
             color: white; padding: 40px 48px; }}
  .header h1 {{ font-size: 2rem; font-weight: 700; margin-bottom: 6px; }}
  .header p  {{ opacity: .7; font-size: .95rem; }}
  .meta {{ display:flex; gap: 32px; margin-top: 20px; flex-wrap: wrap; }}
  .meta-item {{ background: rgba(255,255,255,.1); border-radius: 8px;
                padding: 10px 18px; font-size: .85rem; }}
  .meta-item span {{ display:block; opacity:.6; font-size:.75rem; margin-bottom:2px; }}

  .kpis {{ display: flex; gap: 16px; padding: 32px 48px 0; flex-wrap: wrap; }}
  .kpi {{ background: white; border-radius: 12px; padding: 20px 28px;
          flex: 1; min-width: 140px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
  .kpi .num {{ font-size: 2.4rem; font-weight: 800; line-height: 1; }}
  .kpi .lbl {{ font-size: .8rem; color: #666; margin-top: 4px; }}

  .section {{ margin: 32px 48px; background: white; border-radius: 16px;
              box-shadow: 0 2px 12px rgba(0,0,0,.07); overflow: hidden; }}
  .section-header {{ padding: 24px 32px; color: white; display:flex;
                     align-items:center; gap:12px; }}
  .section-header h2 {{ font-size: 1.25rem; font-weight: 700; }}
  .section-header .badge {{ background: rgba(255,255,255,.2); border-radius: 20px;
                            padding: 3px 12px; font-size: .85rem; margin-left:auto; }}

  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr;
                  gap: 0; border-bottom: 1px solid #f0f0f0; }}
  .chart-box {{ padding: 24px; border-right: 1px solid #f0f0f0; }}
  .chart-box:last-child {{ border-right: none; }}
  .chart-title {{ font-size: .8rem; font-weight: 600; color: #888;
                  text-transform: uppercase; letter-spacing: .05em; margin-bottom: 12px; }}

  .verif-row {{ display:flex; gap:16px; padding: 20px 32px; background:#fafafa;
                border-bottom: 1px solid #f0f0f0; flex-wrap:wrap; }}
  .verif-pill {{ border-radius: 20px; padding: 6px 16px; font-size: .85rem; font-weight:600; }}
  .pill-green  {{ background:#e8f5e9; color:#2e7d32; }}
  .pill-yellow {{ background:#fff9c4; color:#f57f17; }}
  .pill-gray   {{ background:#f5f5f5; color:#757575; }}

  .table-wrap {{ overflow-x: auto; padding: 0 32px 24px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.85rem; margin-top:16px; }}
  thead tr {{ background:#f8f9fa; }}
  th {{ padding:10px 12px; text-align:left; font-weight:600; color:#555;
        border-bottom: 2px solid #eee; white-space:nowrap; }}
  td {{ padding:9px 12px; border-bottom:1px solid #f0f0f0; vertical-align:top; }}
  tr:hover td {{ background:#fafcff; }}
  .web-link {{ color: #1D6FA8; text-decoration:none; }}
  .web-link:hover {{ text-decoration:underline; }}
  .verif-badge {{ font-size:.78rem; white-space:nowrap; }}

  footer {{ text-align:center; padding:32px; color:#aaa; font-size:.8rem; }}

  @media(max-width:700px) {{
    .header, .kpis, .section {{ padding-left:16px; padding-right:16px; }}
    .section {{ margin-left:12px; margin-right:12px; }}
    .charts-grid {{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🗺️ Mapeo de ecosistema — {zona}</h1>
  <p>Análisis territorial de actores del ecosistema</p>
  <div class="meta">
    <div class="meta-item"><span>Fecha</span>{fecha}</div>
    <div class="meta-item"><span>Proveedor IA</span>{provider}</div>
    <div class="meta-item"><span>Motor búsqueda</span>{motor}</div>
    <div class="meta-item"><span>Total actores</span>{total}</div>
  </div>
</div>

<div class="kpis" id="kpis"></div>
<div id="sections"></div>

<footer>Generado automáticamente · Ecosystem Mapper</footer>

<script>
const DATA = {data_json};

const COLORES = {{
  "Empresas privadas": "#1D6FA8",
  "Academia": "#6B4FA8",
  "Administración pública": "#1A7A4A",
  "Sociedad civil organizada": "#A85A1A",
  "Incubadoras y aceleradoras": "#00695C",
}};

// KPIs globales
const kpisEl = document.getElementById("kpis");
DATA.forEach(s => {{
  kpisEl.innerHTML += `
    <div class="kpi">
      <div class="num" style="color:${{s.color}}">${{s.total}}</div>
      <div class="lbl">${{s.icono}} ${{s.cat}}</div>
    </div>`;
}});

// Secciones
const sectionsEl = document.getElementById("sections");
DATA.forEach((s, idx) => {{
  const secId = `sec_${{idx}}`;
  const div = document.createElement("div");
  div.className = "section";

  const [dentro, fuera, sinDatos] = [
    s.verificacion["✅ Dentro"] || 0,
    s.verificacion["⚠️ Fuera"] || 0,
    s.verificacion["❓ Sin datos"] || 0,
  ];

  const filas = s.actores.map(a => `
    <tr>
      <td><strong>${{a.nombre}}</strong></td>
      <td>${{a.tipo || ""}}</td>
      <td>${{a.sector || ""}}</td>
      <td>${{a.ubicacion || ""}}</td>
      <td>${{a.web ? `<a class="web-link" href="${{a.web}}" target="_blank">🔗 Web</a>` : ""}}</td>
      <td class="verif-badge">${{a.verificacion || ""}}</td>
    </tr>`).join("");

  div.innerHTML = `
    <div class="section-header" style="background:${{s.color}}">
      <span style="font-size:1.5rem">${{s.icono}}</span>
      <h2>${{s.cat}}</h2>
      <span class="badge">${{s.total}} actores</span>
    </div>

    <div class="verif-row">
      <span class="verif-pill pill-green">✅ Dentro de zona: ${{dentro}}</span>
      <span class="verif-pill pill-yellow">⚠️ Fuera — revisar: ${{fuera}}</span>
      <span class="verif-pill pill-gray">❓ Sin confirmar: ${{sinDatos}}</span>
    </div>

    <div class="charts-grid">
      <div class="chart-box">
        <div class="chart-title">Por sector / ámbito</div>
        <div id="${{secId}}_sectores"></div>
      </div>
      <div class="chart-box">
        <div class="chart-title">Por tipo</div>
        <div id="${{secId}}_tipos"></div>
      </div>
    </div>

    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Nombre</th><th>Tipo</th><th>Sector</th>
          <th>Ubicación</th><th>Web</th><th>Verificación</th>
        </tr></thead>
        <tbody>${{filas}}</tbody>
      </table>
    </div>`;

  sectionsEl.appendChild(div);

  const layout = {{
    height: 260, margin: {{t:10,b:10,l:10,r:10}},
    showlegend: true,
    legend: {{orientation:"h", y:-0.2, font:{{size:11}}}},
    paper_bgcolor:"rgba(0,0,0,0)",
    plot_bgcolor:"rgba(0,0,0,0)",
  }};

  // Gráfico sectores — barras horizontales
  const sectKeys = Object.keys(s.sectores);
  const sectVals = Object.values(s.sectores);
  if (sectKeys.length > 0) {{
    Plotly.newPlot(`${{secId}}_sectores`, [{{
      type: "bar", orientation: "h",
      x: sectVals, y: sectKeys,
      marker: {{ color: s.color, opacity: 0.85 }},
      hovertemplate: "%{{y}}: %{{x}}<extra></extra>",
    }}], {{...layout, xaxis:{{fixedrange:true}}, yaxis:{{fixedrange:true, automargin:true}}}},
    {{displayModeBar:false, responsive:true}});
  }}

  // Gráfico tipos — donut
  const tipoKeys = Object.keys(s.tipos);
  const tipoVals = Object.values(s.tipos);
  if (tipoKeys.length > 0) {{
    Plotly.newPlot(`${{secId}}_tipos`, [{{
      type: "pie", hole: 0.45,
      labels: tipoKeys, values: tipoVals,
      textinfo: "percent",
      hovertemplate: "%{{label}}: %{{value}}<extra></extra>",
      marker: {{ colors: tipoKeys.map((_,i) => `hsl(${{(i*47+200)%360}},55%,${{45+i*5}}%)`) }},
    }}], {{...layout}}, {{displayModeBar:false, responsive:true}});
  }}
}});
</script>
</body>
</html>"""
    return html
