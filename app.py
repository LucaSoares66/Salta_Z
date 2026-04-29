import streamlit as st
import pandas as pd
import boto3
import io
import folium
from streamlit_folium import st_folium

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(layout="wide")

# -------------------------------
# HEADER
# -------------------------------
st.image("header.png", use_container_width=True)
st.title("📍 Mapa de Unidades SALTA")

# -------------------------------
# FUNÇÃO PARA CARREGAR DADOS DO S3
# -------------------------------
@st.cache_data
def carregar_dados():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_DEFAULT_REGION"]
    )

    obj = s3.get_object(
        Bucket=st.secrets["BUCKET_NAME"],
        Key=st.secrets["FILE_KEY"]
    )

    df = pd.read_csv(io.BytesIO(obj["Body"].read()))
    return df

# -------------------------------
# LOAD DATA
# -------------------------------
df = carregar_dados()

# -------------------------------
# LIMPEZA / PADRONIZAÇÃO
# -------------------------------
df.columns = df.columns.str.upper()

# Garantir consistência
df['FUNCIONANDO'] = df['FUNCIONANDO'].astype(str).str.lower()

# Remover estados
df = df[~df['ESTADO'].isin(['AP', 'PA', 'AC'])]

# -------------------------------
# SIDEBAR FILTROS
# -------------------------------
st.sidebar.header("Filtros")

filtro_funcionando = st.sidebar.selectbox(
    "Funcionando?",
    options=["todos", "sim", "nao"]
)

if filtro_funcionando != "todos":
    df = df[df['FUNCIONANDO'] == filtro_funcionando]

# -------------------------------
# CORES POR SITUAÇÃO
# -------------------------------
cores = {
    "ATIVO": "green",
    "INATIVO": "red",
    "MANUTENCAO": "orange"
}

def get_color(situacao):
    if pd.isna(situacao):
        return "gray"
    return cores.get(situacao.upper(), "blue")

# -------------------------------
# MAPA
# -------------------------------
mapa = folium.Map(
    location=[-14.2350, -51.9253],
    zoom_start=4
)

# -------------------------------
# MARCADORES
# -------------------------------
for _, row in df.iterrows():
    if pd.notna(row["LAT"]) and pd.notna(row["LON"]):
        folium.CircleMarker(
            location=[row["LAT"], row["LON"]],
            radius=5,
            color=get_color(row["SITUACAO"]),
            fill=True,
            fill_opacity=0.7,
            popup=f"""
            <b>Estado:</b> {row['ESTADO']}<br>
            <b>Situação:</b> {row['SITUACAO']}<br>
            <b>Funcionando:</b> {row['FUNCIONANDO']}
            """
        ).add_to(mapa)

# -------------------------------
# LEGENDA
# -------------------------------
legend_html = """
<div style="
position: fixed;
bottom: 50px;
left: 50px;
width: 200px;
height: 130px;
background-color: white;
border:2px solid grey;
z-index:9999;
font-size:14px;
padding: 10px;
">
<b>Legenda</b><br>
<i style="color:green;">●</i> Ativo<br>
<i style="color:red;">●</i> Inativo<br>
<i style="color:orange;">●</i> Manutenção<br>
<i style="color:blue;">●</i> Outros
</div>
"""

mapa.get_root().html.add_child(folium.Element(legend_html))

# -------------------------------
# MOSTRAR MAPA
# -------------------------------
st_folium(mapa, use_container_width=True)
