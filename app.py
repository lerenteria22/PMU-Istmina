import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import re
from datetime import datetime

# ===================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ===================================================================
st.set_page_config(
    page_title="PMU - Sala de Crisis Istmina",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Control de acceso con Contraseña
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🚨 PMU - Sala de Crisis Istmina")
    clave = st.text_input("Ingrese la clave de acceso para continuar:", type="password")
    if st.button("Ingresar"):
        if clave == "Istmina2026":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    st.stop()

# ===================================================================
# CARGA Y TRATAMIENTO DE DATOS (CON CACHÉ DE 30 SEGUNDOS)
# ===================================================================
@st.cache_data(ttl=30)
def cargar_datos():
    url_csv = "https://docs.google.com/spreadsheets/d/1UyHaV3J-MJ3lMnQs5lnPGIdGMTn591Tsz1aZ9_E1Z8g/gviz/tq?tqx=out:csv&sheet=Hoja%201"
    try:
        df = pd.read_csv(url_csv)
        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('[^a-zA-Z0-9_]', '', regex=True)
    except Exception:
        df = pd.DataFrame()

    if df.empty or len(df) == 0:
        df = pd.DataFrame({
            "marca_temporal": ["2026-08-14 08:30:00", "2026-08-14 10:15:00", "2026-08-14 14:20:00"],
            "barrio_vereda": ["Cubis", "Comercio", "Independencia"],
            "clasificacion_habitabilidad": ["Riesgo de colapso", "Habitable", "No habitable"],
            "total_habitantes": [5, 3, 4], "ninos": [2, 0, 1], "adultos_mayores": [1, 0, 1],
            "n_personas_discapacidad": [0, 1, 0], "n_mujeres_embarazadas": [1, 0, 0],
            "coordenadas_gps": ["5.161,-76.681", "5.165,-76.675", "5.158,-76.685"],
            "nombre_propietario": ["Carlos Pérez", "María López", "Juan Gómez"],
            "telefono": ["3101234567", "3119876543", "3125554433"],
            "necesidades_inmediatas": ["Cubierta, Agua", "Materiales", "Reparación de muros"],
            "fotos": ["https://google.com", "", ""]
        })

    # Eliminar duplicados
    cols_comp = [c for c in df.columns if c not in ["marca_temporal", "timestamp"]]
    df = df.drop_duplicates(subset=cols_comp)

    # Fechas
    if "marca_temporal" in df.columns:
        df["fecha_corta"] = pd.to_datetime(df["marca_temporal"], errors='coerce').dt.date
    elif "timestamp" in df.columns:
        df["fecha_corta"] = pd.to_datetime(df["timestamp"], errors='coerce').dt.date
    else:
        df["fecha_corta"] = datetime.now().date()
    df["fecha_corta"] = df["fecha_corta"].fillna(datetime.now().date())

    # Columnas numéricas
    cols_num = ["total_habitantes", "ninos", "adultos_mayores", "n_personas_discapacidad", "n_mujeres_embarazadas"]
    for c in cols_num:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

    # Columnas de texto
    cols_txt = ["barrio_vereda", "clasificacion_habitabilidad", "nombre_propietario", "telefono", "necesidades_inmediatas", "fotos"]
    for c in cols_txt:
        if c not in df.columns:
            df[c] = "No registrado"
        df[c] = df[c].fillna("No registrado").astype(str)

    # Coordenadas GPS
    if "coordenadas_gps" in df.columns:
        coords = df["coordenadas_gps"].str.split(",", expand=True)
        df["lat"] = pd.to_numeric(coords[0], errors='coerce').fillna(5.161)
        df["lon"] = pd.to_numeric(coords[1], errors='coerce').fillna(-76.681)
    else:
        df["lat"] = 5.161
        df["lon"] = -76.681

    # Normalización de Barrios y Sectores
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
        return txt.title()

    def estandarizar_sector(txt):
        txt = str(txt).lower().strip()
        if "genoveva" in txt: return "Santa Genoveva"
        elif "meseta" in txt: return "La Meseta"
        elif re.search(r"lavanderia|lavandería|lavander", txt): return "Lavandería"
        elif re.search(r"\b70\b|la 70|setenta", txt): return "La 70"
        elif re.search(r"antuco|chorro", txt): return "Chorro de Antuco"
        elif re.search(r"chamblun|chamblún|chambl", txt): return "Chamblún"
        return "Sin Sector Específico"

    colores_hab = {
        "Habitable": "#27ae60",
        "Habitable con restricciones": "#f1c40f",
        "No habitable": "#e74c3c",
        "Riesgo de colapso": "#8e44ad",
        "No evaluado": "#3498db",
        "Sin Clasificar": "#95a5a6"
    }

    df["barrio_estandar"] = df["barrio_vereda"].apply(estandarizar_barrio)
    df["sector_especifico"] = df["barrio_vereda"].apply(estandarizar_sector)
    df["color_riesgo"] = df["clasificacion_habitabilidad"].map(colores_hab).fillna("#95a5a6")

    # Banderas de Necesidades
    nec_str = df["necesidades_inmediatas"].str.lower()
    df["nec_cubierta"] = nec_str.str.contains("cubierta").astype(int)
    df["nec_materiales"] = nec_str.str.contains("materiales").astype(int)
    df["nec_muros"] = nec_str.str.contains("reparación de muros|reparacion de muros", regex=True).astype(int)
    df["nec_estructura"] = nec_str.str.contains("reparaciones estructurales|estructural", regex=True).astype(int)
    df["nec_agua"] = nec_str.str.contains("agua").astype(int)
    df["nec_alojamiento"] = nec_str.str.contains("alojamiento").astype(int)
    df["nec_alimento"] = nec_str.str.contains("alimentación|alimentacion", regex=True).astype(int)

    # Evaluación de Daños
    cols_severidad = ["dano_cimentacion", "dano_columnas", "dano_vigas", "dano_muros", 
                      "dano_placas_pisos", "dano_cubierta", "dano_fachada", 
                      "dano_inst_electrica", "dano_inst_hidraulica", "dano_inst_gas"]
    cols_sino = ["grietas_muros", "grietas_estructurales", "desprendimiento_material", 
                 "inclinacion_muros", "danos_columnas_vigas", "danos_cubierta", 
                 "danos_instalaciones", "parte_colapsada"]

    for col in cols_severidad:
        if col not in df.columns: df[col] = "Sin daño"
        df[col] = df[col].fillna("Sin daño")

    for col in cols_sino:
        if col not in df.columns: df[col] = "No"
        df[col] = df[col].fillna("No")

    df["es_riesgo_estructural"] = (
        df["dano_cimentacion"].isin(["Severo", "Colapso"]) |
        df["dano_columnas"].isin(["Severo", "Colapso"]) |
        df["dano_vigas"].isin(["Severo", "Colapso"]) |
        df["grietas_estructurales"].str.lower().str.contains("sí|si", regex=True) |
        df["danos_columnas_vigas"].str.lower().str.contains("sí|si", regex=True)
    )

    df["es_afectacion_cubierta"] = (
        df["dano_cubierta"].isin(["Moderado", "Severo", "Colapso"]) |
        df["danos_cubierta"].str.lower().str.contains("sí|si", regex=True)
    )

    df["es_afectacion_muros"] = (
        df["dano_muros"].isin(["Moderado", "Severo", "Colapso"]) |
        df["dano_fachada"].isin(["Moderado", "Severo", "Colapso"]) |
        df["grietas_muros"].str.lower().str.contains("sí|si", regex=True) |
        df["inclinacion_muros"].str.lower().str.contains("sí|si", regex=True)
    )

    df["es_colapso"] = (
        df["dano_cimentacion"].eq("Colapso") | df["dano_columnas"].eq("Colapso") |
        df["dano_vigas"].eq("Colapso") | df["dano_muros"].eq("Colapso") |
        df["dano_placas_pisos"].eq("Colapso") | df["dano_cubierta"].eq("Colapso") |
        df["parte_colapsada"].str.lower().str.contains("sí|si", regex=True)
    )

    def calcular_resumen(row):
        criticos = []
        if row["dano_cimentacion"] in ["Severo", "Colapso"]: criticos.append(f"Cimentación ({row['dano_cimentacion']})")
        if row["dano_columnas"] in ["Severo", "Colapso"]: criticos.append(f"Columnas ({row['dano_columnas']})")
        if row["dano_vigas"] in ["Severo", "Colapso"]: criticos.append(f"Vigas ({row['dano_vigas']})")
        if row["dano_muros"] in ["Severo", "Colapso"]: criticos.append(f"Muros ({row['dano_muros']})")
        if row["dano_placas_pisos"] in ["Severo", "Colapso"]: criticos.append(f"Placas/Pisos ({row['dano_placas_pisos']})")
        if row["dano_cubierta"] in ["Severo", "Colapso"]: criticos.append(f"Cubierta ({row['dano_cubierta']})")
        if "sí" in str(row["grietas_estructurales"]).lower() or "si" in str(row["grietas_estructurales"]).lower(): criticos.append("Grietas Estructurales")
        if "sí" in str(row["parte_colapsada"]).lower() or "si" in str(row["parte_colapsada"]).lower(): criticos.append("Parte Colapsada")
        return " | ".join(criticos) if criticos else "Sin daños estructurales críticos"

    df["resumen_danos_criticos"] = df.apply(calcular_resumen, axis=1)
    df["id_casa"] = range(1, len(df) + 1)
    return df, colores_hab

df, colores_habitabilidad = cargar_datos()

# ===================================================================
# INTERFAZ Y NAVEGACIÓN
# ===================================================================
st.title("🚨 PMU - Sala de Crisis Istmina")
st.caption("Sincronización en vivo con Google Sheets cada 30 segundos")

tabs = st.tabs(["📊 Mando Unificado", "🗺️ Visor Geoespacial", "🏗️ Análisis de Daños", "👶 Vulnerabilidad", "📦 Logística y Rescate", "📂 Expedientes"])

# -------------------------------------------------------------------
# TAB 1: MANDO UNIFICADO
# -------------------------------------------------------------------
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Viviendas Evaluadas", len(df))
    colapso_count = int(df["clasificacion_habitabilidad"].eq("Riesgo de colapso").sum())
    c2.metric("Riesgo Inminente (Colapso)", colapso_count)
    c3.metric("Población Total Afectada", int(df["total_habitantes"].sum()))
    vuln_count = int(df["ninos"].sum() + df["adultos_mayores"].sum() + df["n_personas_discapacidad"].sum() + df["n_mujeres_embarazadas"].sum())
    c4.metric("Población Vulnerable", vuln_count)

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("Estado de Habitabilidad General")
        df_hab = df["clasificacion_habitabilidad"].value_counts().reset_index()
        df_hab.columns = ["Estado", "Cantidad"]
        fig_hab = px.bar(df_hab, x="Cantidad", y="Estado", orientation='h', color="Estado",
                         color_discrete_map=colores_habitabilidad)
        fig_hab.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_hab, use_container_width=True)

    with col_g2:
        st.subheader("Habitabilidad Consolidada por Barrio")
        df_barrio = df.groupby(["barrio_estandar", "clasificacion_habitabilidad"]).size().reset_index(name="n")
        fig_barrio = px.bar(df_barrio, x="n", y="barrio_estandar", color="clasificacion_habitabilidad",
                            orientation='h', color_discrete_map=colores_habitabilidad,
                            labels={"n": "Cantidad de Viviendas", "barrio_estandar": "", "clasificacion_habitabilidad": "Estado"})
        fig_barrio.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_barrio, use_container_width=True)

    st.subheader("Evolución Temporal de Reportes")
    df_tiempo = df.groupby("fecha_corta").size().reset_index(name="n")
    fig_tiempo = px.line(df_tiempo, x="fecha_corta", y="n", markers=True, labels={"fecha_corta": "Fecha", "n": "Evaluaciones"})
    fig_tiempo.update_traces(line_color="#e74c3c")
    st.plotly_chart(fig_tiempo, use_container_width=True)

# -------------------------------------------------------------------
# TAB 2: VISOR GEOESPACIAL
# -------------------------------------------------------------------
with tabs[1]:
    col_filtros, col_mapa = st.columns([1, 2])
    
    with col_filtros:
        st.subheader("📍 Filtros Interactivos")
        barrios_sel = st.multiselect("Seleccione Barrio / Vereda:", options=sorted(df["barrio_estandar"].unique()))
        estados_sel = st.multiselect("Filtrar por Estado:", options=sorted(df["clasificacion_habitabilidad"].unique()))

        df_mapa = df.copy()
        if barrios_sel: df_mapa = df_mapa[df_mapa["barrio_estandar"].isin(barrios_sel)]
        if estados_sel: df_mapa = df_mapa[df_mapa["clasificacion_habitabilidad"].isin(estados_sel)]

        st.subheader("📋 Padrón Filtrado")
        st.dataframe(df_mapa[["nombre_propietario", "barrio_estandar", "clasificacion_habitabilidad", "total_habitantes"]], height=250)

    with col_mapa:
        st.subheader("🗺️ Mapa Interactivo")
        m = folium.Map(location=[5.161, -76.681], zoom_start=14)
        for _, r in df_mapa.iterrows():
            html_popup = f"""
            <b>{r['nombre_propietario']}</b><br>
            <b>Barrio:</b> {r['barrio_estandar']} ({r['sector_especifico']})<br>
            <b>Estado:</b> <span style="color:{r['color_riesgo']}; font-weight:bold;">{r['clasificacion_habitabilidad']}</span><br>
            <b>Habitantes:</b> {r['total_habitantes']}<br>
            <b>Daños:</b> {r['resumen_danos_criticos']}<br>
            <b>Teléfono:</b> {r['telefono']}
            """
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=8,
                color=r["color_riesgo"],
                fill=True,
                fill_color=r["color_riesgo"],
                fill_opacity=0.85,
                popup=folium.Popup(html_popup, max_width=250)
            ).add_to(m)
        st_folium(m, width="100%", height=500)

# -------------------------------------------------------------------
# TAB 3: ANÁLISIS DE DAÑOS
# -------------------------------------------------------------------
with tabs[2]:
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Riesgo Estructural Crítico", int(df["es_riesgo_estructural"].sum()))
    d2.metric("Afectación en Cubiertas", int(df["es_afectacion_cubierta"].sum()))
    d3.metric("Afectación Muros / Fachada", int(df["es_afectacion_muros"].sum()))
    d4.metric("Viviendas con Colapso", int(df["es_colapso"].sum()))

    st.markdown("---")
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.subheader("Severidad por Elemento")
        cols_sev = ["dano_cimentacion", "dano_columnas", "dano_vigas", "dano_muros", 
                    "dano_placas_pisos", "dano_cubierta", "dano_fachada"]
        df_sev = df[cols_sev].melt(var_name="Elemento", value_name="Nivel")
        df_sev = df_sev[df_sev["Nivel"].isin(["Leve", "Moderado", "Severo", "Colapso"])]
        if not df_sev.empty:
            df_sev["Elemento"] = df_sev["Elemento"].str.replace("dano_", "").str.replace("_", " ").str.title()
            df_counts = df_sev.groupby(["Elemento", "Nivel"]).size().reset_index(name="n")
            colores_dano = {"Leve": "#f1c40f", "Moderado": "#e67e22", "Severo": "#e74c3c", "Colapso": "#8e44ad"}
            fig_sev = px.bar(df_counts, x="n", y="Elemento", color="Nivel", orientation='h', color_discrete_map=colores_dano)
            st.plotly_chart(fig_sev, use_container_width=True)
        else:
            st.info("Sin datos de daños reportados.")

    with col_d2:
        st.subheader("Señales Visibles Frecuentes")
        cols_sino = ["grietas_muros", "grietas_estructurales", "desprendimiento_material", 
                     "inclinacion_muros", "danos_columnas_vigas", "danos_cubierta"]
        df_alert = df[cols_sino].melt(var_name="Alerta", value_name="Resp")
        df_alert = df_alert[df_alert["Resp"].str.lower().str.contains("sí|si", regex=True)]
        if not df_alert.empty:
            df_alert["Alerta"] = df_alert["Alerta"].str.replace("_", " ").str.title()
            df_al_cnt = df_alert["Alerta"].value_counts().reset_index()
            df_al_cnt.columns = ["Alerta", "n"]
            fig_al = px.bar(df_al_cnt, x="n", y="Alerta", orientation='h', color_discrete_sequence=["#34495e"])
            st.plotly_chart(fig_al, use_container_width=True)
        else:
            st.info("Sin señales visibles reportadas.")

# -------------------------------------------------------------------
# TAB 4: VULNERABILIDAD
# -------------------------------------------------------------------
with tabs[3]:
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Total Niños y Niñas", int(df["ninos"].sum()))
    v2.metric("Adultos Mayores", int(df["adultos_mayores"].sum()))
    v3.metric("Personas con Discapacidad", int(df["n_personas_discapacidad"].sum()))
    v4.metric("Mujeres Embarazadas", int(df["n_mujeres_embarazadas"].sum()))

    st.markdown("---")
    st.subheader("Concentración de Población Vulnerable por Barrio")
    df_vuln = df.groupby("barrio_estandar")[["ninos", "adultos_mayores", "n_personas_discapacidad", "n_mujeres_embarazadas"]].sum().reset_index()
    df_vuln_melt = df_vuln.melt(id_vars=["barrio_estandar"], var_name="Grupo", value_name="Total")
    df_vuln_melt = df_vuln_melt[df_vuln_melt["Total"] > 0]
    
    fig_vuln = px.bar(df_vuln_melt, x="Total", y="barrio_estandar", color="Grupo", barmode="group", orientation='h',
                      labels={"barrio_estandar": "", "Total": "Cantidad de Personas"})
    st.plotly_chart(fig_vuln, use_container_width=True)

# -------------------------------------------------------------------
# TAB 5: LOGÍSTICA Y RESCATE
# -------------------------------------------------------------------
with tabs[4]:
    st.subheader("Matriz de Necesidades Inmediatas Solicitadas")
    df_nec = pd.DataFrame({
        "Necesidad": ["Cubiertas/Techos", "Materiales Const.", "Reparación de Muros", "Reparaciones Estructurales", "Agua Potable", "Alojamiento", "Alimentación"],
        "Total": [df["nec_cubierta"].sum(), df["nec_materiales"].sum(), df["nec_muros"].sum(), df["nec_estructura"].sum(), df["nec_agua"].sum(), df["nec_alojamiento"].sum(), df["nec_alimento"].sum()]
    })
    fig_nec = px.bar(df_nec, x="Total", y="Necesidad", orientation='h', color_discrete_sequence=["#34495e"])
    st.plotly_chart(fig_nec, use_container_width=True)

    st.subheader("🚨 Triage Urgente: Familias Inhabitables con Población Vulnerable")
    df_triage = df[(df["clasificacion_habitabilidad"].isin(["Riesgo de colapso", "No habitable"])) & 
                   ((df["ninos"] > 0) | (df["adultos_mayores"] > 0) | (df["n_personas_discapacidad"] > 0) | (df["n_mujeres_embarazadas"] > 0))]
    cols_triage = ["barrio_estandar", "nombre_propietario", "telefono", "clasificacion_habitabilidad", "ninos", "adultos_mayores", "n_personas_discapacidad", "necesidades_inmediatas"]
    st.dataframe(df_triage[cols_triage], use_container_width=True)

# -------------------------------------------------------------------
# TAB 6: EXPEDIENTES
# -------------------------------------------------------------------
with tabs[5]:
    st.subheader("📂 Base de Datos Completa de Evaluación")
    busqueda = st.text_input("🔍 Buscar por Nombre de Propietario o Barrio:")
    df_exp = df.copy()
    if busqueda:
        df_exp = df_exp[df_exp["nombre_propietario"].str.contains(busqueda, case=False) | df_exp["barrio_estandar"].str.contains(busqueda, case=False)]
    
    st.dataframe(df_exp, use_container_width=True)
