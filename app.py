import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import dateutil.relativedelta as rd
import re

st.set_page_config(layout="wide", page_title="AIOS Planner Pro")

# --- HULPFUNCTIES ---
def add_months(start_date, months):
    return pd.to_datetime(start_date) + rd.relativedelta(months=int(months))

def get_sort_key(name):
    """Haalt het nummer uit de locatienaam voor sortering (bijv. '04' uit '04. Dwarslaesie')"""
    match = re.search(r'(\d+)', str(name))
    return int(match.group(1)) if match else 999

# --- DATA VERWERKING ---
def process_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        processed_data = []
        current_arts = "Onbekend"
        for _, row in df.iterrows():
            if row['Type'] == 'group':
                current_arts = str(row['Name / Title']).strip()
            elif row['Type'] == 'task' and pd.notna(row['Start Date']):
                processed_data.append({
                    'Arts': current_arts,
                    'Stage': str(row['Name / Title']),
                    'Locatie': str(row['Resources']) if pd.notna(row['Resources']) else "99. Onbekend",
                    'Startdatum': pd.to_datetime(row['Start Date']),
                    'Einddatum': pd.to_datetime(row['End Date'])
                })
        return pd.DataFrame(processed_data)
    except Exception as e:
        st.error(f"Fout bij inladen: {e}")
        return None

# --- CAPACITEITSCHECK ---
def check_conflicts(new_df, full_df):
    conflicts = []
    combined = pd.concat([full_df, new_df], ignore_index=True)
    for _, row in new_df.iterrows():
        if any(x in row['Locatie'] for x in ["Dwarslaesie", "Neurologie", "Kinderen"]):
            mask = (combined['Locatie'] == row['Locatie']) & \
                   (combined['Startdatum'] < row['Einddatum']) & \
                   (combined['Einddatum'] > row['Startdatum'])
            aantal = len(combined[mask])
            if "Dwarslaesie" in row['Locatie'] and aantal > 2:
                conflicts.append(f"Capaciteit overschreden op Dwarslaesie ({aantal} AIOS) rond {row['Startdatum'].date()}")
            if "Neurologie" in row['Locatie'] and aantal > 2:
                conflicts.append(f"Capaciteit overschreden op Neurologie ({aantal} AIOS) rond {row['Startdatum'].date()}")
            if "Kinderen" in row['Locatie'] and aantal > 1:
                conflicts.append(f"Capaciteit overschreden op {row['Locatie']} (max 1) rond {row['Startdatum'].date()}")
    return conflicts

# --- UI START ---
st.title("🏥 AIOS Revalidatie Planner & Generator")

uploaded_file = st.file_uploader("Stap 1: Upload je huidige .csv planning", type="csv")

if uploaded_file:
    if 'df' not in st.session_state:
        st.session_state.df = process_csv(uploaded_file)

    # --- SIDEBAR: GENERATOR ---
    with st.sidebar:
        st.header("📅 Nieuw Schema Plannen")
        with st.form("generator_form"):
            n_naam = st.text_input("Naam nieuwe AIOS")
            n_start = st.date_input("Startdatum opleiding", value=date.today())
            
            st.divider()
            n_totale_duur = st.slider("Totale duur opleiding (maanden)", 41, 48, 45)
            n_volgorde = st.radio("Volgorde kliniek", ["Neurologie -> Dwarslaesie", "Dwarslaesie -> Neurologie"])
            n_zh_duur = st.slider("Duur ziekenhuisstage (maanden)", 6, 12, 12)
            n_acad_duur = st.slider("Duur academische stage (maanden)", 3, 6, 3)
            n_keuze_duur = st.slider("Duur keuze onderwijs (maanden)", 3, 9, 6)
            n_lus = st.selectbox("Welke Lus?", ["Zuid-Limburg", "Venlo", "Breda"])
            
            submit_gen = st.form_submit_button("Genereer en check")

    if submit_gen and n_naam:
        new_rows = []
        curr = pd.to_datetime(n_start)

        # 1. Kliniek (12 maanden totaal)
        afd1 = "05. Neurologie" if "Neurologie" in n_volgorde else "04. Dwarslaesie"
        afd2 = "04. Dwarslaesie" if "Neurologie" in n_volgorde else "05. Neurologie"
        for afd in [afd1, afd2]:
            nxt = add_months(curr, 6)
            new_rows.append({'Arts': n_naam, 'Stage': afd, 'Locatie': afd, 'Startdatum': curr, 'Einddatum': nxt})
            curr = nxt

        # 2. Polikliniek (Vast 6 maanden)
        nxt = add_months(curr, 6)
        new_rows.append({'Arts': n_naam, 'Stage': 'Polikliniek', 'Locatie': '17. Polikliniek Hoensbroek', 'Startdatum': curr, 'Einddatum': nxt})
        curr = nxt

        # 3. De Lus (Ziekenhuis + Kind)
        zh_loc = "08. Ziekenhuis Heerlen" if "Zuid" in n_lus else "09. Ziekenhuis Venlo" if "Venlo" in n_lus else "10. Ziekenhuis Breda"
        kind_loc = "12. Kinderen Houthem" if "Zuid" in n_lus else "13. Kinderen Venlo" if "Venlo" in n_lus else "14. Kinderen Breda"
        
        nxt = add_months(curr, n_zh_duur)
        new_rows.append({'Arts': n_naam, 'Stage': 'Ziekenhuisstage', 'Locatie': zh_loc, 'Startdatum': curr, 'Einddatum': nxt})
        curr = nxt
        
        nxt = add_months(curr, 6)
        new_rows.append({'Arts': n_naam, 'Stage': 'Kinderrevalidatie', 'Locatie': kind_loc, 'Startdatum': curr, 'Einddatum': nxt})
        curr = nxt

        # 4. Academisch
        nxt = add_months(curr, n_acad_duur)
        new_rows.append({'Arts': n_naam, 'Stage': 'Academisch', 'Locatie': '16. Academische stage Maastricht', 'Startdatum': curr, 'Einddatum': nxt})
        curr = nxt

        # 5. Keuzestage
        nxt = add_months(curr, n_keuze_duur)
        new_rows.append({'Arts': n_naam, 'Stage': 'Keuzestage', 'Locatie': '18. Keuzestage', 'Startdatum': curr, 'Einddatum': nxt})

        proposed_df = pd.DataFrame(new_rows)
        
        fouten = check_conflicts(proposed_df, st.session_state.df)
        if fouten:
            for f in fouten: st.sidebar.error(f)
        else:
            st.sidebar.success(f"✅ Schema voor {n_naam} toegevoegd!")
        
        # Voeg direct toe aan de sessie
        st.session_state.df = pd.concat([st.session_state.df, proposed_df], ignore_index=True)

    # --- SORTERING & FILTERS ---
    # Sorteer AIOS op hun allereerste startdatum in de dataset
    order_df = st.session_state.df.groupby('Arts')['Startdatum'].min().sort_values().reset_index()
    sorted_aios = order_df['Arts'].tolist()

    st.subheader("🔍 Filters & Overzicht")
    f1, f2, f3 = st.columns(3)
    with f1:
        sel_aios = st.selectbox("Selecteer één AIOS", ["Alle AIOS"] + sorted_aios)
    with f2:
        locs = sorted(st.session_state.df['Locatie'].unique(), key=get_sort_key)
        sel_locs = st.multiselect("Selecteer Afdeling(en)", options=locs)
    with f3:
        view_filter = st.radio("Tijdlijn", ["Vanaf vandaag", "Volledige historie"], horizontal=True)

    # Filteren van de data voor de grafiek
    plot_df = st.session_state.df.copy()
    if sel_aios != "Alle AIOS":
        plot_df = plot_df[plot_df['Arts'] == sel_aios]
    if sel_locs:
        plot_df = plot_df[plot_df['Locatie'].isin(sel_locs)]
    if view_filter == "Vanaf vandaag":
        plot_df = plot_df[plot_df['Einddatum'] >= datetime.now()]

    # --- GANTT CHART ---
    if not plot_df.empty:
        # Legenda sorteren op locatienummer
        sorted_legend = sorted(plot_df['Locatie'].unique(), key=get_sort_key)
        
        fig = px.timeline(
            plot_df, 
            x_start="Startdatum", 
            x_end="Einddatum", 
            y="Arts", 
            color="Locatie",
            text="Stage", 
            category_orders={"Arts": sorted_aios, "Locatie": sorted_legend},
            height=max(400, len(plot_df['Arts'].unique()) * 55)
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

    # --- EXPORT ---
    st.divider()
    csv_data = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Genereer .csv (Download bijgewerkte planning)",
        data=csv_data,
        file_name=f"Bijgewerkte_Planning_{date.today()}.csv",
        mime="text/csv"
    )
else:
    st.info("👋 Upload een CSV bestand om de planner te starten.")