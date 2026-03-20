import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re
import os

st.set_page_config(layout="wide", page_title="AIOS Planning Overzicht")

def get_sort_key(name):
    match = re.search(r'(\d+)', str(name))
    return int(match.group(1)) if match else 999

# --- DATA LADEN ---
# We zoeken naar de laatst geëxporteerde versie op je bureaublad of in de map
FILE_NAME = "planning_export.csv" 

if os.path.exists(FILE_NAME):
    df = pd.read_csv(FILE_NAME)
    df['Startdatum'] = pd.to_datetime(df['Startdatum'])
    df['Einddatum'] = pd.to_datetime(df['Einddatum'])
    
    # Sortering op startdatum
    order_df = df.groupby('Arts')['Startdatum'].min().sort_values().reset_index()
    sorted_aios = order_df['Arts'].tolist()

    st.title("🏥 Actueel Overzicht Opleidingsschema's")
    st.info("Dit is een alleen-lezen versie voor collega's.")

    # --- FILTERS ---
    st.sidebar.header("🔍 Filters")
    sel_aios = st.sidebar.selectbox("Selecteer AIOS", ["Alle AIOS"] + sorted_aios)
    
    all_locs = sorted(df['Locatie'].unique(), key=get_sort_key)
    sel_locs = st.sidebar.multiselect("Filter op Afdeling", options=all_locs)
    
    view_filter = st.sidebar.radio("Tijdlijn", ["Vanaf vandaag", "Volledige historie"])

    # Filter logica
    plot_df = df.copy()
    if sel_aios != "Alle AIOS":
        plot_df = plot_df[plot_df['Arts'] == sel_aios]
    if sel_locs:
        plot_df = plot_df[plot_df['Locatie'].isin(sel_locs)]
    if view_filter == "Vanaf vandaag":
        plot_df = plot_df[plot_df['Einddatum'] >= datetime.now()]

    # --- GANTT ---
    if not plot_df.empty:
        sorted_legend = sorted(plot_df['Locatie'].unique(), key=get_sort_key)
        fig = px.timeline(
            plot_df, x_start="Startdatum", x_end="Einddatum", y="Arts", color="Locatie",
            text="Stage", category_orders={"Arts": sorted_aios, "Locatie": sorted_legend},
            height=max(500, len(plot_df['Arts'].unique()) * 50)
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(xaxis_title="Datum", yaxis_title="AIOS (Chronologisch)")
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Bekijk volledige lijst"):
            st.dataframe(plot_df.sort_values(['Arts', 'Startdatum']), use_container_width=True)
    else:
        st.warning("Geen planning gevonden voor deze selectie.")
else:
    st.error(f"Bestand '{FILE_NAME}' niet gevonden. Zorg dat je een export maakt vanuit de hoofd-app.")
