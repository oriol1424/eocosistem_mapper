import streamlit as st
from datetime import datetime
from tools.geo import buscar_zonas
from tools.enrichment import enriquecer_lista
from agents.empresas_agent import EmpresasAgent
from agents.academia_agent import AcademiaAgent
from agents.administracion_agent import AdministracionAgent
from agents.sociedad_agent import SociedadAgent
from agents.coordinator import coordinar
from agents.incubadoras_agent import IncubadorasAgent
from exporter import exportar_excel
from html_exporter import exportar_html

st.set_page_config(page_title="Mapeador de Ecosistemas", page_icon="🗺️", layout="wide")
st.title("🗺️ Mapeador de ecosistemas territoriales")
st.caption("Analiza actores de un territorio y exporta los resultados a Excel")

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")

    st.subheader("Proveedor de IA")
    provider = st.selectbox(
        "Proveedor",
        ["groq", "openai", "gemini", "anthropic"],
        format_func=lambda x: {
            "groq": "Groq (gratuito)",
            "openai": "OpenAI",
            "gemini": "Google Gemini (gratuito)",
            "anthropic": "Anthropic / Claude"
        }[x]
    )
    api_key = st.text_input("API Key de IA", type="password", placeholder="Pega tu key aquí...")
    st.caption("🔒 Solo se usa en esta sesión.")

    st.divider()
    st.subheader("Búsqueda web")
    st.info(
        "**Recomendado para mejores resultados:**\n\n"
        "🥇 **Serper** — Filtra por país e idioma automáticamente. "
        "Resultados mucho más precisos geográficamente. "
        "Gratis en [serper.dev](https://serper.dev) (2.500/mes)\n\n"
        "🥈 **Tavily** — Buena alternativa. "
        "Gratis en [tavily.com](https://tavily.com) (1.000/mes)\n\n"
        "⚠️ Sin keys usa DuckDuckGo gratis pero sin filtro geográfico — "
        "puede devolver resultados de otras zonas con el mismo nombre."
    )
    tavily_key = st.text_input("Tavily API Key", type="password", placeholder="tvly-...")
    serper_key = st.text_input("Serper API Key", type="password", placeholder="...")

    st.divider()
    st.subheader("Ubicación (opcional)")
    geoapify_key = st.text_input(
        "Geoapify Key",
        type="password",
        placeholder="geoapify.com — gratis",
        help="Activa el autocompletado de zonas."
    )
    opencage_key = st.text_input(
        "OpenCage Key",
        type="password",
        placeholder="opencagedata.com — gratis",
        help="Mejora el enriquecimiento de direcciones."
    )

# ── INSTRUCCIONES ────────────────────────────────────────────────────────────
with st.expander("📖 Instrucciones y APIs necesarias — léeme antes de empezar"):
    st.markdown("""
## Cómo usar el Mapeador de Ecosistemas

Esta herramienta busca automáticamente actores de un ecosistema territorial (empresas, academia, administración pública y sociedad civil) y exporta los resultados a Excel y un dashboard HTML interactivo.

---

### 🤖 APIs de Inteligencia Artificial — el cerebro del agente

El agente necesita un modelo de IA para extraer y clasificar la información. **Elige uno:**

| Proveedor | Coste | Límite gratuito | Registro |
|---|---|---|---|
| **Groq** ⭐ Recomendado | Gratuito | 100.000 tokens/día · 6.000/min | [console.groq.com](https://console.groq.com) |
| **Google Gemini** | Gratuito | 15 req/min · sin límite diario estricto | [aistudio.google.com](https://aistudio.google.com) |
| **OpenAI** | De pago | Sin tier gratuito | [platform.openai.com](https://platform.openai.com) |
| **Anthropic** | De pago | Sin tier gratuito | [console.anthropic.com](https://console.anthropic.com) |

> ⚠️ **Con Groq:** si se agotan los tokens diarios la app guarda los resultados parciales y avisa. Los tokens se resetean cada 24h. Si necesitas más búsquedas en el mismo día, usa Gemini como alternativa.

---

### 🔍 APIs de Búsqueda Web — para encontrar actores

Sin estas keys la app usa DuckDuckGo gratis, pero los resultados son menos precisos geográficamente.

| Proveedor | Coste | Límite gratuito | Registro |
|---|---|---|---|
| **Serper** ⭐ Recomendado | Gratuito | 2.500 búsquedas/mes | [serper.dev](https://serper.dev) |
| **Tavily** | Gratuito | 1.000 búsquedas/mes | [tavily.com](https://tavily.com) |
| **DuckDuckGo** | Gratuito | Sin límite (más lento, sin filtro geográfico) | Sin registro |

> ⭐ **Serper** es el más recomendado porque filtra automáticamente por país e idioma, lo que mejora mucho la precisión geográfica de los resultados.

---

### 🗺️ APIs de Ubicación — para el autocompletado y enriquecimiento

Opcionales pero mejoran mucho la experiencia y la calidad de los datos.

| Proveedor | Para qué sirve | Coste | Registro |
|---|---|---|---|
| **Geoapify** | Autocompletado de zonas geográficas en el desplegable | Gratuito · 3.000 req/día | [geoapify.com](https://geoapify.com) |
| **OpenCage** | Enriquecer actores con dirección y coordenadas exactas | Gratuito · 2.500 req/día | [opencagedata.com](https://opencagedata.com) |

> Sin Geoapify puedes escribir la zona en texto libre. Sin OpenCage el enriquecimiento usa solo OSM Nominatim (más lento).

---

### 🚀 Configuración recomendada para empezar gratis

1. Regístrate en **[console.groq.com](https://console.groq.com)** → API Keys → Create API Key
2. Regístrate en **[serper.dev](https://serper.dev)** → copia tu API key
3. Regístrate en **[geoapify.com](https://geoapify.com)** → API Keys → copia tu key
4. Pega las tres keys en la barra lateral izquierda
5. Escribe una zona y lanza la búsqueda

Con esta configuración tienes **~3-4 búsquedas completas al día** de forma totalmente gratuita.

---

### ⚠️ Sobre la precisión de los resultados

- Los resultados dependen de lo que hay indexado en internet sobre esa zona
- Zonas muy específicas (barrios, distritos) pueden tener menos resultados que ciudades enteras
- La columna **Verificación** en el Excel indica si cada actor está confirmado dentro de la zona
- Revisa siempre los marcados con ⚠️ antes de presentar los resultados a un cliente
""")

# ── ZONA GEOGRÁFICA ──────────────────────────────────────────────────────────
st.header("1. Define la zona a analizar")

if "zona_info" not in st.session_state:
    st.session_state.zona_info = None

texto_zona = st.text_input(
    "Escribe una zona geográfica",
    placeholder="Ej: Montcada, Paraíba, Gràcia, Lyon...",
)

zona_info = None

if geoapify_key and len(texto_zona) >= 3:
    with st.spinner("Buscando zonas..."):
        opciones = buscar_zonas(texto_zona, geoapify_key)
    if opciones:
        labels = [f"{o['display']}  [{o['nivel']}]" for o in opciones]
        labels.insert(0, "— Selecciona una opción —")
        seleccion = st.selectbox("Selecciona la zona exacta", labels)
        if seleccion != "— Selecciona una opción —":
            idx = labels.index(seleccion) - 1
            zona_info = opciones[idx]
            st.session_state.zona_info = zona_info
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Nivel", zona_info["nivel"])
            col_b.metric("País", zona_info["pais"])
            col_c.metric("Idioma búsqueda", zona_info["idioma"].upper())
    else:
        st.warning("No se encontraron zonas. Prueba con otro nombre.")

elif len(texto_zona) >= 3:
    zona_info = {
        "display": texto_zona, "nombre": texto_zona,
        "pais": "", "pais_code": "", "nivel": "Ciudad",
        "idioma": "es", "contexto": "", "lat": 0, "lon": 0,
    }
    st.session_state.zona_info = zona_info
    st.caption("Modo texto libre — añade Geoapify key para autocompletado.")

if st.session_state.zona_info and not zona_info:
    zona_info = st.session_state.zona_info

# ── SELECCIÓN DE AGENTES ─────────────────────────────────────────────────────
st.header("2. Agentes a ejecutar")
st.caption("Selecciona qué categorías quieres analizar.")

col_ag1, col_ag2, col_ag3, col_ag4, col_ag5 = st.columns(5)
ag_empresas  = col_ag1.toggle("🏢 Empresas",       value=True)
ag_academia  = col_ag2.toggle("🎓 Academia",        value=True)
ag_admin     = col_ag3.toggle("🏛️ Administración",  value=True)
ag_sociedad  = col_ag4.toggle("🤝 Sociedad civil",  value=True)
ag_incub     = col_ag5.toggle("🚀 Incubadoras",     value=True)

# ── SECTORES ─────────────────────────────────────────────────────────────────
st.header("3. Sectores prioritarios (opcional)")

with st.expander("🏢 Empresas privadas"):
    sectores_empresas = st.multiselect("Sectores", [
        "Tecnología e innovación", "Salud y farmacia", "Industria y manufactura",
        "Comercio y retail", "Construcción e inmobiliaria", "Servicios profesionales",
        "Energía y medio ambiente", "Turismo y hostelería",
        "Alimentación y agroindustria", "Finanzas y seguros"
    ], label_visibility="collapsed")

with st.expander("🎓 Academia"):
    sectores_academia = st.multiselect("Tipos", [
        "Universidades", "Másteres y posgrados", "Doctorado y PhD",
        "Formación Profesional", "Colegios e institutos",
        "Centros de investigación", "Centros tecnológicos"
    ], label_visibility="collapsed")

with st.expander("🏛️ Administración pública"):
    sectores_admin = st.multiselect("Tipos", [
        "Ayuntamientos", "Diputaciones y consejos",
        "Empresas públicas", "Agencias de desarrollo",
        "Servicios sociales", "Bibliotecas y centros cívicos"
    ], label_visibility="collapsed")

with st.expander("🤝 Sociedad civil"):
    sectores_sociedad = st.multiselect("Tipos", [
        "ONGs", "Asociaciones vecinales", "Fundaciones",
        "Asociaciones culturales", "Cooperativas", "Voluntariado"
    ], label_visibility="collapsed")

with st.expander("⚙️ Opciones avanzadas"):
    enriquecer = st.toggle("Enriquecer con direcciones", value=True,
        help="Usa OSM y OpenCage para añadir direcciones y teléfonos.")
    usar_coordinador = st.toggle("Usar agente coordinador", value=True,
        help="Revisa y corrige clasificaciones entre categorías al final.")

# ── LANZAR ────────────────────────────────────────────────────────────────────
st.divider()

ICONOS = {
    "Empresas privadas": "🏢",
    "Academia": "🎓",
    "Administración pública": "🏛️",
    "Sociedad civil organizada": "🤝",
    "Incubadoras y aceleradoras": "🚀",
}

if st.button("🚀 Iniciar búsqueda", type="primary", use_container_width=True):
    if not zona_info:
        st.error("Escribe y selecciona una zona antes de buscar.")
    elif not api_key:
        st.error("Añade tu API key de IA en la barra lateral.")
    else:
        resultados = {
            "Empresas privadas": [],
            "Academia": [],
            "Administración pública": [],
            "Sociedad civil organizada": [],
            "Incubadoras y aceleradoras": [],
        }

        # ── UI de progreso ────────────────────────────────────────────────
        barra_global = st.progress(0)
        estado_global = st.empty()

        col_e, col_a, col_ad, col_s, col_i = st.columns(5)
        indicadores = {
            "Empresas privadas":        col_e.empty(),
            "Academia":                 col_a.empty(),
            "Administración pública":   col_ad.empty(),
            "Sociedad civil organizada":col_s.empty(),
            "Incubadoras y aceleradoras": col_i.empty(),
        }
        for cat, ind in indicadores.items():
            ico = ICONOS.get(cat, "🚀")
            ind.markdown(f"{ico} **{cat.split()[0]}**\n\n⬜ Pendiente")

        detalle = st.empty()
        contador = st.empty()

        from datetime import datetime as dt
        log_busqueda = []
        tokens_agotados = False
        categoria_parada = ""
        meta_busqueda = {
            "zona": zona_info.get("display", ""),
            "fecha": dt.now().strftime("%d/%m/%Y %H:%M"),
            "provider": provider,
            "motor": "Serper" if serper_key else ("Tavily" if tavily_key else "DuckDuckGo"),
            "tokens_agotados": False,
            "categoria_parada": "",
        }

        def _agente(cls, sects):
            return cls(provider, api_key, tavily_key or None, serper_key or None), sects

        agentes_posibles = []
        if ag_empresas:
            agentes_posibles.append(("Empresas privadas",   *_agente(EmpresasAgent, sectores_empresas)))
        if ag_academia:
            agentes_posibles.append(("Academia",            *_agente(AcademiaAgent, sectores_academia)))
        if ag_admin:
            agentes_posibles.append(("Administración pública", *_agente(AdministracionAgent, sectores_admin)))
        if ag_sociedad:
            agentes_posibles.append(("Sociedad civil organizada", *_agente(SociedadAgent, sectores_sociedad)))
        if ag_incub:
            agentes_posibles.append(("Incubadoras y aceleradoras", *_agente(IncubadorasAgent, [])))
        agentes = agentes_posibles

        total_fases = len(agentes) + (len(agentes) if enriquecer else 0) + (1 if usar_coordinador else 0)
        fase_actual = 0

        # ── FASE 1: Búsqueda ──────────────────────────────────────────────
        for i, (nombre, agente, sectores) in enumerate(agentes):
            indicadores[nombre].markdown(f"{ICONOS[nombre]} **{nombre.split()[0]}**\n\n🔄 Buscando...")
            estado_global.info(f"🔍 Buscando actores: **{nombre}**")
            total_encontrados = sum(len(v) for v in resultados.values())
            contador.metric("Actores encontrados", total_encontrados)

            def cb_busqueda(msg, n=nombre):
                detalle.caption(f"→ {msg}")

            n_antes = len(log_busqueda)
            try:
                actores = agente.run(zona_info, sectores, progress_callback=cb_busqueda, log=log_busqueda)
                for entrada in log_busqueda[n_antes:]:
                    entrada["categoria"] = nombre
                resultados[nombre] = actores
                indicadores[nombre].markdown(f"{ICONOS[nombre]} **{nombre.split()[0]}**\n\n✅ {len(actores)} actores")
            except Exception as e:
                st.warning(f"Error en {nombre}: {str(e)}")
                indicadores[nombre].markdown(f"{ICONOS[nombre]} **{nombre.split()[0]}**\n\n⚠️ Error")

            fase_actual += 1
            barra_global.progress(fase_actual / total_fases)
            total_encontrados = sum(len(v) for v in resultados.values())
            contador.metric("Actores encontrados", total_encontrados)

        # ── FASE 2: Enriquecimiento ───────────────────────────────────────
        if enriquecer:
            for i, (nombre, _, _) in enumerate(agentes):
                if nombre not in resultados or not resultados[nombre]:
                    fase_actual += 1
                    barra_global.progress(fase_actual / total_fases)
                    continue
                actores_cat = resultados[nombre]
                total_cat = len(actores_cat)
                estado_global.info(f"📍 Enriqueciendo: **{nombre}**")
                barra_enrich = st.progress(0)
                detalle_enrich = st.empty()

                def cb_enrich(idx, total, actor_nombre, bar=barra_enrich, det=detalle_enrich, n=nombre):
                    pct = int((idx + 1) / total * 100) if total > 0 else 0
                    bar.progress(pct / 100)
                    det.caption(f"→ {n}: {actor_nombre} ({idx+1}/{total})")

                try:
                    resultados[nombre] = enriquecer_lista(
                        actores_cat, nombre, zona_info,
                        opencage_key=opencage_key or None,
                        progress_callback=cb_enrich
                    )
                    barra_enrich.progress(1.0)
                    detalle_enrich.caption(f"✅ {nombre}: {total_cat} actores enriquecidos")
                except Exception as e:
                    st.warning(f"Error enriqueciendo {nombre}: {str(e)}")

                fase_actual += 1
                barra_global.progress(fase_actual / total_fases)

        # ── FASE 3: Coordinador ───────────────────────────────────────────
        if usar_coordinador:
            estado_global.info("🔄 Coordinador revisando clasificaciones...")
            detalle.caption("→ Revisando actores mal clasificados entre categorías...")
            try:
                resultados = coordinar(resultados, provider, api_key)
                detalle.caption("→ Clasificaciones corregidas")
            except Exception as e:
                st.warning(f"Error en coordinador: {str(e)}")
            fase_actual += 1
            barra_global.progress(fase_actual / total_fases)

        barra_global.progress(1.0)
        if tokens_agotados:
            estado_global.warning(f"⚠️ Búsqueda incompleta — tokens diarios agotados al llegar a **{categoria_parada}**. Descarga el Excel con los resultados parciales.")
        else:
            estado_global.success("✅ Búsqueda completada")
        detalle.empty()

        total_final = sum(len(v) for v in resultados.values())
        contador.metric("Actores encontrados", total_final)

        # ── RESULTADOS ────────────────────────────────────────────────────
        st.header("Resultados")

        cats_list = list(resultados.items())
        cols = st.columns(len(cats_list))
        for idx, (cat, actores) in enumerate(cats_list):
            ico = ICONOS.get(cat, "📋")
            cols[idx].metric(f"{ico} {cat.split()[0]}", len(actores))

        for categoria, actores in resultados.items():
            ico = ICONOS.get(categoria, "📋")
            with st.expander(f"{ico} {categoria} — {len(actores)} actores"):
                if actores:
                    st.dataframe(actores, use_container_width=True)
                else:
                    st.caption("No se encontraron actores.")

        # ── DESCARGA ──────────────────────────────────────────────────────
        st.divider()
        fecha = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_zona = zona_info.get("nombre", "zona").replace(" ", "_")
        # Añadir categoría a entradas de log sin ella
        for entrada in log_busqueda:
            if "categoria" not in entrada:
                entrada["categoria"] = ""
        meta_busqueda["tokens_agotados"] = tokens_agotados
        meta_busqueda["categoria_parada"] = categoria_parada
        excel_bytes = exportar_excel(resultados, zona_info.get("display", nombre_zona), log=log_busqueda, meta=meta_busqueda)

        import zipfile, io as _io
        html_content = exportar_html(resultados, zona_info.get("display", nombre_zona), meta=meta_busqueda)
        nombre_html = f"ecosistema_{nombre_zona}_{fecha}.html"
        nombre_xlsx = f"ecosistema_{nombre_zona}_{fecha}.xlsx"

        zip_buffer = _io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(nombre_xlsx, excel_bytes)
            zf.writestr(nombre_html, html_content.encode("utf-8"))
        zip_buffer.seek(0)

        st.download_button(
            label="📦 Descargar Excel + Dashboard HTML",
            data=zip_buffer.getvalue(),
            file_name=f"ecosistema_{nombre_zona}_{fecha}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )
        st.caption("💡 Descomprime el ZIP. Abre el .html en el navegador para los dashboards interactivos y el .xlsx para los datos completos.")
