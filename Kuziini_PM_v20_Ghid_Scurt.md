# Kuziini Project Manager v20 — Ghid scurt
*Versiune document: 2025-08-17 06:48*

Acest ghid descrie profesional, concis și practic funcționalitățile fiecărei secțiuni. 
Structura aplicației este **stabilă** și nu va fi modificată fără decizie explicită privind designul.

---

## Structură module (fixă)
- **Dashboard** — KPI & rezumate execuție
- **Vedere generală** — registru proiecte filtrabil
- **Secțiuni producție** — etape Debitare → CNC → Vopsitorie → Asamblare → Ambalare/Livrare → Montaj
- **Setări proiect** — parametri per proiect
- **Comandă nouă** — introducere rapidă proiect/comandă
- **Utilizatori & roluri** — administrare acces
- **Profil utilizator** — preferințe personale
- **Diagnoză date** — verificări integritate Excel

---

## 1) Dashboard
**Rol:** Indicatori cheie ai proiectelor curente: volum, progres, întârzieri, sarcini critice.  
**Funcționare:** KPI din foaia «Proiecte» (total active, la risc, progres mediu, trend). Link-uri către proiectele cu risc.

## 2) Vedere generală
**Rol:** Listă filtrabilă a tuturor proiectelor cu stări, termene și responsabili.  
**Funcționare:** Filtre/ordine după client, termen, status 25/50/75/100, manager. Deschidere fișă proiect.

## 3) Secțiuni producție
**Rol:** Monitorizează etapele: Debitare, CNC, Vopsitorie, Asamblare, Ambalare/Livrare, Montaj.  
**Funcționare:** Timeline/coloane, progres pe faze, blocaje, dependențe. Update-urile se reflectă în KPI și fișa proiectului.

## 4) Setări proiect
**Rol:** Parametri operaționali per proiect: buget, deadline, manager, priorități.  
**Funcționare:** Formular standardizat; persistă în date; alimentează scorul de risc și alertele.

## 5) Comandă nouă
**Rol:** Înregistrare rapidă a unei comenzi/proiect cu ID unic.  
**Funcționare:** Generează «OF-YYYY-NNNN», setează client/dimensiuni/descriere/responsabil/termene. Scriere în «Proiecte» sau «Comenzi».

## 6) Utilizatori & roluri
**Rol:** Administrare utilizatori și roluri (viewer/manager/owner).  
**Funcționare:** Controlează acțiuni sensibile (setări proiect, export). Opțional: audit minimal.

## 7) Profil utilizator
**Rol:** Preferințe personale (limbă, temă, notificări).  
**Funcționare:** Nu afectează configurațiile globale. Persistă local.

## 8) Diagnoză date
**Rol:** Verifică integritatea fișierelor Excel (coloane critice, valori lipsă, anomalii).  
**Funcționare:** Rulează controale automate și oferă recomandări de remediere. Produce raport sumar.

---

## Schelet tehnic (orientare rapidă)
- **Entrypoint:** `streamlit_app.py` (router + sidebar)
- **Module UI:** `containers/`
- **Servicii date:** `utils/data_loader.py`
- **Resurse:** `assets/` (logo), `data/` (Excel)
- **Temă:** `.streamlit/config.toml`
- **Dependențe:** `requirements.txt`

```ascii
[UI Sidebar] → [Router] → [containers/*] → [utils/data_loader] → [Excel]
                   ↘ KPI / Secțiuni / Setări / Users ↙
```

---

## Notă operare
- Orice modificare de funcționalitate va fi reflectată în această documentație și în panoul de ajutor din sidebar.
- Structura generală rămâne neschimbată până la o decizie explicită de redesign.

