# Mapeador de ecosistemas territoriales

Agente de IA que investiga actores de un ecosistema territorial y exporta los resultados a Excel.

## Qué hace

1. El usuario define una zona geográfica (barrio, ciudad, región...)
2. Selecciona sectores prioritarios por categoría
3. El agente busca en internet y clasifica los actores en 4 categorías:
   - Empresas privadas (por sectores)
   - Academia (universidades, centros I+D, FP)
   - Administración pública (ayuntamientos, entidades públicas)
   - Sociedad civil organizada (ONGs, asociaciones, fundaciones)
4. Descarga un Excel con una hoja por categoría

## Cómo subir a Streamlit Cloud (para compartir con cualquiera)

### 1. Sube el código a GitHub

- Crea un repositorio nuevo en github.com (público o privado)
- Sube todos los archivos de esta carpeta

### 2. Crea una cuenta en Streamlit Cloud

- Ve a share.streamlit.io
- Inicia sesión con tu cuenta de GitHub

### 3. Despliega la app

- Haz clic en "New app"
- Selecciona tu repositorio
- En "Main file path" escribe: `app.py`
- Haz clic en "Deploy"

En 2-3 minutos tendrás una URL pública que puedes compartir con quien quieras.

## Cómo ejecutarlo en local (para desarrollo)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## API Keys necesarias

### Obligatoria (elige una)
- **Groq** (gratuito): https://console.groq.com — crea cuenta y genera API key
- **Google Gemini** (gratuito): https://aistudio.google.com — genera API key
- **OpenAI**: https://platform.openai.com — requiere pago
- **Anthropic**: https://console.anthropic.com — requiere pago

### Opcionales (mejoran la búsqueda)
- **Tavily** (2.500/mes gratis): https://tavily.com
- **Serper** (2.500/mes gratis): https://serper.dev

Sin estas opcionales, la app usa DuckDuckGo que es gratuito e ilimitado (algo más lento).

## Estructura del proyecto

```
ecosystem-mapper/
├── app.py                    # Interfaz Streamlit
├── exporter.py               # Exportador a Excel
├── requirements.txt
├── agents/
│   ├── base_agent.py         # Lógica común
│   ├── empresas_agent.py
│   ├── academia_agent.py
│   ├── administracion_agent.py
│   └── sociedad_agent.py
└── tools/
    ├── search.py             # Motor de búsqueda en cascada
    └── llm.py                # Adaptadores de LLM
```
