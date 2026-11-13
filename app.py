import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- 1. SETUP & DATENBANK ---
os.makedirs("fotos", exist_ok=True)
conn = sqlite3.connect("bus_archiv.db", check_same_thread=False)
c = conn.cursor()

c.execute('CREATE TABLE IF NOT EXISTS fahrzeuge (id INTEGER PRIMARY KEY AUTOINCREMENT, kennzeichen TEXT, marke TEXT, modell TEXT, baujahr INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS fotos (id INTEGER PRIMARY KEY AUTOINCREMENT, fahrzeug_id INTEGER, pfad TEXT, datum TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS standorte (id INTEGER PRIMARY KEY AUTOINCREMENT, fahrzeug_id INTEGER, standort TEXT, datum_von TEXT, datum_bis TEXT)')

# Neue Spalten einzeln nachträglich hinzufügen, falls sie fehlen
try:
    c.execute('ALTER TABLE fahrzeuge ADD COLUMN wagennummer TEXT')
except: pass

try:
    c.execute('ALTER TABLE fahrzeuge ADD COLUMN betreiber TEXT')
except: pass

try:
    c.execute('ALTER TABLE fahrzeuge ADD COLUMN notizen TEXT')
except: pass

try:
    c.execute('ALTER TABLE fotos ADD COLUMN aufnahme_standort TEXT')
except: pass

conn.commit()

# --- 2. HILFSFUNKTIONEN ---
def parse_datum(datum_str):
    if datum_str and datum_str != "??":
        try: return datetime.strptime(datum_str, "%d.%m.%Y").date()
        except: return None
    return None

def get_liste(spalte, tabelle="fahrzeuge"):
    try:
        werte = pd.read_sql(f"SELECT DISTINCT {spalte} FROM {tabelle} WHERE {spalte} IS NOT NULL AND {spalte} != ''", conn)
        return sorted(werte[spalte].astype(str).tolist())
    except:
        return []

def form_auswahl(label, spalte, tabelle="fahrzeuge", aktueller_wert="", key=None):
    optionen = ["➕ Neu eingeben..."] + get_liste(spalte, tabelle)
    
    idx = 0
    if aktueller_wert and aktueller_wert in optionen:
        idx = optionen.index(aktueller_wert)
        
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

# --- KOPFZEILE (Header) ---
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
# BEREICH: STARTSEITE (LISTENANSICHT)
# ==========================================
if st.session_state.page == "liste":
    
    col1, col2 = st.columns([3, 1])
    col1.title("Datenbank")
    if col2.button("✏️ Neues Fahrzeug", use_container_width=True):
        st.session_state.page = "neu"
        st.rerun()
    
    query = """
    SELECT f.*, 
           (SELECT GROUP_CONCAT(standort, ' ') FROM standorte WHERE fahrzeug_id = f.id) as s_orte,
           (SELECT GROUP_CONCAT(aufnahme_standort, ' ') FROM fotos WHERE fahrzeug_id = f.id) as f_orte
    FROM fahrzeuge f
    """
    fahrzeuge = pd.read_sql(query, conn)
    fahrzeuge.fillna({'wagennummer': '', 'betreiber': '', 'baujahr': '', 'marke': '', 'modell': '', 'notizen': '', 's_orte': '', 'f_orte': ''}, inplace=True)
    
    if not fahrzeuge.empty:
        suchbegriff = st.text_input("🔍 Schnellsuchen (Kennzeichen, Wagen-Nr., Modell, Betreiber, Standort, Notiz...):")
        
        gefiltert = fahrzeuge.copy()
        if suchbegriff:
            mask = gefiltert.astype(str).apply(lambda row: row.str.contains(suchbegriff, case=False).any(), axis=1)
            gefiltert = gefiltert[mask]
        
        st.write(f"**{len(gefiltert)} Datensätze**")
        st.markdown("---")
        
        for _, row in gefiltert.iterrows():
            wagen = f" [Wg: {row['wagennummer']}]" if row['wagennummer'] else ""
            betreiber = f" | {row['betreiber']}" if row['betreiber'] else ""
            baujahr = f" | Bj: {int(row['baujahr'])}" if row['baujahr'] != '' else ""
            
            button_text = f"🚍 {row['kennzeichen']}{wagen}  ➔  {row['marke']} {row['modell']}{baujahr}{betreiber}"
            
            if st.button(button_text, key=f"bus_{row['id']}", use_container_width=True):
                st.session_state.bus_id = row['id']
                st.session_state.page = "details"
                st.rerun()
                
    else:
        st.info("Die Datenbank ist aktuell leer. Klicke oben auf 'Neues Fahrzeug'.")

# ==========================================
# BEREICH: DETAILANSICHT
# ==========================================
elif st.session_state.page == "details" and st.session_state.bus_id is not None:
    
    auto_id = st.session_state.bus_id
    auto = pd.read_sql(f"SELECT * FROM fahrzeuge WHERE id = {auto_id}", conn).iloc[0]
    
    baujahr_val = str(int(auto['baujahr'])) if pd.notnull(auto['baujahr']) and auto['baujahr'] != "" else "-"
    wagen_val = auto['wagennummer'] if pd.notnull(auto['wagennummer']) and auto['wagennummer'] else "-"
    betreiber_val = auto['betreiber'] if pd.notnull(auto['betreiber']) and auto['betreiber'] else "-"
    notizen_val = auto['notizen'] if pd.notnull(auto['notizen']) and auto['notizen'] else ""
    
    st.title(auto['kennzeichen'])
    
    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("✏️ Bearbeiten"):
        st.session_state.page = "bearbeiten"
        st.rerun()
    if c2.button("🗑️ Löschen"):
        c.execute("DELETE FROM fahrzeuge WHERE id=?", (auto_id,))
        c.execute("DELETE FROM fotos WHERE fahrzeug_id=?", (auto_id,))
        c.execute("DELETE FROM standorte WHERE fahrzeug_id=?", (auto_id,))
        conn.commit()
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
    
    # Notizen anzeigen, falls vorhanden
    if notizen_val:
        st.write("---")
        st.write("### 📝 Notizen")
        st.write(notizen_val)
        
    st.markdown("---")
    
    # FOTOS
    st.write("### 📸 Fotos")
    fotos = pd.read_sql(f"SELECT id, pfad, datum, aufnahme_standort FROM fotos WHERE fahrzeug_id = {auto_id} ORDER BY id DESC", conn)
    
    if not fotos.empty:
        for _, foto in fotos.iterrows():
            foto_id = foto['id']
            if os.path.exists(foto['pfad']):
                
                caption_text = f"Aufnahme: {foto['datum']}"
                if pd.notnull(foto['aufnahme_standort']) and foto['aufnahme_standort']:
                    caption_text += f" | Ort: {foto['aufnahme_standort']}"
                    
                st.image(foto['pfad'], caption=caption_text)
                
                with st.expander("Foto bearbeiten / löschen"):
                    altes_datum = parse_datum(foto['datum']) or datetime.now().date()
                    neu_datum = st.date_input("Datum ändern", value=altes_datum, key=f"date_{foto_id}")
                    
                    aktueller_ort = foto['aufnahme_standort'] if pd.notnull(foto['aufnahme_standort']) else ""
                    neu_foto_ort = form_auswahl("Aufnahme Standort", "aufnahme_standort", "fotos", aktueller_ort, key=f"foto_ort_{foto_id}")
                    
                    bc1, bc2 = st.columns(2)
                    if bc1.button("Speichern", key=f"save_{foto_id}"):
                        c.execute("UPDATE fotos SET datum=?, aufnahme_standort=? WHERE id=?", (neu_datum.strftime("%d.%m.%Y"), neu_foto_ort, foto_id))
                        conn.commit()
                        st.rerun()
                    if bc2.button("Löschen", key=f"del_{foto_id}"):
                        try: os.remove(foto['pfad'])
                        except: pass
                        c.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
                        conn.commit()
                        st.rerun()
    else:
        st.write("Keine Fotos vorhanden.")
        
    with st.expander("➕ Neues Foto hochladen"):
        upload_datum = st.date_input("Aufnahmedatum", value=datetime.now().date(), key=f"upload_date_{auto_id}")
        neu_foto_ort = form_auswahl("Aufnahme Standort", "aufnahme_standort", "fotos", key=f"upload_ort_{auto_id}")
        neues_foto = st.file_uploader("Datei auswählen", type=['jpg', 'png', 'jpeg'], key=f"upload_{auto_id}")
        
        if neues_foto:
            pfad = os.path.join("fotos", neues_foto.name)
            c.execute("SELECT id FROM fotos WHERE fahrzeug_id = ? AND pfad = ?", (auto_id, pfad))
            if not c.fetchone():
                with open(pfad, "wb") as f:
                    f.write(neues_foto.getbuffer())
                c.execute("INSERT INTO fotos (fahrzeug_id, pfad, datum, aufnahme_standort) VALUES (?, ?, ?, ?)", (auto_id, pfad, upload_datum.strftime("%d.%m.%Y"), neu_foto_ort))
                conn.commit()
                st.rerun()

    st.markdown("---")
    
    # STANDORTE
    st.write("### 📍 Standort-Historie")
    standorte = pd.read_sql(f"SELECT id, standort, datum_von, datum_bis FROM standorte WHERE fahrzeug_id = {auto_id}", conn)
    
    if not standorte.empty:
        for _, ort_row in standorte.iterrows():
            ort_id = ort_row['id']
            with st.expander(f"{ort_row['standort']} ({ort_row['datum_von']} bis {ort_row['datum_bis']})"):
                
                neu_ort = form_auswahl("Standort", "standort", "standorte", ort_row['standort'], key=f"edit_ort_{ort_id}")
                neu_von = st.date_input("Von", value=parse_datum(ort_row['datum_von']), key=f"ort_von_{ort_id}")
                neu_bis = st.date_input("Bis", value=parse_datum(ort_row['datum_bis']), key=f"ort_bis_{ort_id}")
                
                oc1, oc2 = st.columns(2)
                if oc1.button("Speichern", key=f"ort_save_{ort_id}"):
                    str_von = neu_von.strftime("%d.%m.%Y") if neu_von else "??"
                    str_bis = neu_bis.strftime("%d.%m.%Y") if neu_bis else "??"
                    c.execute("UPDATE standorte SET standort=?, datum_von=?, datum_bis=? WHERE id=?", (neu_ort, str_von, str_bis, ort_id))
                    conn.commit()
                    st.rerun()
                if oc2.button("Löschen", key=f"ort_del_{ort_id}"):
                    c.execute("DELETE FROM standorte WHERE id=?", (ort_id,))
                    conn.commit()
                    st.rerun()
    else:
        st.write("Keine Historie hinterlegt.")
    
    with st.expander("➕ Neuen Standort eintragen"):
        ort_neu = form_auswahl("Ort / Betriebshof", "standort", "standorte", key="neu_ort_eingabe")
        von_neu = st.date_input("Von (optional)", value=None)
        bis_neu = st.date_input("Bis (optional)", value=None)
        
        if st.button("Standort speichern"):
            if ort_neu: 
                str_von_neu = von_neu.strftime("%d.%m.%Y") if von_neu else "??"
                str_bis_neu = bis_neu.strftime("%d.%m.%Y") if bis_neu else "??"
                c.execute("INSERT INTO standorte (fahrzeug_id, standort, datum_von, datum_bis) VALUES (?, ?, ?, ?)", (auto_id, ort_neu, str_von_neu, str_bis_neu))
                conn.commit()
                st.rerun()

# ==========================================
# BEREICH: NEUES FAHRZEUG
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
    
    notizen = st.text_area("Notizen (optional)", placeholder="Besonderheiten, Historie, Ausmusterungsgrund...")
    
    st.markdown("---")
    st.write("### Fotos direkt hinzufügen")
    upload_datum = st.date_input("Aufnahmedatum", value=datetime.now().date())
    foto_ort = form_auswahl("Aufnahme Standort", "aufnahme_standort", "fotos", key="neu_foto_ort")
    neue_fotos = st.file_uploader("Bilder auswählen", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
    
    if st.button("Speichern & Öffnen", type="primary"):
        if kennzeichen:
            c.execute("INSERT INTO fahrzeuge (kennzeichen, wagennummer, betreiber, marke, modell, baujahr, notizen) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      (kennzeichen, wagennummer, betreiber, marke, modell, baujahr, notizen))
            neue_auto_id = c.lastrowid
            
            if neue_fotos:
                str_datum = upload_datum.strftime("%d.%m.%Y")
                for f in neue_fotos:
                    pfad = os.path.join("fotos", f.name)
                    with open(pfad, "wb") as file:
                        file.write(f.getbuffer())
                    c.execute("INSERT INTO fotos (fahrzeug_id, pfad, datum, aufnahme_standort) VALUES (?, ?, ?, ?)", (neue_auto_id, pfad, str_datum, foto_ort))
            
            conn.commit()
            st.session_state.bus_id = neue_auto_id
            st.session_state.page = "details"
            st.rerun()
        else:
            st.error("Kennzeichen ist erforderlich.")

# ==========================================
# BEREICH: FAHRZEUG BEARBEITEN
# ==========================================
elif st.session_state.page == "bearbeiten" and st.session_state.bus_id is not None:
    
    auto_id = st.session_state.bus_id
    auto = pd.read_sql(f"SELECT * FROM fahrzeuge WHERE id = {auto_id}", conn).iloc[0]
    
    st.title("Fahrzeug bearbeiten")
    
    neu_kz = st.text_input("Kennzeichen", auto['kennzeichen'])
    neu_wagen = st.text_input("Wagennummer", auto['wagennummer'] if pd.notnull(auto['wagennummer']) else "")
    
    neu_marke = form_auswahl("Marke", "marke", "fahrzeuge", auto['marke'], key="edit_marke")
    neu_modell = form_auswahl("Modell", "modell", "fahrzeuge", auto['modell'], key="edit_modell")
    neu_betreiber = form_auswahl("Betreiber", "betreiber", "fahrzeuge", auto['betreiber'], key="edit_betreiber")
    
    bj_val = int(auto['baujahr']) if pd.notnull(auto['baujahr']) and auto['baujahr'] != '' else None
    neu_baujahr = st.number_input("Baujahr", value=bj_val)
    
    neu_notizen = st.text_area("Notizen", auto['notizen'] if pd.notnull(auto['notizen']) else "")
    
    col1, col2 = st.columns(2)
    if col1.button("Änderungen speichern", type="primary"):
        c.execute("UPDATE fahrzeuge SET kennzeichen=?, wagennummer=?, betreiber=?, marke=?, modell=?, baujahr=?, notizen=? WHERE id=?", 
                  (neu_kz, neu_wagen, neu_betreiber, neu_marke, neu_modell, neu_baujahr, neu_notizen, auto_id))
        conn.commit()
        st.session_state.page = "details"
        st.rerun()
        
    if col2.button("Abbrechen"):
        st.session_state.page = "details"
        st.rerun()
