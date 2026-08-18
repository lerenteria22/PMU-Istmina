import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import re
import unicodedata
from datetime import datetime

# ===================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS (FLEXDASHBOARD FLATLY)
# ===================================================================
st.set_page_config(
    page_title="PMU - Sala de Crisis Istmina",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    /* Fondo general claro Flexdashboard */
    .stApp { background-color: #eaeded !important; color: #2c3e50 !important; font-family: 'Lato', 'Helvetica Neue', Arial, sans-serif !important; }
    header {visibility: hidden !important;}
    .block-container { padding-top: 0rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; max-width: 100% !important; }
    
    /* BARRA SUPERIOR TURQUESA (Header) */
    .pmu-navbar { background-color: #1abc9c !important; color: #ffffff !important; padding: 14px 20px !important; margin-bottom: 0px !important; font-size: 22px !important; font-weight: 700 !important; letter-spacing: 0.5px !important; }
    
    /* BARRA DE NAVEGACIÓN Y PESTAÑAS */
    .stTabs [data-baseweb="tab-list"] { background-color: #1abc9c !important; padding: 0px 15px 4px 15px !important; gap: 4px !important; border-bottom: none !important; }
    .stTabs [data-baseweb="tab"] { background-color: #1abc9c !important; border: none !important; padding: 10px 18px !important; border-radius: 4px 4px 0 0 !important; }
    .stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] span, .stTabs [data-baseweb="tab"] div { color: #ffffff !important; font-weight: 700 !important; font-size: 14px !important; opacity: 0.95 !important; }
    .stTabs [aria-selected="true"] { background-color: #16a085 !important; border-bottom: 4px solid #f1c40f !important; }
    .stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] span, .stTabs [aria-selected="true"] div { color: #ffffff !important; opacity: 1.0 !important; }
    
    /* SUB-PESTAÑAS INTERNAS */
    div[data-testid="stTab"] button p { color: #2c3e50 !important; font-weight: 700 !important; }
    
    /* ESTILO INTEGRADO PARA TODOS LOS BOTONES */
    div.stButton > button, div.stButton > button:focus, div.stButton > button:active { background-color: #1abc9c !important; color: #ffffff !important; border: none !important; border-radius: 4px !important; font-weight: 700 !important; font-size: 14px !important; padding: 8px 16px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; transition: all 0.2s ease-in-out !important; }
    div.stButton > button:hover { background-color: #16a085 !important; color: #ffffff !important; box-shadow: 0 3px 6px rgba(0,0,0,0.15) !important; }
    div.stButton > button p, div.stButton > button span { color: #ffffff !important; font-weight: 700 !important; }
    
    /* TEXTOS OSCUROS EN CONTENEDORES */
    div[data-testid="stVerticalBlock"] p, div[data-testid="stVerticalBlock"] span, div[data-testid="stVerticalBlock"] label, [data-testid="stWidgetLabel"] p, .chart-title { color: #2c3e50 !important; font-weight: 700 !important; }
    
    /* TABLAS BLANCAS CON TEXTO OSCURO */
    div[data-testid="stDataFrame"], div[data-testid="stTable"], div[data-testid="stDataFrame"] div, [data-testid="stElementToolbar"] { background-color: #ffffff !important; color: #2c3e50 !important; }
    
    /* CORRECCIÓN DE CONTRASTE Y LEGIBILIDAD EN DESPLEGABLES (SELECT & MULTISELECT) */
    div[data-baseweb="select"] > div { background-color: #ffffff !important; color: #2c3e50 !important; border: 1px solid #bdc3c7 !important; border-radius: 4px !important; }
    div[data-baseweb="select"] span, div[data-baseweb="select"] div, div[data-baseweb="select"] input { color: #2c3e50 !important; font-weight: 600 !important; }
    div[data-baseweb="popover"], div[data-baseweb="popover"] * { background-color: #ffffff !important; color: #2c3e50 !important; }
    li[role="option"] { background-color: #ffffff !important; color: #2c3e50 !important; font-weight: 600 !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background-color: #eaeded !important; color: #16a085 !important; }
    span[data-baseweb="tag"] { background-color: #1abc9c !important; }
    span[data-baseweb="tag"] span { color: #ffffff !important; font-weight: 700 !important; }

    /* TARJETAS VALUEBOX */
    .value-box { border-radius: 4px; padding: 15px 20px; color: white !important; position: relative; overflow: hidden; min-height: 95px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .value-box-num { font-size: 38px; font-weight: 800; line-height: 1; margin-bottom: 4px; color: white !important; }
    .value-box-title { font-size: 13px; font-weight: 600; opacity: 0.95; color: white !important; }
    .value-box-icon { position: absolute; right: 15px; top: 50%; transform: translateY(-50%); font-size: 50px; opacity: 0.22; color: white !important; }
    
    /* CONTENEDORES BLANCOS DE GRÁFICOS */
    div[data-testid="stVerticalBlock"] > div[data-testid="stBlock"] { background-color: #ffffff !important; border-radius: 4px; padding: 12px; border: 1px solid #dce4ec; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .chart-title { color: #2c3e50 !important; font-weight: 700; font-size: 15px; margin-bottom: 8px; display: block; }
</style>
""", unsafe_allow_html=True)

# Control de Autenticación
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if "expediente_buscado" not in st.session_state:
    st.session_state["expediente_buscado"] = ""

if not st.session_state["autenticado"]:
    st.markdown('<div class="pmu-navbar">🚨 PMU - Sala de Crisis Istmina</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    clave = st.text_input("Ingrese la clave de acceso para continuar:", type="password")
    if st.button("Ingresar"):
        if clave == "Istmina2026":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    st.stop()

# Helper para ValueBoxes
def render_value_box(numero, titulo, color_bg, icono_fa):
    st.markdown(f"""
    <div class="value-box" style="background-color: {color_bg};">
        <div>
            <div class="value-box-num">{numero}</div>
            <div class="value-box-title">{titulo}</div>
        </div>
        <i class="fa-solid {icono_fa} value-box-icon"></i>
    </div>
    """, unsafe_allow_html=True)

# Estilizado estricto para gráficos de Plotly
def aplicar_estilo_plotly(fig, height=350):
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#2c3e50", family="sans-serif", size=12),
        margin=dict(l=10, r=10, t=30, b=40),
        height=height,
        xaxis=dict(gridcolor="#e5e8e8", zerolinecolor="#e5e8e8", tickfont=dict(color="#2c3e50"), title_font=dict(color="#2c3e50", size=13), automargin=True),
        yaxis=dict(gridcolor="#e5e8e8", zerolinecolor="#e5e8e8", tickfont=dict(color="#2c3e50"), title_font=dict(color="#2c3e50", size=13), automargin=True),
        legend=dict(font=dict(color="#2c3e50", size=11), bgcolor="rgba(255,255,255,0.9)")
    )
    return fig

# ===================================================================
# 2. CARGA Y TRATAMIENTO DE DATOS CON DEPURACIÓN RIGUROSA DE DUPLICADOS
# ===================================================================
def clean_col(name):
    name = unicodedata.normalize('NFD', str(name))
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name

def buscar_columna(df_cols, palabras_clave):
    for col in df_cols:
        if any(kw in col for kw in palabras_clave):
            return col
    return None

def check_cond_cols(df, palabras_clave, valores_objetivo):
    cols_coincidentes = [c for c in df.columns if any(kw in c for kw in palabras_clave)]
    if not cols_coincidentes:
        return pd.Series(False, index=df.index)
    return df[cols_coincidentes].isin(valores_objetivo).any(axis=1)

@st.cache_data(ttl=30)
def cargar_datos():
    url_csv = "https://docs.google.com/spreadsheets/d/1UyHaV3J-MJ3lMnQs5lnPGIdGMTn591Tsz1aZ9_E1Z8g/gviz/tq?tqx=out:csv&sheet=Hoja%201"
    try:
        df_bruto = pd.read_csv(url_csv)
        df_bruto.columns = [clean_col(c) for c in df_bruto.columns]
    except Exception:
        df_bruto = pd.DataFrame()

    if not df_bruto.empty and len(df_bruto) > 0:
        df = df_bruto.copy()
    else:
        df = pd.DataFrame({
            "marca_temporal": ["2026-08-14 08:30:00", "2026-08-14 10:15:00", "2026-08-14 14:20:00"],
            "barrio_vereda": ["Cubis", "Comercio", "Independencia"],
            "clasificacion_habitabilidad": ["Riesgo de colapso", "Habitable", "No habitable"],
            "total_habitantes": [5, 3, 4], "ninos": [2, 0, 1], "adultos_mayores": [1, 0, 1],
            "n_personas_discapacidad": [0, 1, 0], "n_mujeres_embarazadas": [1, 0, 0],
            "coordenadas_gps": ["5.161,-76.681", "5.165,-76.675", "5.158,-76.685"],
            "nombre_propietario": ["Carlos Pérez", "María López", "Juan Gómez"],
            "telefono": ["3101234567", "3119876543", "3125554433"],
            "documento": ["10751234", "35876543", "11125554"],
            "necesidades_inmediatas": ["Cubierta, Agua", "Materiales", "Reparación de muros"],
            "fotos": ["https://google.com", "", ""]
        })

    col_barrio = buscar_columna(df.columns, ["barrio", "vereda"]) or "barrio_vereda"
    col_habitabilidad = buscar_columna(df.columns, ["habitabilidad", "clasificacion"]) or "clasificacion_habitabilidad"
    col_habitantes = buscar_columna(df.columns, ["total_habitantes", "habitantes", "personas"]) or "total_habitantes"
    col_ninos = buscar_columna(df.columns, ["ninos", "ninase"]) or "ninos"
    col_mayores = buscar_columna(df.columns, ["adultos_mayores", "mayores", "ancianos"]) or "adultos_mayores"
    col_discap = buscar_columna(df.columns, ["discapacidad"]) or "n_personas_discapacidad"
    col_embaraz = buscar_columna(df.columns, ["embarazada", "gestante"]) or "n_mujeres_embarazadas"
    col_propietario = buscar_columna(df.columns, ["propietario", "nombre", "afectado"]) or "nombre_propietario"
    col_telefono = buscar_columna(df.columns, ["telefono", "celular", "contacto"]) or "telefono"
    col_documento = buscar_columna(df.columns, ["documento", "cedula", "identificacion", "id", "cc"]) or "documento"
    col_necesidades = buscar_columna(df.columns, ["necesidad", "requiere"]) or "necesidades_inmediatas"
    col_coords = buscar_columna(df.columns, ["coordenadas", "gps", "ubicacion"]) or "coordenadas_gps"

    col_fotos = df.columns[1] if len(df.columns) > 1 else "fotos"

    df["barrio_vereda"] = df[col_barrio].fillna("No registrado").astype(str) if col_barrio in df.columns else "No registrado"
    df["clasificacion_habitabilidad"] = df[col_habitabilidad].fillna("Sin Clasificar").astype(str) if col_habitabilidad in df.columns else "Sin Clasificar"
    df["total_habitantes"] = pd.to_numeric(df[col_habitantes], errors='coerce').fillna(0).astype(int) if col_habitantes in df.columns else 0
    df["ninos"] = pd.to_numeric(df[col_ninos], errors='coerce').fillna(0).astype(int) if col_ninos in df.columns else 0
    df["adultos_mayores"] = pd.to_numeric(df[col_mayores], errors='coerce').fillna(0).astype(int) if col_mayores in df.columns else 0
    df["n_personas_discapacidad"] = pd.to_numeric(df[col_discap], errors='coerce').fillna(0).astype(int) if col_discap in df.columns else 0
    df["n_mujeres_embarazadas"] = pd.to_numeric(df[col_embaraz], errors='coerce').fillna(0).astype(int) if col_embaraz in df.columns else 0
    df["nombre_propietario"] = df[col_propietario].fillna("No registrado").astype(str) if col_propietario in df.columns else "No registrado"
    df["necesidades_inmediatas"] = df[col_necesidades].fillna("Sin especificación").astype(str) if col_necesidades in df.columns else "Sin especificación"
    df["fotos"] = df[col_fotos].fillna("").astype(str) if col_fotos in df.columns else ""

    if col_telefono in df.columns:
        df["telefono"] = df[col_telefono].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', 'No registrado')
    else:
        df["telefono"] = "No registrado"
        
    if col_documento in df.columns:
        df["documento"] = df[col_documento].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', 'No registrado')
    else:
        df["documento"] = "No registrado"

    col_fecha = buscar_columna(df.columns, ["marca_temporal", "timestamp", "fecha"])
    if col_fecha and col_fecha in df.columns:
        df["fecha_corta"] = pd.to_datetime(df[col_fecha], errors='coerce').dt.date.fillna(datetime.now().date())
    else:
        df["fecha_corta"] = datetime.now().date()

    if col_coords and col_coords in df.columns:
        coords = df[col_coords].astype(str).str.split(",", expand=True)
        df["lat"] = pd.to_numeric(coords[0], errors='coerce').fillna(5.161)
        df["lon"] = pd.to_numeric(coords[1], errors='coerce').fillna(-76.681)
    else:
        df["lat"] = 5.161
        df["lon"] = -76.681

    def estandarizar_barrio(txt):
        txt = str(txt).lower().strip()
        if re.search(r"eduardo|santo|pep", txt): return "Eduardo Santos (La Pepé)"
        elif re.search(r"cubi|70|setenta|genoveva|lavander|chambl", txt): return "Cubis"
        elif re.search(r"camell|camelo", txt): return "Camellón"
        elif re.search(r"comerci|comers", txt): return "Comercio"
        elif re.search(r"ofel|offel", txt): return "Offel"
        elif re.search(r"independencia|valdes|valdés|valdez", txt): return "Independencia"
        elif re.search(r"diego|luis", txt): return "Diego Luis"
        elif re.search(r"carretera|carrete|san francisco|francisco", txt): return "Carretera (San Francisco)"
        elif re.search(r"agust", txt): return "San Agustín"
        elif re.search(r"pueblo|nuevo|meseta", txt): return "Pueblo Nuevo"
        return txt.title() if txt not in ["nan", ""] else "No Registrado"

    def estandarizar_sector(txt):
        txt = str(txt).lower().strip()
        if "genoveva" in txt: return "Santa Genoveva"
        elif "meseta" in txt: return "La Meseta"
        elif re.search(r"lavanderia|lavandería|lavander", txt): return "Lavandería"
        elif re.search(r"\b70\b|la 70|setenta", txt): return "La 70"
        elif re.search(r"antuco|chorro", txt): return "Chorro de Antuco"
        elif re.search(r"chamblun|chamblún|chambl", txt): return "Chamblún"
        return "Sin Sector Específico"

    df["barrio_estandar"] = df["barrio_vereda"].apply(estandarizar_barrio)
    df["sector_especifico"] = df["barrio_vereda"].apply(estandarizar_sector)

    # -------------------------------------------------------------------
    # FILTRO AVANZADO DE ENTRADAS REPETIDAS (DEPURACIÓN ESTRUCTURADA)
    # -------------------------------------------------------------------
    # 1. Conservar el registro más reciente si coincide el documento de identidad
    mask_doc_valido = (df["documento"] != "No registrado") & (df["documento"] != "") & (df["documento"] != "0")
    df_con_doc = df[mask_doc_valido].drop_duplicates(subset=["documento"], keep="last")
    df_sin_doc = df[~mask_doc_valido]
    
    # 2. Para registros sin documento, depurar por Propietario + Barrio
    df_sin_doc = df_sin_doc.drop_duplicates(subset=["nombre_propietario", "barrio_estandar"], keep="last")
    
    # 3. Consolidar el dataframe limpio
    df = pd.concat([df_con_doc, df_sin_doc]).sort_index().reset_index(drop=True)

    colores_hab = {
        "Habitable": "#27ae60",
        "Habitable con restricciones": "#f1c40f",
        "No evaluado": "#3498db",
        "No habitable": "#e74c3c",
        "Riesgo de colapso": "#8e44ad",
        "Sin Clasificar": "#95a5a6",
        "No registrado": "#95a5a6"
    }

    df["color_riesgo"] = df["clasificacion_habitabilidad"].map(colores_hab).fillna("#95a5a6")

    def crear_btn_foto(foto):
        foto = str(foto).strip()
        urls = re.findall(r'(https?://[^\s]+)', foto)
        if urls:
            link_real = urls[0].replace('"', '').replace("'", "")
            return f"<a href='{link_real}' target='_blank' style='display:inline-block; padding:4px 8px; background:#2980b9; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;'>Ver Evidencia</a>"
        
        if "www." in foto:
            urls_www = re.findall(r'(www\.[^\s]+)', foto)
            if urls_www:
                link_real = "https://" + urls_www[0].replace('"', '').replace("'", "")
                return f"<a href='{link_real}' target='_blank' style='display:inline-block; padding:4px 8px; background:#2980b9; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;'>Ver Evidencia</a>"
                
        return "<span style='color:gray; font-size:11px;'>Sin evidencia</span>"

    df["btn_foto"] = df["fotos"].apply(crear_btn_foto)

    nec_str = df["necesidades_inmediatas"].astype(str).str.lower()
    df["nec_cubierta"] = nec_str.str.contains("cubierta").astype(int)
    df["nec_materiales"] = nec_str.str.contains("materiales").astype(int)
    df["nec_muros"] = nec_str.str.contains("muros").astype(int)
    df["nec_estructura"] = nec_str.str.contains("estructural").astype(int)
    df["nec_agua"] = nec_str.str.contains("agua").astype(int)
    df["nec_alojamiento"] = nec_str.str.contains("alojamiento").astype(int)
    df["nec_alimento"] = nec_str.str.contains("alimenta").astype(int)

    val_criticos = ["Severo", "Colapso", "Si", "Sí", "si", "sí"]
    val_mod_crit = ["Moderado", "Severo", "Colapso", "Si", "Sí", "si", "sí"]

    df["es_riesgo_estructural"] = check_cond_cols(df, ["cimentacion", "columnas", "vigas", "grieta_estructural"], val_criticos)
    df["es_afectacion_cubierta"] = check_cond_cols(df, ["cubierta", "techo"], val_mod_crit)
    df["es_afectacion_muros"] = check_cond_cols(df, ["muros", "fachada", "grieta_muro"], val_mod_crit)
    df["es_colapso"] = check_cond_cols(df, ["dano", "colaps", "parte_colapsada"], ["Colapso"]) | df["clasificacion_habitabilidad"].astype(str).str.contains("colapso", case=False, na=False)

    cols_sev = [c for c in df.columns if c.startswith("dano_")]
    def resumen_danos(row):
        danos = [f"{c.replace('dano_', '').title()} ({row[c]})" for c in cols_sev if row[c] in ["Severo", "Colapso"]]
        return " | ".join(danos) if danos else "Sin daños estructurales críticos"

    df["resumen_danos_criticos"] = df.apply(resumen_danos, axis=1) if cols_sev else "Sin evaluación de daños"
    df["id_casa"] = range(1, len(df) + 1)
    return df, colores_hab

df, colores_habitabilidad = cargar_datos()

if df.empty:
    st.error("No se pudieron cargar los datos de Google Sheets.")
    st.stop()

# ===================================================================
# 3. INTERFAZ SALA DE CRISIS
# ===================================================================
st.markdown('<div class="pmu-navbar">PMU - Sala de Crisis Istmina</div>', unsafe_allow_html=True)
tabs = st.tabs(["Mando Unificado", "Visor Geoespacial", "Análisis de Daños", "Vulnerabilidad", "Logística y Rescate", "Expedientes"])

# -------------------------------------------------------------------
# TAB 1: MANDO UNIFICADO
# -------------------------------------------------------------------
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_value_box(len(df), "Viviendas Evaluadas", "#2c3e50", "fa-house")
    with c2: render_value_box(int(df["clasificacion_habitabilidad"].str.contains("colapso", case=False, na=False).sum()), "Riesgo Inminente (Colapso)", "#8e44ad", "fa-triangle-exclamation")
    with c3: render_value_box(int(df["total_habitantes"].sum()), "Población Total Afectada", "#e67e22", "fa-users")
    with c4: render_value_box(int(df["ninos"].sum() + df["adultos_mayores"].sum() + df["n_personas_discapacidad"].sum() + df["n_mujeres_embarazadas"].sum()), "Población Vulnerable", "#d35400", "fa-child")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<span class="chart-title">Estado de Habitabilidad General</span>', unsafe_allow_html=True)
        df_hab = df["clasificacion_habitabilidad"].value_counts().reset_index()
        df_hab.columns = ["Estado", "Cantidad"]
        fig_hab = px.bar(df_hab, x="Cantidad", y="Estado", orientation='h', color="Estado", color_discrete_map=colores_habitabilidad)
        fig_hab = aplicar_estilo_plotly(fig_hab, height=350)
        fig_hab.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, xaxis_title="Número de Viviendas", yaxis_title="")
        st.plotly_chart(fig_hab, use_container_width=True, theme=None)

    with g2:
        st.markdown('<span class="chart-title">Habitabilidad Consolidada por Barrio</span>', unsafe_allow_html=True)
        df_barrio_cnt = df.groupby('barrio_estandar').size().to_dict()
        df['barrio_etiqueta'] = df['barrio_estandar'].apply(lambda x: f"{x} ({df_barrio_cnt.get(x, 0)})")
        df_barrio = df.groupby(["barrio_etiqueta", "clasificacion_habitabilidad"]).size().reset_index(name="n")
        fig_barrio = px.bar(df_barrio, x="n", y="barrio_etiqueta", color="clasificacion_habitabilidad", orientation='h', color_discrete_map=colores_habitabilidad, labels={"n": "Cantidad de Viviendas", "barrio_etiqueta": ""})
        fig_barrio = aplicar_estilo_plotly(fig_barrio, height=350)
        fig_barrio.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Cantidad de Viviendas", legend_title_text="")
        st.plotly_chart(fig_barrio, use_container_width=True, theme=None)

    st.markdown('<span class="chart-title">Evolución Temporal de Reportes (Línea de Tiempo)</span>', unsafe_allow_html=True)
    df_tiempo = df.groupby("fecha_corta").size().reset_index(name="n")
    fig_tiempo = go.Figure()
    fig_tiempo.add_trace(go.Bar(x=df_tiempo["fecha_corta"], y=df_tiempo["n"], marker_color="#34495e", name="Registros", opacity=0.85))
    fig_tiempo.add_trace(go.Scatter(x=df_tiempo["fecha_corta"], y=df_tiempo["n"], mode="lines+markers", line=dict(color="#e74c3c", width=2.5), marker=dict(size=7, color="#e74c3c"), name="Tendencia"))
    fig_tiempo = aplicar_estilo_plotly(fig_tiempo, height=250)
    fig_tiempo.update_layout(showlegend=False, xaxis_title="Fecha de Registro", yaxis_title="Evaluaciones")
    st.plotly_chart(fig_tiempo, use_container_width=True, theme=None)

# -------------------------------------------------------------------
# TAB 2: VISOR GEOESPACIAL
# -------------------------------------------------------------------
with tabs[1]:
    col_f, col_m = st.columns([45, 55])
    with col_f:
        st.markdown('<span class="chart-title">📍 Filtros Interactivos</span>', unsafe_allow_html=True)
        barrio_sel = st.multiselect("Seleccione Barrio / Vereda:", options=sorted(df["barrio_estandar"].unique()))
        
        st.markdown("**Filtrar por Estado de Habitabilidad:**")
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        ch_hab = fc1.checkbox("Habitable", value=True)
        ch_rest = fc2.checkbox("Hab. c/ restricciones", value=True)
        ch_noeval = fc3.checkbox("No evaluado", value=True)
        ch_nohab = fc4.checkbox("No habitable", value=True)
        ch_colapso = fc5.checkbox("Colapso", value=True)

        estados_filtro = []
        if ch_hab: estados_filtro.append("Habitable")
        if ch_rest: estados_filtro.append("Habitable con restricciones")
        if ch_noeval: estados_filtro.append("No evaluado")
        if ch_nohab: estados_filtro.append("No habitable")
        if ch_colapso: estados_filtro.append("Riesgo de colapso")

        df_m = df.copy()
        if barrio_sel: df_m = df_m[df_m["barrio_estandar"].isin(barrio_sel)]
        if estados_filtro: df_m = df_m[df_m["clasificacion_habitabilidad"].isin(estados_filtro)]

        st.markdown('<span class="chart-title">🗺️ Mapa Interactivo</span>', unsafe_allow_html=True)
        m = folium.Map(location=[5.161, -76.681], zoom_start=14, tiles="CartoDB positron")
        for _, r in df_m.iterrows():
            resumen_d = str(r['resumen_danos_criticos'])[:45]
            necesidad_i = str(r['necesidades_inmediatas'])[:35]
            doc_str = f"({r['documento']})" if r['documento'] != "No registrado" else ""
            html_popup = f"""
            <div style='min-width:180px; font-family:sans-serif;'>
            <h4 style='margin:0 0 5px 0; color:#2c3e50;'>{r['nombre_propietario']} {doc_str}</h4>
            <b>Barrio:</b> {r['barrio_estandar']} ({r['sector_especifico']})<br>
            <b>Estado:</b> <span style='color:{r['color_riesgo']}; font-weight:bold;'>{r['clasificacion_habitabilidad']}</span><br>
            <b>Habitantes:</b> {r['total_habitantes']}<br>
            <hr style='margin:5px 0;'>
            <b>Daños:</b> <span style='color:#e74c3c;'>{resumen_d}</span><br>
            <b>Necesidad:</b> {necesidad_i}<br>
            <b>Teléfono:</b> {r['telefono']}<br><br>
            <div style='text-align:center;'>{r['btn_foto']}</div>
            </div>
            """
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=8, color=r["color_riesgo"],
                fill=True, fill_color=r["color_riesgo"], fill_opacity=0.85,
                popup=folium.Popup(html_popup, max_width=260)
            ).add_to(m)
        st_folium(m, width="100%", height=400, key="mapa_general")

    with col_m:
        sub_tab1, sub_tab2 = st.tabs(["📋 Padrón Filtrado", "📊 Gráfica Viva Barrios"])
        with sub_tab1:
            st.dataframe(df_m[["nombre_propietario", "documento", "barrio_estandar", "clasificacion_habitabilidad", "total_habitantes", "telefono"]], height=480, use_container_width=True)
            propietario_sel = st.selectbox("Seleccionar para expediente:", options=["-- Seleccionar --"] + sorted(df_m["nombre_propietario"].unique().tolist()))
            if propietario_sel != "-- Seleccionar --":
                if st.button("📂 Ver Expediente Completo", key="btn_exp_visor"):
                    st.session_state["expediente_buscado"] = propietario_sel
                    st.success("Expediente cargado. Ve a la pestaña 'Expedientes'.")

        with sub_tab2:
            df_viva = df_m.groupby(["barrio_estandar", "clasificacion_habitabilidad"]).size().reset_index(name="count")
            barrios_orden = df_viva.groupby("barrio_estandar")["count"].sum().sort_values(ascending=False).index.tolist()
            
            fig_viva = px.bar(
                df_viva, x="barrio_estandar", y="count", color="clasificacion_habitabilidad",
                color_discrete_map=colores_habitabilidad,
                category_orders={
                    "barrio_estandar": barrios_orden,
                    "clasificacion_habitabilidad": ["Habitable", "Habitable con restricciones", "No evaluado", "No habitable", "Riesgo de colapso"]
                },
                labels={"barrio_estandar": "", "count": "Cantidad de Viviendas Filtradas", "clasificacion_habitabilidad": ""}
            )
            fig_viva = aplicar_estilo_plotly(fig_viva, height=480)
            fig_viva.update_layout(barmode="stack", xaxis=dict(tickangle=-30), yaxis_title="Cantidad de Viviendas Filtradas", legend=dict(traceorder="reversed"))
            st.plotly_chart(fig_viva, use_container_width=True, theme=None)

# -------------------------------------------------------------------
# TAB 3: ANÁLISIS DE DAÑOS
# -------------------------------------------------------------------
with tabs[2]:
    d1, d2, d3, d4 = st.columns(4)
    with d1: render_value_box(int(df["es_riesgo_estructural"].sum()), "Riesgo Estructural Crítico", "#e74c3c", "fa-building")
    with d2: render_value_box(int(df["es_afectacion_cubierta"].sum()), "Afectación en Cubiertas", "#d35400", "fa-house")
    with d3: render_value_box(int(df["es_afectacion_muros"].sum()), "Afectación Muros / Fachada", "#f39c12", "fa-border-all")
    with d4: render_value_box(int(df["es_colapso"].sum()), "Viviendas con Colapso", "#8e44ad", "fa-circle-exclamation")

    sub_d1, sub_d2 = st.tabs(["📊 Gráficas de Daño", "🗺️ Mapa de Afectaciones"])
    
    with sub_d1:
        cd1, cd2 = st.columns(2)
        with cd1:
            st.markdown('<span class="chart-title">Severidad por Elemento</span>', unsafe_allow_html=True)
            cols_d = [c for c in df.columns if c.startswith("dano_")]
            if cols_d:
                df_sev = df[cols_d].melt(var_name="Elemento", value_name="Nivel")
                df_sev = df_sev[df_sev["Nivel"].isin(["Leve", "Moderado", "Severo", "Colapso"])]
                if not df_sev.empty:
                    df_sev["Elemento"] = df_sev["Elemento"].str.replace("dano_", "").str.title()
                    colores_dano = {"Leve": "#f1c40f", "Moderado": "#e67e22", "Severo": "#e74c3c", "Colapso": "#8e44ad"}
                    fig_sev = px.bar(df_sev.groupby(["Elemento", "Nivel"]).size().reset_index(name="n"), x="n", y="Elemento", color="Nivel", orientation='h', color_discrete_map=colores_dano)
                    fig_sev = aplicar_estilo_plotly(fig_sev, height=350)
                    fig_sev.update_layout(xaxis_title="", yaxis_title="")
                    st.plotly_chart(fig_sev, use_container_width=True, theme=None)

        with cd2:
            st.markdown('<span class="chart-title">Señales Visibles Frecuentes</span>', unsafe_allow_html=True)
            cols_sn = [c for c in df.columns if any(p in c for p in ["grieta", "desprendimiento", "inclinacion", "colaps"])]
            if cols_sn:
                df_sn = df[cols_sn].melt(var_name="Alerta", value_name="Resp")
                df_sn = df_sn[df_sn["Resp"].astype(str).str.lower().str.contains("si|sí")]
                if not df_sn.empty:
                    df_sn["Alerta"] = df_sn["Alerta"].str.replace("_", " ").str.title()
                    fig_sn = px.bar(df_sn["Alerta"].value_counts().reset_index(name="n"), x="n", y="Alerta", orientation='h', color_discrete_sequence=["#34495e"])
                    fig_sn = aplicar_estilo_plotly(fig_sn, height=350)
                    fig_sn.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
                    st.plotly_chart(fig_sn, use_container_width=True, theme=None)

    with sub_d2:
        col_dfiltros, col_dmapa = st.columns([3, 7])
        with col_dfiltros:
            st.markdown('<span class="chart-title">Filtros de Afectación</span>', unsafe_allow_html=True)
            b_dano = st.multiselect("Seleccione Barrio:", options=sorted(df["barrio_estandar"].unique()), key="bd_dano")
            s_dano = st.multiselect("Seleccione Sector:", options=sorted(df["sector_especifico"].unique()), key="sd_dano")
            
            st.markdown("**Mostrar solo:**")
            c_cubierta = st.checkbox("Afectación en Cubierta", key="chk_cub")
            c_muros = st.checkbox("Afectación en Muros/Fachada", key="chk_mur")
            c_estructural = st.checkbox("Riesgo Estructural", key="chk_est")
            c_colapso = st.checkbox("Vivienda con Colapso", key="chk_col")

            df_mapa_danos = df.copy()

            # Filtrado por Barrio y Sector
            if b_dano: df_mapa_danos = df_mapa_danos[df_mapa_danos["barrio_estandar"].isin(b_dano)]
            if s_dano: df_mapa_danos = df_mapa_danos[df_mapa_danos["sector_especifico"].isin(s_dano)]

            # Filtrado interactivo por casillas de verificación
            if c_cubierta or c_muros or c_estructural or c_colapso:
                cond_afect = pd.Series(False, index=df_mapa_danos.index)
                if c_cubierta: cond_afect |= df_mapa_danos["es_afectacion_cubierta"]
                if c_muros: cond_afect |= df_mapa_danos["es_afectacion_muros"]
                if c_estructural: cond_afect |= df_mapa_danos["es_riesgo_estructural"]
                if c_colapso: cond_afect |= df_mapa_danos["es_colapso"]
                df_mapa_danos = df_mapa_danos[cond_afect]
            else:
                # Si no hay ninguna casilla marcada, se muestran todas las viviendas con algún daño
                df_mapa_danos = df_mapa_danos[df_mapa_danos["es_riesgo_estructural"] | df_mapa_danos["es_afectacion_cubierta"] | df_mapa_danos["es_afectacion_muros"] | df_mapa_danos["es_colapso"]]

        with col_dmapa:
            m_dano = folium.Map(location=[5.161, -76.681], zoom_start=14, tiles="CartoDB positron")
            for _, r in df_mapa_danos.iterrows():
                color_point = "#8e44ad" if r["es_colapso"] else ("#e74c3c" if r["es_riesgo_estructural"] else "#f39c12")
                doc_str = f"({r['documento']})" if r['documento'] != "No registrado" else ""
                
                html_p = f"""
                <div style='min-width:200px; font-family:sans-serif;'>
                <h4 style='margin:0 0 5px 0; color:#2c3e50;'>{r['nombre_propietario']} {doc_str}</h4>
                <b>Teléfono:</b> {r['telefono']}<br>
                <b>Barrio:</b> {r['barrio_estandar']} ({r['sector_especifico']})<br>
                <b>Estado:</b> <span style='color:{r['color_riesgo']}; font-weight:bold;'>{r['clasificacion_habitabilidad']}</span><br>
                <hr style='margin:5px 0;'>
                <b>Daños Registrados:</b><br>
                <span style='color:#e74c3c; font-size:12px;'>{r['resumen_danos_criticos']}</span><br><br>
                <div style='text-align:center;'>{r['btn_foto']}</div>
                </div>
                """
                folium.CircleMarker(
                    location=[r["lat"], r["lon"]],
                    radius=8, color=color_point, fill=True, fill_color=color_point, fill_opacity=0.85,
                    popup=folium.Popup(html_p, max_width=280)
                ).add_to(m_dano)
            st_folium(m_dano, width="100%", height=400, key="mapa_danos")

# -------------------------------------------------------------------
# TAB 4: VULNERABILIDAD
# -------------------------------------------------------------------
with tabs[3]:
    v1, v2, v3, v4 = st.columns(4)
    with v1: render_value_box(int(df["ninos"].sum()), "Total Niños y Niñas", "#16a085", "fa-child")
    with v2: render_value_box(int(df["adultos_mayores"].sum()), "Adultos Mayores", "#2980b9", "fa-user")
    with v3: render_value_box(int(df["n_personas_discapacidad"].sum()), "Personas con Discapacidad", "#8e44ad", "fa-wheelchair")
    with v4: render_value_box(int(df["n_mujeres_embarazadas"].sum()), "Mujeres Embarazadas", "#c0392b", "fa-person-pregnant")

    col_v_izq, col_v_der = st.columns([4, 6])
    with col_v_izq:
        st.markdown('<span class="chart-title">📍 Mapa de Población Vulnerable</span>', unsafe_allow_html=True)
        f_ninos = st.checkbox("Niños y Niñas", value=True)
        f_mayores = st.checkbox("Adultos Mayores", value=True)
        f_discap = st.checkbox("Personas con Discapacidad", value=True)
        f_emb = st.checkbox("Mujeres Embarazadas", value=True)

        cond_v = pd.Series(False, index=df.index)
        if not df.empty:
            if f_ninos: cond_v |= (df["ninos"] > 0)
            if f_mayores: cond_v |= (df["adultos_mayores"] > 0)
            if f_discap: cond_v |= (df["n_personas_discapacidad"] > 0)
            if f_emb: cond_v |= (df["n_mujeres_embarazadas"] > 0)

        df_v_mapa = df[cond_v]
        m_v = folium.Map(location=[5.161, -76.681], zoom_start=14, tiles="CartoDB positron")
        for _, r in df_v_mapa.iterrows():
            total_vuln = int(r["ninos"] + r["adultos_mayores"] + r["n_personas_discapacidad"] + r["n_mujeres_embarazadas"])
            doc_str = f"({r['documento']})" if r['documento'] != "No registrado" else ""
            
            html_p = f"""
            <div style='min-width:200px; font-family:sans-serif;'>
            <h4 style='margin:0 0 5px 0; color:#2c3e50;'>{r['nombre_propietario']} {doc_str}</h4>
            <b>Teléfono:</b> {r['telefono']}<br>
            <b>Barrio:</b> {r['barrio_estandar']} ({r['sector_especifico']})<br>
            <hr style='margin:5px 0;'>
            <b>Total Personas Vulnerables:</b> <span style='color:#d35400; font-size:14px; font-weight:bold;'>{total_vuln}</span><br>
            <ul style='margin:5px 0 10px 15px; padding:0; font-size:12px;'>
                <li><b>Niños / Niñas:</b> {r['ninos']}</li>
                <li><b>Adultos Mayores:</b> {r['adultos_mayores']}</li>
                <li><b>Mujeres Embarazadas:</b> {r['n_mujeres_embarazadas']}</li>
                <li><b>Personas c/ Discapacidad:</b> {r['n_personas_discapacidad']}</li>
            </ul>
            <div style='text-align:center;'>{r['btn_foto']}</div>
            </div>
            """
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=8, color="#e67e22", fill=True, fill_color="#e67e22", fill_opacity=0.85,
                popup=folium.Popup(html_p, max_width=280)
            ).add_to(m_v)
        st_folium(m_v, width="100%", height=400, key="mapa_vuln")

    with col_v_der:
        st.markdown('<span class="chart-title">Concentración de Población Vulnerable por Barrio</span>', unsafe_allow_html=True)
        df_v = df.groupby("barrio_estandar")[["ninos", "adultos_mayores", "n_personas_discapacidad", "n_mujeres_embarazadas"]].sum().reset_index()
        df_v = df_v.rename(columns={"ninos": "Niños y Niñas", "adultos_mayores": "Adultos Mayores", "n_personas_discapacidad": "Personas con Discapacidad", "n_mujeres_embarazadas": "Mujeres Embarazadas"})
        df_v_melt = df_v.melt(id_vars=["barrio_estandar"], var_name="Grupo", value_name="Total")
        
        fig_v = px.bar(df_v_melt, x="Total", y="barrio_estandar", color="Grupo", barmode="group", orientation='h', color_discrete_sequence=px.colors.sequential.Viridis)
        fig_v = aplicar_estilo_plotly(fig_v, height=450)
        fig_v.update_layout(xaxis_title="Cantidad de Personas", yaxis_title="", legend_title_text="")
        st.plotly_chart(fig_v, use_container_width=True, theme=None)

# -------------------------------------------------------------------
# TAB 5: LOGÍSTICA Y RESCATE
# -------------------------------------------------------------------
with tabs[4]:
    st.markdown('<span class="chart-title">Matriz de Necesidades Inmediatas Solicitadas</span>', unsafe_allow_html=True)
    df_n = pd.DataFrame({
        "Necesidad": ["Cubiertas/Techos", "Materiales Const.", "Reparación Muros", "Estructurales", "Agua Potable", "Alojamiento", "Alimentación"],
        "Total": [df["nec_cubierta"].sum(), df["nec_materiales"].sum(), df["nec_muros"].sum(), df["nec_estructura"].sum(), df["nec_agua"].sum(), df["nec_alojamiento"].sum(), df["nec_alimento"].sum()]
    })
    fig_n = px.bar(df_n, x="Total", y="Necesidad", orientation='h', color_discrete_sequence=["#34495e"])
    fig_n = aplicar_estilo_plotly(fig_n, height=300)
    fig_n.update_layout(showlegend=False, xaxis_title="Viviendas que lo solicitan", yaxis_title="")
    st.plotly_chart(fig_n, use_container_width=True, theme=None)

    st.markdown('<span class="chart-title">🚨 Triage Urgente: Familias Inhabitables con Población Vulnerable</span>', unsafe_allow_html=True)
    df_t = df[(df["clasificacion_habitabilidad"].str.contains("colapso|no habitable", case=False, na=False)) & ((df["ninos"] > 0) | (df["adultos_mayores"] > 0) | (df["n_personas_discapacidad"] > 0) | (df["n_mujeres_embarazadas"] > 0))]
    
    df_t_show = df_t.rename(columns={
        "documento": "Documento",
        "barrio_estandar": "Barrio",
        "nombre_propietario": "Propietario",
        "telefono": "Teléfono",
        "clasificacion_habitabilidad": "Estado",
        "ninos": "Niños",
        "adultos_mayores": "Mayores",
        "n_personas_discapacidad": "Discap",
        "n_mujeres_embarazadas": "Embarazo",
        "necesidades_inmediatas": "Necesita"
    })
    cols_triage = ["Barrio", "Propietario", "Documento", "Teléfono", "Estado", "Niños", "Mayores", "Discap", "Embarazo", "Necesita"]
    st.dataframe(df_t_show[[c for c in cols_triage if c in df_t_show.columns]], use_container_width=True)

    if not df_t.empty:
        triage_sel = st.selectbox("Atender caso urgente de:", options=["-- Seleccionar --"] + sorted(df_t["nombre_propietario"].unique().tolist()))
        if triage_sel != "-- Seleccionar --":
            if st.button("📂 Abrir Expediente de Emergencia", key="btn_exp_triage"):
                st.session_state["expediente_buscado"] = triage_sel
                st.success("Caso seleccionado. Ve a la pestaña 'Expedientes'.")

# -------------------------------------------------------------------
# TAB 6: EXPEDIENTES
# -------------------------------------------------------------------
with tabs[5]:
    st.markdown('<span class="chart-title">📂 Base de Datos Completa de Evaluación</span>', unsafe_allow_html=True)
    col_search, col_clean = st.columns([4, 1])
    with col_search:
        busqueda = st.text_input("🔍 Buscar por Nombre de Propietario o Barrio:", value=st.session_state["expediente_buscado"])
    with col_clean:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Limpiar Filtro"):
            st.session_state["expediente_buscado"] = ""
            st.rerun()

    df_export = df.rename(columns={
        "fecha_corta": "Fecha",
        "barrio_estandar": "Barrio",
        "sector_especifico": "Sector",
        "nombre_propietario": "Propietario",
        "documento": "Documento",
        "telefono": "Teléfono",
        "clasificacion_habitabilidad": "Habitabilidad",
        "total_habitantes": "Pob_Total",
        "ninos": "Niños",
        "adultos_mayores": "Mayores",
        "n_personas_discapacidad": "Discapacitados",
        "n_mujeres_embarazadas": "Embarazadas",
        "resumen_danos_criticos": "Daños_Críticos",
        "necesidades_inmediatas": "Necesidades"
    })
    
    cols_exp = ["Fecha", "Barrio", "Sector", "Propietario", "Documento", "Teléfono", "Habitabilidad", "Pob_Total", "Niños", "Mayores", "Discapacitados", "Embarazadas", "Daños_Críticos", "Necesidades"]
    df_e = df_export[[c for c in cols_exp if c in df_export.columns]].copy()
    
    if busqueda:
        df_e = df_e[df_e["Propietario"].astype(str).str.contains(busqueda, case=False) | df_e["Barrio"].astype(str).str.contains(busqueda, case=False)]

    st.dataframe(df_e, use_container_width=True)
