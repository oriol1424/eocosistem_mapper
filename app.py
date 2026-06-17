import streamlit as st
import threading
from datetime import datetime

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

# ── SIDEBAR: configuración ──────────────────────────────────────────────────
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

    api_key = st.text_input(
        "Tu API Key",
        type="password",
        placeholder="Pega aquí tu API key...",
        help="Solo se usa durante esta sesión, nunca se guarda."
    )

    st.caption("🔒 La key desaparece al cerrar el navegador.")

    st.divider()

    st.subheader("Búsqueda web (opcional)")
    st.caption("Si no añades keys, se usa DuckDuckGo gratis.")
    tavily_key = st.text_input("Tavily API Key", type="password", placeholder="tvly-...")
    serper_key = st.text_input("Serper API Key", type="password", placeholder="...")

# ── ZONA GEOGRÁFICA ─────────────────────────────────────────────────────────
st.header("1. Define la zona a analizar")

col1, col2 = st.columns([2, 1])
with col1:
    zona = st.text_input(
        "Zona geográfica",
        placeholder="Ej: Eixample Barcelona, Comunidad de Madrid, Tarragona...",
        help="Puedes escribir un barrio, ciudad, comarca, región o país."
    )
with col2:
    nivel = st.selectbox(
        "Nivel de análisis",
        ["Barrio", "Distrito", "Ciudad", "Comarca", "Región", "País"]
    )

# ── SECTORES PRIORITARIOS ───────────────────────────────────────────────────
st.header("2. Sectores prioritarios (opcional)")
st.caption("Deja en blanco para buscar todos los sectores.")

with st.expander("Empresas privadas — sectores a priorizar"):
    sectores_empresas = st.multiselect(
        "Sectores",
        ["Tecnología e innovación", "Salud y farmacia", "Industria y manufactura",
         "Comercio y retail", "Construcción e inmobiliaria", "Servicios profesionales",
         "Energía y medio ambiente", "Turismo y hostelería",
         "Alimentación y agroindustria", "Finanzas y seguros"],
        label_visibility="collapsed"
    )

with st.expander("Academia — tipos a priorizar"):
    sectores_academia = st.multiselect(
        "Tipos",
        ["Universidades", "Centros de investigación", "Formación Profesional",
         "Colegios e institutos", "Centros tecnológicos"],
        label_visibility="collapsed"
    )

with st.expander("Administración pública — tipos a priorizar"):
    sectores_admin = st.multiselect(
        "Tipos",
        ["Ayuntamientos", "Diputaciones y consejos comarcales",
         "Empresas públicas", "Agencias de desarrollo", "Servicios sociales públicos"],
        label_visibility="collapsed"
    )

with st.expander("Sociedad civil — tipos a priorizar"):
    sectores_sociedad = st.multiselect(
        "Tipos",
        ["ONGs", "Asociaciones vecinales", "Fundaciones",
         "Asociaciones culturales", "Cooperativas"],
        label_visibility="collapsed"
    )

# ── BOTÓN Y EJECUCIÓN ───────────────────────────────────────────────────────
st.divider()

if st.button("Iniciar búsqueda", type="primary", use_container_width=True):
    if not zona:
        st.error("Por favor, escribe una zona geográfica.")
    elif not api_key:
        st.error("Por favor, añade tu API key en la barra lateral.")
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

            def cb(msg, nom=nombre):
                log.caption(f"{nom}: {msg}")

            try:
                actores = agente.run(zona, nivel, sectores, progress_callback=cb)
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
        categorias = list(resultados.keys())
        for idx, col in enumerate(cols):
            with col:
                cat = categorias[idx]
                col.metric(cat, len(resultados[cat]))

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

        # ── DESCARGA EXCEL ──────────────────────────────────────────────────
        st.divider()
        fecha = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_archivo = f"ecosistema_{zona.replace(' ', '_')}_{fecha}.xlsx"

        excel_bytes = exportar_excel(resultados, zona)

        st.download_button(
            label="Descargar Excel",
            data=excel_bytes,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
