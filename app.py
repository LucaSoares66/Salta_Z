import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# =========================
# 🔹 CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("📍 Mapa de Comunidades - SALTA")

# =========================
# 🔹 LOAD
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("PLANILHA_SALTAZ_GEODCODIFICADA.xlsx")
    return df

df = load_data()

# =========================
# 🔹 LIMPEZA
# =========================
df = df.dropna(subset=["lat", "lon"])

df["FUNCIONANDO"] = (
    df["FUNCIONANDO"]
    .fillna("SEM INFORMAÇÃO")
    .astype(str)
    .str.upper()
    .str.strip()
)

df["SITUAÇÃO"] = (
    df["SITUAÇÃO"]
    .fillna("SEM INFORMAÇÃO")
    .astype(str)
    .str.upper()
    .str.strip()
)

df["ESTADO"] = df["ESTADO"].astype(str).str.upper()
df["COMUNIDADE"] = df["COMUNIDADE"].astype(str).str.upper()

# =========================
# 🔹 DASHBOARD (AGORA FUNCIONANDO)
# =========================
st.subheader("Quantidade por Funcionamento")

contagem_func = df["FUNCIONANDO"].value_counts()
cols = st.columns(len(contagem_func))

def cor_funcionando(func):
    if func == "SIM":
        return "blue"
    elif func == "NÃO":
        return "red"
    else:
        return "gray"

for i, (func, val) in enumerate(contagem_func.items()):
    cols[i].markdown(
        f"<h3 style='color:{cor_funcionando(func)}'>{val}</h3><p>{func}</p>",
        unsafe_allow_html=True
    )

# =========================
# 🔹 FILTROS
# =========================
col1, col2, col3 = st.columns(3)

# SITUAÇÃO (mantido como filtro, mas sem dashboard)
situacoes = ["TODOS"] + sorted(df["SITUAÇÃO"].unique())
filtro_situacao = col1.selectbox("Situação:", situacoes)

# ESTADO
estados = ["TODOS"] + sorted(df["ESTADO"].unique())
filtro_estado = col2.selectbox("Estado:", estados)

# COMUNIDADE
df_temp = df.copy()

if filtro_estado != "TODOS":
    df_temp = df_temp[df_temp["ESTADO"] == filtro_estado]

comunidades = ["TODOS"] + sorted(df_temp["COMUNIDADE"].unique())
filtro_comunidade = col3.selectbox("Comunidade:", comunidades)

# =========================
# 🔹 APLICAR FILTROS
# =========================
df_filtrado = df.copy()

if filtro_situacao != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["SITUAÇÃO"] == filtro_situacao]

if filtro_estado != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["ESTADO"] == filtro_estado]

if filtro_comunidade != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["COMUNIDADE"] == filtro_comunidade]

# =========================
# 🔹 MAPA
# =========================
mapa = folium.Map(
    location=[-14, -52],
    zoom_start=4,
    prefer_canvas=True
)

def get_color(func, situacao):
    if situacao == "SEM INFORMAÇÃO":
        return "gray"
    elif func == "SIM":
        return "blue"
    elif func == "NÃO":
        return "red"
    return "gray"

# =========================
# 🔹 PLOTAR PONTOS
# =========================
for _, row in df_filtrado.iterrows():

    tooltip = f"{row['ESTADO']} - {row['COMUNIDADE']}"

    popup = f"""
    <b>Comunidade:</b> {row['COMUNIDADE']}<br>
    <b>Município:</b> {row['MUNICIPIO']}<br>
    <b>Estado:</b> {row['ESTADO']}<br>
    <b>Situação:</b> {row['SITUAÇÃO']}<br>
    <b>Funcionando:</b> {row['FUNCIONANDO']}
    """

    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=5,
        color=get_color(row["FUNCIONANDO"], row["SITUAÇÃO"]),
        fill=True,
        fill_color=get_color(row["FUNCIONANDO"], row["SITUAÇÃO"]),
        fill_opacity=0.7,
        tooltip=tooltip,
        popup=popup
    ).add_to(mapa)

# =========================
# 🔹 AUTO ZOOM
# =========================
coords = df_filtrado[["lat", "lon"]].values.tolist()
if coords:
    mapa.fit_bounds(coords)

# =========================
# 🔹 LEGENDA (FUNCIONANDO)
# =========================
contagem_legenda = df_filtrado["FUNCIONANDO"].value_counts()

html_legenda = """
<div style="
position: fixed; 
bottom: 50px; left: 50px; width: 220px; 
background-color: white; 
border:2px solid grey; 
z-index:9999; 
font-size:14px;
padding: 10px;
">
<b>Funcionamento</b><br>
"""

for func, val in contagem_legenda.items():
    cor = cor_funcionando(func)
    html_legenda += f"""
    <i style="background:{cor};width:10px;height:10px;display:inline-block;margin-right:5px;"></i>
    {func}: {val}<br>
    """

html_legenda += "</div>"

mapa.get_root().html.add_child(folium.Element(html_legenda))

# =========================
# 🔹 RENDER
# =========================
st_folium(mapa, width=1200, height=600)