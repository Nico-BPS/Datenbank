import streamlit as st
import pandas as pd
import os
from datetime import datetime
from supabase import create_client, Client

# --- 1. SETUP SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HILFSFUNKTIONEN ---
def get_liste(spalte, tabelle="fahrzeuge"):
    try:
        response = supabase.table(tabelle).select(spalte).execute()
        werte = [row[spalte] for row in response.data if row.get(spalte)]
        return sorted(list(set(werte)))
    except:
        return []

def form_auswahl(label, spalte, tabelle="fahrzeuge", aktueller_wert="", key=None):
    optionen = ["➕ Neu eingeben..."] + get_liste(spalte, tabelle)
    idx = optionen.index(aktueller_wert) if aktueller_wert and aktueller_wert in optionen else 0
    sel_key = f"sel_{key}" if key else None
    txt_key = f"txt_{key}" if key else None
    
    auswahl = st.selectbox(label, optionen, index=idx, key=sel_key)
    if auswahl == "➕ Neu eingeben...":
        standard_text = aktueller_wert if (aktueller_wert and aktueller_wert not in optionen) else ""
        return st.text_input(f"Neuen Wert für '{label}' eintippen:", value=standard_text, key=txt_key)
    return auswahl

# --- 3. SESSION STATE NAVIGATION ---
if 'page' not in st.session_state:
    st.session_state.page = "liste"
if 'bus_id' not in st.session_state:
    st.session_state.bus_id = None

# --- KOPFZEILE ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown("<h1 style='font-size: 45px; margin-top: -20px;'>Bus Archiv</h1>", unsafe_allow_html=True)
with col_head2:
    if st.session_state.page != "liste":
        if st.button("🏠 Zur Startseite", use_container_width=True):
            st.session_state.page = "liste"
            st.session_state.bus_id = None
            st.rerun()

st.markdown("---")

# ==========================================
# STARTSEITE
# ==========================================
if st.session_state.page == "liste":
    col1, col2 = st.columns([3, 1])
    col1.title("Datenbank")
    if col2.button("✏️ Neues Fahrzeug", use_container_width=True):
        st.session_state.page = "neu"
        st.rerun()
    
    response = supabase.table("fahrzeuge").select("*").execute()
    fahrzeuge = pd.DataFrame(response.data)
    
    if not fahrzeuge.empty:
        fahrzeuge.fillna({'wagennummer': '', 'betreiber': '', 'baujahr': '', 'marke': '', 'modell': '', 'notizen': ''}, inplace=True)
        suchbegriff = st.text_input("🔍 Schnellsuchen (Kennzeichen, Modell, Betreiber, Notiz...):")
        
        gefiltert = fahrzeuge.copy()
        if suchbegriff:
            mask = gefiltert.astype(str).apply(lambda row: row.str.contains(suchbegriff, case=False).any(), axis=1)
            gefiltert = gefiltert[mask]
        
        st.write(f"**{len(gefiltert)} Datensätze**")
        st.markdown("---")
        
        for _, row in gefilzert.iterrows():
            wagen = f" [Wg: {row['wagennummer']}]" if row['wagennummer'] else ""
            betreiber = f" | {row['betreiber']}" if row['betreiber'] else ""
            baujahr = f" | Bj: {int(row['baujahr'])}" if row['baujahr'] != '' else ""
            
            button_text = f"🚍 {row['kennzeichen']}{wagen}  ➔  {row['marke']} {row['modell']}{baujahr}{betreiber}"
            if st.button(button_text, key=f"bus_{row['id']}", use_container_width=True):
                st.session_state.bus_id = row['id']
                st.session_state.page = "details"
                st.rerun()
    else:
        st.info("Die Datenbank ist aktuell leer.")

# ==========================================
# DETAILS
# ==========================================
elif st.session_state.page == "details" and st.session_state.bus_id is not None:
    auto_id = st.session_state.bus_id
    response = supabase.table("fahrzeuge").select("*").eq("id", auto_id).execute()
    auto = response.data[0]
    
    baujahr_val = str(int(auto.get('baujahr') or 0)) if auto.get('baujahr') else "-"
    wagen_val = auto.get('wagennummer') or "-"
    betreiber_val = auto.get('betreiber') or "-"
    notizen_val = auto.get('notizen') or ""
    
    st.title(auto['kennzeichen'])
    
    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("✏️ Bearbeiten"):
        st.session_state.page = "bearbeiten"
        st.rerun()
    if c2.button("🗑️ Löschen"):
        supabase.table("fahrzeuge").delete().eq("id", auto_id).execute()
        st.session_state.bus_id = None
        st.session_state.page = "liste"
        st.success("Fahrzeug gelöscht!")
        st.rerun()

    st.markdown("---")
    col_info1, col_info2 = st.columns(2)
    col_info1.write(f"**Marke / Modell:** {auto['marke']} {auto['modell']}")
    col_info1.write(f"**Baujahr:** {baujahr_val}")
    col_info2.write(f"**Wagennummer:** {wagen_val}")
    col_info2.write(f"**Betreiber:** {betreiber_val}")
    
    if notizen_val:
        st.write("---")
        st.write("### 📝 Notizen")
        st.write(notizen_val)
        
    st.markdown("---")
    
    # FOTOS
    st.write("### 📸 Fotos")
    fotos_resp = supabase.table("fotos").select("*").eq("fahrzeug_id", auto_id).order("id", desc=True).execute()
    fotos = pd.DataFrame(fotos_resp.data)
    
    if not fotos.empty:
        for _, foto in fotos.iterrows():
            foto_id = foto['id']
            caption_text = f"Aufnahme: {foto.get('datum', '??')}"
            if foto.get('aufnahme_standort'): caption_text += f" | Ort: {foto['aufnahme_standort']}"
                
            st.image(foto['pfad'], caption=caption_text)
            
            with st.expander("Foto bearbeiten / löschen"):
                neu_datum = st.text_input("Datum (z.B. 2024 oder 12.05.2024)", value=foto.get('datum', ''), key=f"date_{foto_id}")
                neu_foto_ort = form_auswahl("Aufnahme Standort", "aufnahme_standort", "fotos", foto.get('aufnahme_standort') or "", key=f"foto_ort_{foto_id}")
                
                bc1, bc2 = st.columns(2)
                if bc1.button("Speichern", key=f"save_{foto_id}"):
                    final_datum = neu_datum.strip() if neu_datum.strip() else "??"
                    supabase.table("fotos").update({"datum": final_datum, "aufnahme_standort": neu_foto_ort}).eq("id", foto_id).execute()
                    st.rerun()
                if bc2.button("Löschen", key=f"del_{foto_id}"):
                    supabase.table("fotos").delete().eq("id", foto_id).execute()
                    st.rerun()
    else:
        st.write("Keine Fotos vorhanden.")
        
    with st.expander("➕ Neues Foto hochladen"):
        upload_datum = st.text_input("Aufnahmedatum (z.B. 2024, 05.2024 oder 12.05.2024)", value="", key=f"upload_date_{auto_id}")
        neu_foto_ort = form_auswahl("Aufnahme Standort", "aufnahme_standort", "fotos", key=f"upload_ort_{auto_id}")
        neues_foto = st.file_uploader("Datei auswählen", type=['jpg', 'png', 'jpeg'], key=f"upload_{auto_id}")
        
        if neues_foto:
            file_name = f"{auto_id}_{datetime.now().timestamp()}.jpg"
            supabase.storage.from_("fotos").upload(file_name, neues_foto.getvalue())
            public_url = supabase.storage.from_("fotos").get_public_url(file_name)
            
            final_datum = upload_datum.strip() if upload_datum.strip() else "??"
            supabase.table("fotos").insert({"fahrzeug_id": auto_id, "pfad": public_url, "datum": final_datum, "aufnahme_standort": neu_foto_ort}).execute()
            st.rerun()

    st.markdown("---")
    
    # STANDORTE
    st.write("### 📍 Standort-Historie")
    standorte_resp = supabase.table("standorte").select("*").eq("fahrzeug_id", auto_id).execute()
    standorte = pd.DataFrame(standorte_resp.data)
    
    if not standorte.empty:
        for _, ort_row in standorte.iterrows():
            ort_id = ort_row['id']
            with st.expander(f"{ort_row['standort']} ({ort_row['datum_von']} bis {ort_row['datum_bis']})"):
                neu_ort = form_auswahl("Standort", "standort", "standorte", ort_row['standort'], key=f"edit_ort_{ort_id}")
                neu_von = st.text_input("Von (z.B. 2023 oder 01.2023)", value=ort_row.get('datum_von', ''), key=f"ort_von_{ort_id}")
                neu_bis = st.text_input("Bis (z.B. 2024 oder 12.2024)", value=ort_row.get('datum_bis', ''), key=f"ort_bis_{ort_id}")
                
                oc1, oc2 = st.columns(2)
                if oc1.button("Speichern", key=f"ort_save_{ort_id}"):
                    str_von = neu_von.strip() if neu_von.strip() else "??"
                    str_bis = neu_bis.strip() if neu_bis.strip() else "??"
                    supabase.table("standorte").update({"standort": neu_ort, "datum_von": str_von, "datum_bis": str_bis}).eq("id", ort_id).execute()
                    st.rerun()
                if oc2.button("Löschen", key=f"ort_del_{ort_id}"):
                    supabase.table("standorte").delete().eq("id", ort_id).execute()
                    st.rerun()
    else:
        st.write("Keine Historie hinterlegt.")
    
    with st.expander("➕ Neuen Standort eintragen"):
        ort_neu = form_auswahl("Ort / Betriebshof", "standort", "standorte", key="neu_ort_eingabe")
        von_neu = st.text_input("Von (optional, z.B. 2023)", value="", key="neu_ort_von")
        bis_neu = st.text_input("Bis (optional, z.B. 2024)", value="", key="neu_ort_bis")
        
        if st.button("Standort speichern"):
            if ort_neu: 
                str_von = von_neu.strip() if von_neu.strip() else "??"
                str_bis = bis_neu.strip() if bis_neu.strip() else "??"
                supabase.table("standorte").insert({"fahrzeug_id": auto_id, "standort": ort_neu, "datum_von": str_von, "datum_bis": str_bis}).execute()
                st.rerun()

# ==========================================
# NEUES FAHRZEUG
# ==========================================
elif st.session_state.page == "neu":
    st.title("Neues Fahrzeug anlegen")
    col1, col2 = st.columns(2)
    kennzeichen = col1.text_input("Kennzeichen (Pflichtfeld)")
    wagennummer = col2.text_input("Wagennummer (optional)")
    
    marke = form_auswahl("Marke", "marke", key="neu_marke")
    modell = form_auswahl("Modell", "modell", key="neu_modell")
    betreiber = form_auswahl("Betreiber / Firma", "betreiber", key="neu_betreiber")
    baujahr = st.number_input("Baujahr (optional)", min_value=1950, max_value=2030, value=None)
    notizen = st.text_area("Notizen (optional)")
    
    st.markdown("---")
    st.write("### Foto direkt hinzufügen")
    upload_datum = st.text_input("Aufnahmedatum (z.B. 2024)", value="", key="neu_auto_foto_datum")
    foto_ort = form_auswahl("Aufnahme Standort", "aufnahme_standort", "fotos", key="neu_auto_foto_ort")
    neues_foto = st.file_uploader("Bild auswählen", type=['jpg', 'png', 'jpeg'], key="neu_auto_foto_file")
    
    if st.button("Fahrzeug speichern", type="primary"):
        if kennzeichen:
            data = {"kennzeichen": kennzeichen, "wagennummer": wagennummer, "betreiber": betreiber, "marke": marke, "modell": modell, "baujahr": baujahr, "notizen": notizen}
            res = supabase.table("fahrzeuge").insert(data).execute()
            new_id = res.data[0]['id']
            
            if neues_foto:
                file_name = f"{new_id}_{datetime.now().timestamp()}.jpg"
                supabase.storage.from_("fotos").upload(file_name, neues_foto.getvalue())
                public_url = supabase.storage.from_("fotos").get_public_url(file_name)
                final_datum = upload_datum.strip() if upload_datum.strip() else "??"
                supabase.table("fotos").insert({"fahrzeug_id": new_id, "pfad": public_url, "datum": final_datum, "aufnahme_standort": foto_ort}).execute()
            
            st.session_state.bus_id = new_id
            st.session_state.page = "details"
            st.rerun()
        else:
            st.error("Kennzeichen ist erforderlich.")

# ==========================================
# BEARBEITEN
# ==========================================
elif st.session_state.page == "bearbeiten" and st.session_state.bus_id is not None:
    auto_id = st.session_state.bus_id
    auto = supabase.table("fahrzeuge").select("*").eq("id", auto_id).execute().data[0]
    
    st.title("Fahrzeug bearbeiten")
    neu_kz = st.text_input("Kennzeichen", auto['kennzeichen'])
    neu_wagen = st.text_input("Wagennummer", auto.get('wagennummer') or "")
    neu_marke = form_auswahl("Marke", "marke", "fahrzeuge", auto.get('marke'), key="edit_marke")
    neu_modell = form_auswahl("Modell", "modell", "fahrzeuge", auto.get('modell'), key="edit_modell")
    neu_betreiber = form_auswahl("Betreiber", "betreiber", "fahrzeuge", auto.get('betreiber'), key="edit_betreiber")
    
    bj_val = int(auto['baujahr']) if auto.get('baujahr') else None
    neu_baujahr = st.number_input("Baujahr", value=bj_val)
    neu_notizen = st.text_area("Notizen", auto.get('notizen') or "")
    
    col1, col2 = st.columns(2)
    if col1.button("Änderungen speichern", type="primary"):
        data = {"kennzeichen": neu_kz, "wagennummer": neu_wagen, "betreiber": neu_betreiber, "marke": neu_marke, "modell": neu_modell, "baujahr": neu_baujahr, "notizen": neu_notizen}
        supabase.table("fahrzeuge").update(data).eq("id", auto_id).execute()
        st.session_state.page = "details"
        st.rerun()
    if col2.button("Abbrechen"):
        st.session_state.page = "details"
        st.rerun()
