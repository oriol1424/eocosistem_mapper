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

# ── SECTORES ─────────────────────────────────────────────────────────────────
st.header("2. Sectores prioritarios (opcional)")

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
        meta_busqueda = {
            "zona": zona_info.get("display", ""),
            "fecha": dt.now().strftime("%d/%m/%Y %H:%M"),
            "provider": provider,
            "motor": "Serper" if serper_key else ("Tavily" if tavily_key else "DuckDuckGo"),
        }

        agentes = [
            ("Empresas privadas",
             EmpresasAgent(provider, api_key, tavily_key or None, serper_key or None),
             sectores_empresas),
            ("Academia",
             AcademiaAgent(provider, api_key, tavily_key or None, serper_key or None),
             sectores_academia),
            ("Administración pública",
             AdministracionAgent(provider, api_key, tavily_key or None, serper_key or None),
             sectores_admin),
            ("Sociedad civil organizada",
             SociedadAgent(provider, api_key, tavily_key or None, serper_key or None),
             sectores_sociedad),
            ("Incubadoras y aceleradoras",
             IncubadorasAgent(provider, api_key, tavily_key or None, serper_key or None),
             []),
        ]

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

        # ── FASE 2: Coordinador ───────────────────────────────────────────
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

        # ── FASE 3: Enriquecimiento ───────────────────────────────────────
        if enriquecer:
            for i, (nombre, _, _) in enumerate(agentes):
                estado_global.info(f"📍 Enriqueciendo direcciones: **{nombre}**")
                actores_cat = resultados[nombre]
                total_cat = len(actores_cat)

                def cb_enrich(idx, total, actor_nombre, n=nombre):
                    pct = int((idx / total * 100)) if total > 0 else 0
                    detalle.caption(f"→ {n}: {actor_nombre} ({idx}/{total})")

                try:
                    resultados[nombre] = enriquecer_lista(
                        actores_cat, nombre, zona_info,
                        opencage_key=opencage_key or None,
                        progress_callback=cb_enrich
                    )
                except Exception as e:
                    st.warning(f"Error enriqueciendo {nombre}: {str(e)}")

                fase_actual += 1
                barra_global.progress(fase_actual / total_fases)

        barra_global.progress(1.0)
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
        excel_bytes = exportar_excel(resultados, zona_info.get("display", nombre_zona), log=log_busqueda, meta=meta_busqueda)

        st.download_button(
            label="📥 Descargar Excel",
            data=excel_bytes,
            file_name=f"ecosistema_{nombre_zona}_{fecha}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
