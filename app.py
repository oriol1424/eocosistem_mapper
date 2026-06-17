import streamlit as st
from datetime import datetime
from tools.geo import buscar_zonas
from agents.empresas_agent import EmpresasAgent
from agents.academia_agent import AcademiaAgent
from agents.administracion_agent import AdministracionAgent
from agents.sociedad_agent import SociedadAgent
from exporter import exportar_excel

st.set_page_config(
    page_title="Mapeador de Ecosistemas",
    page_icon="🗺️",
    layout="wide"
)

st.title("Mapeador de ecosistemas territoriales")
st.caption("Analiza actores de un territorio y exporta los resultados a Excel")

# ── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuración")

    st.subheader("Proveedor de IA")
    provider = st.selectbox(
        "Selecciona tu proveedor",
        ["groq", "openai", "gemini", "anthropic"],
        format_func=lambda x: {
            "groq": "Groq (gratuito)",
            "openai": "OpenAI",
            "gemini": "Google Gemini (gratuito)",
            "anthropic": "Anthropic / Claude"
        }[x]
    )
    api_key = st.text_input("Tu API Key", type="password", placeholder="Pega aquí tu API key...")
    st.caption("🔒 Solo se usa en esta sesión, nunca se guarda.")

    st.divider()
    st.subheader("Búsqueda web (opcional)")
    st.caption("Sin keys usa DuckDuckGo gratis.")
    tavily_key = st.text_input("Tavily API Key", type="password", placeholder="tvly-...")
    serper_key = st.text_input("Serper API Key", type="password", placeholder="...")

# ── ZONA GEOGRÁFICA CON AUTOCOMPLETE ────────────────────────────────────────
st.header("1. Define la zona a analizar")

if "zona_info" not in st.session_state:
    st.session_state.zona_info = None
if "zona_texto" not in st.session_state:
    st.session_state.zona_texto = ""

col1, col2 = st.columns([3, 1])
with col1:
    texto_zona = st.text_input(
        "Escribe una zona geográfica",
        placeholder="Ej: Montcada, Paraíba, Gràcia...",
        value=st.session_state.zona_texto,
        help="Escribe al menos 3 letras para ver sugerencias."
    )

opciones = []
if len(texto_zona) >= 3:
    with st.spinner("Buscando zonas..."):
        opciones = buscar_zonas(texto_zona)

if opciones:
    labels = [f"{o['display']}  [{o['nivel']}]" for o in opciones]
    labels.insert(0, "— Selecciona una opción —")
    seleccion = st.selectbox("Selecciona la zona exacta", labels)

    if seleccion != "— Selecciona una opción —":
        idx = labels.index(seleccion) - 1
        st.session_state.zona_info = opciones[idx]
        zona_info = opciones[idx]

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Nivel detectado", zona_info["nivel"])
        col_b.metric("País", zona_info["pais"])
        col_c.metric("Idioma de búsqueda", zona_info["idioma"].upper())
    else:
        zona_info = None
elif len(texto_zona) >= 3:
    st.info("No se encontraron zonas. Prueba con otro nombre.")
    zona_info = None
else:
    zona_info = st.session_state.zona_info

# ── SECTORES ────────────────────────────────────────────────────────────────
st.header("2. Sectores prioritarios (opcional)")
st.caption("Deja en blanco para buscar todos los sectores.")

with st.expander("Empresas privadas — sectores a priorizar"):
    sectores_empresas = st.multiselect(
        "Sectores empresas",
        ["Tecnología e innovación", "Salud y farmacia", "Industria y manufactura",
         "Comercio y retail", "Construcción e inmobiliaria", "Servicios profesionales",
         "Energía y medio ambiente", "Turismo y hostelería",
         "Alimentación y agroindustria", "Finanzas y seguros"],
        label_visibility="collapsed"
    )

with st.expander("Academia — tipos a priorizar"):
    sectores_academia = st.multiselect(
        "Tipos academia",
        ["Universidades", "Centros de investigación", "Formación Profesional",
         "Colegios e institutos", "Centros tecnológicos"],
        label_visibility="collapsed"
    )

with st.expander("Administración pública — tipos a priorizar"):
    sectores_admin = st.multiselect(
        "Tipos administración",
        ["Ayuntamientos", "Diputaciones y consejos comarcales",
         "Empresas públicas", "Agencias de desarrollo", "Servicios sociales públicos"],
        label_visibility="collapsed"
    )

with st.expander("Sociedad civil — tipos a priorizar"):
    sectores_sociedad = st.multiselect(
        "Tipos sociedad civil",
        ["ONGs", "Asociaciones vecinales", "Fundaciones",
         "Asociaciones culturales", "Cooperativas"],
        label_visibility="collapsed"
    )

# ── LANZAR BÚSQUEDA ─────────────────────────────────────────────────────────
st.divider()

if st.button("Iniciar búsqueda", type="primary", use_container_width=True):
    if not zona_info:
        st.error("Selecciona una zona del desplegable antes de buscar.")
    elif not api_key:
        st.error("Añade tu API key en la barra lateral.")
    else:
        resultados = {
            "Empresas privadas": [],
            "Academia": [],
            "Administración pública": [],
            "Sociedad civil organizada": []
        }

        progreso = st.progress(0)
        estado = st.empty()
        log = st.empty()

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
        ]

        for i, (nombre, agente, sectores) in enumerate(agentes):
            estado.info(f"Analizando: **{nombre}** ({i+1}/4)")

            def cb(msg):
                log.caption(f"Buscando: {msg}")

            try:
                actores = agente.run(zona_info, sectores, progress_callback=cb)
                resultados[nombre] = actores
            except Exception as e:
                st.warning(f"Error en {nombre}: {str(e)}")

            progreso.progress((i + 1) / 4)

        estado.success("Búsqueda completada")
        log.empty()

        # ── RESULTADOS ──────────────────────────────────────────────────────
        st.header("Resultados")
        total = sum(len(v) for v in resultados.values())
        st.metric("Total de actores encontrados", total)

        cols = st.columns(4)
        for idx, (cat, actores) in enumerate(resultados.items()):
            cols[idx].metric(cat, len(actores))

        for categoria, actores in resultados.items():
            with st.expander(f"{categoria} — {len(actores)} actores"):
                if actores:
                    st.dataframe(
                        actores,
                        use_container_width=True,
                        column_config={
                            "nombre": "Nombre",
                            "tipo": "Tipo",
                            "sector": "Sector",
                            "descripcion": "Descripción",
                            "web": st.column_config.LinkColumn("Web"),
                            "ubicacion": "Ubicación",
                            "contacto": "Contacto",
                            "categoria": None
                        }
                    )
                else:
                    st.caption("No se encontraron actores.")

        st.divider()
        fecha = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_zona = zona_info.get("nombre", "zona").replace(" ", "_")
        nombre_archivo = f"ecosistema_{nombre_zona}_{fecha}.xlsx"
        excel_bytes = exportar_excel(resultados, zona_info.get("display", nombre_zona))

        st.download_button(
            label="Descargar Excel",
            data=excel_bytes,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
