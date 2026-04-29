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
# HEADER (LAYOUT LADO A LADO)
# -------------------------------
col1, col2 = st.columns([1, 4])

with col1:
    st.image("FUNASA_LOGO.jpeg", width=120)

with col2:
    st.title("Mapa de Unidades SALTA")

# -------------------------------
# FUNÇÃO PARA CARREGAR DADOS DO S3 (EXCEL)
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

    # 🔥 LENDO EXCEL
    df = pd.read_excel(io.BytesIO(obj["Body"].read()))
    return df

# -------------------------------
# LOAD DATA
# -------------------------------
df = carregar_dados()

# -------------------------------
# PADRONIZAÇÃO
# -------------------------------
df.columns = df.columns.str.upper()

df['FUNCIONANDO'] = df['FUNCIONANDO'].astype(str).str.lower()
df['SITUAÇÃO'] = df['SITUAÇÃO'].astype(str).str.upper()
df = df.rename(columns={
    "ESTADO_x": "ESTADO",
    "MUNICIPIO_x": "MUNICIPIO"
})
# -------------------------------
# FILTRO ESTADOS
# -------------------------------
df = df[~df['ESTADO'].isin(['AP', 'PA', 'AC'])]

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.header("Filtros")

filtro_funcionando = st.sidebar.selectbox(
    "Funcionando?",
    options=["todos", "sim", "nao"]
)

if filtro_funcionando != "todos":
    df = df[df['FUNCIONANDO'] == filtro_funcionando]

# -------------------------------
# CORES
# -------------------------------
cores = {
    "ATIVO": "green",
    "INATIVO": "red",
    "MANUTENCAO": "orange"
}

def get_color(situacao):
    if pd.isna(situacao):
        return "gray"
    return cores.get(situacao, "blue")

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
            color=get_color(row["SITUAÇÃO"]),
            fill=True,
            fill_opacity=0.7,
            popup=f"""
            <b>Estado:</b> {row['ESTADO']}<br>
            <b>Situação:</b> {row['SITUAÇÃO']}<br>
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
