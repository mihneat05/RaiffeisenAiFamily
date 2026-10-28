"""Raiffeisen Family Agent: frontend Streamlit (P4), cu identitate vizuală Raiffeisen și layout pentru telefon.

Rulează cu:  streamlit run app.py
Tot ce ține de agent / acte / validare trece prin backend.py.
"""
import base64
from pathlib import Path

import streamlit as st

try:  # detectarea locației din browser (GPS, cu rezervă după IP)
    from streamlit_js_eval import streamlit_js_eval
except ImportError:
    streamlit_js_eval = None

import backend
from pdf_export import build_checklist_pdf

ROOT = Path(__file__).parent
LOGO = ROOT / "assets" / "raiffeisen_logo.png"

st.set_page_config(page_title="Raiffeisen Family Agent",
                   page_icon=str(LOGO) if LOGO.exists() else "🏦",
                   layout="wide", initial_sidebar_state="collapsed")

ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌", "pending": "⏳"}
STATUS_TEXT = {"ok": "în regulă", "warn": "de verificat", "fail": "are o problemă", "pending": "încă neîncărcat"}
HEADLINE = {
    "ok": "Ești pregătit să mergi la bancă.",
    "warn": "Aproape gata. Mai sunt câteva lucruri de verificat.",
    "fail": "Încă nu e momentul. Îți mai lipsesc acte sau unele au probleme.",
}
WELCOME = (
    "Bună! Sunt asistentul Raiffeisen pentru momentele importante din familie. "
    "Spune-mi ce situație ai (de exemplu un deces în familie, o căsătorie sau o procură) "
    "și te ajut să afli ce acte îți trebuie, ca să vii la bancă o singură dată.\n\n"
    "_Sunt un asistent AI: nu iau decizii, verificarea finală se face la bancă._"
)

# ------------------------------------------------------------------ stil
YELLOW, BLACK, GREY = "#FFED00", "#1C161C", "#F4F4F2"

CSS = f"""
<style>
  :root {{ --rb-yellow:{YELLOW}; --rb-black:{BLACK}; --rb-grey:{GREY}; }}
  html, body, [class*="css"] {{ font-family: "Source Sans Pro", "Segoe UI", Arial, sans-serif; }}
  .stApp {{ background: var(--rb-grey); }}
  header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
  .block-container {{ padding-top: 0 !important; padding-bottom: 2rem; max-width: 1240px; }}

  /* bara de sus */
  [data-testid="stToolbar"], [data-testid="stDecoration"], .stDeployButton {{ display:none !important; }}
  .rb-top {{ background: var(--rb-yellow); width:100vw; position:relative; left:50%; transform:translateX(-50%);
            margin-bottom:1.4rem; padding: 18px max(1.2rem, calc(50vw - 600px)) 16px;
            display:flex; align-items:center; gap:16px; box-sizing:border-box; }}
  .rb-top img {{ width:52px; height:52px; border-radius:10px; }}
  .rb-top .t1 {{ font-size:1.45rem; font-weight:800; color:var(--rb-black); line-height:1.1; }}
  .rb-top .t2 {{ font-size:.95rem; color:var(--rb-black); opacity:.8; }}
  .rb-tag {{ margin-left:auto; background:var(--rb-black); color:var(--rb-yellow); font-size:.72rem;
            font-weight:700; padding:4px 10px; border-radius:999px; white-space:nowrap; }}

  /* carduri */
  .st-key-dosar, .st-key-sucursala {{ background:#fff; border-radius:16px; padding:18px 18px 10px;
            box-shadow:0 1px 3px rgba(0,0,0,.06); margin-bottom:14px; }}
  .st-key-chatbox {{ background:#fff; border-radius:16px; box-shadow:0 1px 3px rgba(0,0,0,.06); }}
  .rb-title {{ font-weight:800; font-size:1.3rem; color:var(--rb-black); margin-bottom:10px;
               border-bottom:3px solid var(--rb-yellow); display:inline-block; padding-bottom:2px; }}
  .rb-h {{ font-weight:800; font-size:1.05rem; color:var(--rb-black); margin:2px 0 8px;
           display:flex; align-items:center; gap:8px; }}
  .rb-h .n {{ background:var(--rb-yellow); color:var(--rb-black); width:24px; height:24px; border-radius:50%;
             display:inline-flex; align-items:center; justify-content:center; font-size:.85rem; }}

  /* verdict */
  .rb-verdict {{ border-radius:14px; padding:14px 16px; margin:6px 0 12px; font-size:.98rem; }}
  .rb-verdict b {{ font-size:1.08rem; }}
  .rb-verdict ul {{ margin:8px 0 0 0; padding-left:18px; }}
  .rb-ok   {{ background:#E7F6EC; border-left:6px solid #1E8E3E; }}
  .rb-warn {{ background:#FFF8D6; border-left:6px solid #C9A400; }}
  .rb-fail {{ background:#FDECEC; border-left:6px solid #C62828; }}

  /* checklist */
  .rb-row {{ display:flex; gap:10px; align-items:flex-start; padding:9px 0; border-bottom:1px solid #eee; }}
  .rb-row:last-child {{ border-bottom:none; }}
  .rb-row .ic {{ font-size:1.1rem; line-height:1.3; }}
  .rb-row .lb {{ font-weight:700; color:var(--rb-black); }}
  .rb-row .st {{ font-size:.85rem; color:#666; }}
  .rb-row .rs {{ font-size:.85rem; color:#8a1c1c; margin-top:2px; }}

  /* butoane în culorile băncii */
  .stButton > button, .stDownloadButton > button, .stLinkButton > a {{
      border-radius:999px !important; font-weight:700 !important; min-height:44px; }}
  .stDownloadButton > button, .stLinkButton > a {{ background:var(--rb-yellow) !important;
      color:var(--rb-black) !important; border:none !important; }}
  .stDownloadButton > button:hover, .stLinkButton > a:hover {{ filter:brightness(.95); }}
  [data-testid="stChatInput"] {{ border-radius:999px; }}
  .stRadio [role="radiogroup"] {{ gap:6px 14px; flex-wrap:wrap; }}

  /* plasă de siguranță dacă cineva a ales tema întunecată din meniul Streamlit */
  .st-key-dosar :is(p, label, span, li, div), .st-key-sucursala :is(p, label, span, div),
  .st-key-chatbox :is(p, li, span, em, strong) {{ color: var(--rb-black); }}
  .rb-tag {{ color: var(--rb-yellow) !important; }}

  .st-key-sucursala [data-testid="stTextInputRootElement"], .st-key-sucursala [data-baseweb="input"] {{
      border:1.5px solid #bdbdbd !important; border-radius:999px !important; background:var(--rb-grey) !important; }}
  .st-key-sucursala input {{ background:transparent !important; padding-left:14px !important; }}

  .rb-foot {{ text-align:center; font-size:.78rem; color:#777; margin-top:18px; }}

  /* ---------- telefon ---------- */
  @media (max-width: 760px) {{
    .block-container {{ padding-left:.8rem !important; padding-right:.8rem !important; }}
    .rb-top {{ margin-bottom:1rem; padding: 12px .9rem; gap:10px; }}
    .rb-top img {{ width:40px; height:40px; }}
    .rb-top .t1 {{ font-size:1.15rem; }}
    .rb-top .t2 {{ display:none; }}
    .rb-tag {{ font-size:.65rem; padding:3px 8px; }}
    .st-key-chatbox {{ height:55vh !important; }}
    [data-testid="stColumn"] {{ width:100% !important; flex:1 1 100% !important; min-width:100% !important; }}
    .st-key-dosar, .st-key-sucursala {{ padding:14px 12px 6px; border-radius:14px; }}
  }}
</style>
"""


def logo_html():
    if not LOGO.exists():
        return ""
    b64 = base64.b64encode(LOGO.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="Raiffeisen">'


def render_header():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="rb-top">{logo_html()}<div><div class="t1">Family Agent</div>'
        f'<div class="t2">Vino pregătit la bancă, cu toate actele, dintr-o singură vizită.</div></div>'
        f'<span class="rb-tag">PROTOTIP · HACKATHON</span></div>',
        unsafe_allow_html=True)


# ------------------------------------------------------------------ stare
def init_state():
    st.session_state.setdefault("messages", [{"role": "assistant", "content": WELCOME}])
    st.session_state.setdefault("docs", [])
    st.session_state.setdefault("uploader_gen", 0)
    # Agentul poate detecta situația din chat; selecția se actualizează la rerun-ul următor.
    if "pending_event" in st.session_state:
        st.session_state.event_picker = st.session_state.pop("pending_event")


def reset_session():
    gen = st.session_state.get("uploader_gen", 0) + 1
    st.session_state.clear()
    st.session_state.uploader_gen = gen  # cheie nouă = uploader gol


def mask_cnp(value):
    value = str(value)
    return value[0] + "•" * 9 + value[-3:] if len(value) == 13 else value


def describe_doc(doc):
    text = f"Am primit **{doc['label']}** ({doc['filename']}): {ICON[doc['status']]} {STATUS_TEXT[doc['status']]}."
    return text + "".join(f"\n- {r}" for r in doc["reasons"])


def sync_docs(files, event):
    """Ține st.session_state.docs în pas cu ce e în uploader: fișierele noi se procesează, cele scoase dispar."""
    current = {f"{f.name}:{f.size}": f for f in files or []}
    docs = [d for d in st.session_state.docs if d["fid"] in current]
    known = {d["fid"] for d in docs}
    for fid, f in current.items():
        if fid in known:
            continue
        with st.spinner(f"Citesc „{f.name}”…"):
            doc = backend.process_upload(f.name, f.getvalue(), event)
        doc["fid"] = fid
        docs.append(doc)
        st.session_state.messages.append({"role": "assistant", "content": describe_doc(doc)})
    st.session_state.docs = docs


def checklist_rows(event, docs):
    rows, used = [], set()
    for req in backend.required_docs(event):
        doc = next((d for d in docs if d["doc_type"] == req["type"] and d["fid"] not in used), None)
        if doc:
            used.add(doc["fid"])
        rows.append({"label": req["label"], "status": doc["status"] if doc else "pending",
                     "reasons": doc["reasons"] if doc else [], "doc": doc})
    return rows


# ------------------------------------------------------------------ bucăți de UI
def step(n, title):
    st.markdown(f'<div class="rb-h"><span class="n">{n}</span>{title}</div>', unsafe_allow_html=True)


def render_dosar():
    """Cardul „Dosarul tău”: situația, acordul + upload, verdictul și checklist-ul."""
    with st.container(key="dosar"):
        st.markdown('<div class="rb-title">Dosarul tău</div>', unsafe_allow_html=True)
        step(1, "Ce situație ai?")
        event = st.radio("Situația", list(backend.EVENTS), format_func=backend.EVENTS.get,
                         index=None, key="event_picker", horizontal=True, label_visibility="collapsed")

        step(2, "Încarcă actele")
        consent = st.checkbox("Sunt de acord ca actele mele să fie procesate temporar, doar pentru această sesiune.",
                              key="consent")
        files = st.file_uploader("Poze sau PDF", type=["pdf", "jpg", "jpeg", "png"],
                                 accept_multiple_files=True, disabled=not consent,
                                 key=f"uploader_{st.session_state.uploader_gen}",
                                 label_visibility="collapsed")
        st.caption("🔒 Actele se șterg la finalul sesiunii. CNP-ul nu apare în log-uri.")

        sync_docs(files, event)
        docs = st.session_state.docs
        verdict = backend.crosscheck(docs, event) if event else None

        step(3, "Verdict")
        if not event:
            st.caption("Alege situația sau povestește-mi în chat, și îți arăt ce acte îți trebuie.")
        else:
            render_verdict(verdict)
            rows = checklist_rows(event, docs)
            render_checklist(rows, docs)
            st.download_button(
                "📄 Descarcă checklist-ul (PDF)",
                data=build_checklist_pdf(backend.EVENTS[event], rows, HEADLINE[verdict["status"]],
                                         verdict["reasons"], best_branch()),
                file_name="checklist_raiffeisen.pdf", mime="application/pdf", use_container_width=True)
    return event, verdict


def render_verdict(verdict):
    s = verdict["status"]
    reasons = "".join(f"<li>{r}</li>" for r in verdict["reasons"])
    st.markdown(f'<div class="rb-verdict rb-{s}">{ICON[s]} <b>{HEADLINE[s]}</b>'
                f'{f"<ul>{reasons}</ul>" if reasons else ""}</div>', unsafe_allow_html=True)
    st.caption("Verificare consultativă. Decizia finală o ia consilierul din sucursală.")


def render_checklist(rows, docs):
    html = ""
    for row in rows:
        rs = "".join(f'<div class="rs">↳ {r}</div>' for r in row["reasons"])
        html += (f'<div class="rb-row"><span class="ic">{ICON[row["status"]]}</span><div>'
                 f'<div class="lb">{row["label"]}</div><div class="st">{STATUS_TEXT[row["status"]]}</div>{rs}</div></div>')
    st.markdown(html, unsafe_allow_html=True)

    used = {r["doc"]["fid"] for r in rows if r["doc"]}
    extra = [d for d in docs if d["fid"] not in used]
    if extra:
        st.markdown("**Alte acte încărcate**")
        for d in extra:
            st.markdown(f"{ICON[d['status']]} {d['label']} ({d['filename']})")
    if docs:
        with st.expander("Ce am citit din acte"):
            for d in docs:
                st.markdown(f"**{d['label']}** · `{d['filename']}`")
                st.json({k: mask_cnp(v) if "cnp" in k else v for k, v in d["fields"].items()}, expanded=False)


def _cauta_sucursala():
    loc = st.session_state.get("loc_input", "").strip()
    if loc:
        st.session_state.locatie = loc
        st.session_state.branch_result = backend.find_branches(loc)


# GPS-ul merge doar pe https sau localhost; altfel (ex. telefon pe http://192.168...) cădem pe locația după IP.
GEO_JS = """(async () => {
  const gps = await new Promise(res => {
    if (!navigator.geolocation || !window.isSecureContext) return res(null);
    navigator.geolocation.getCurrentPosition(
      p => res({lat: p.coords.latitude, lon: p.coords.longitude, sursa: "gps", precizie: Math.round(p.coords.accuracy)}),
      () => res(null), {enableHighAccuracy: true, timeout: 9000, maximumAge: 600000});
  });
  if (gps) return gps;
  for (const [url, f] of [["https://ipapi.co/json/", j => [j.latitude, j.longitude, j.city]],
                          ["https://get.geojs.io/v1/ip/geo.json", j => [+j.latitude, +j.longitude, j.city]]]) {
    try { const j = await (await fetch(url)).json(); const [la, lo, c] = f(j);
          if (la && lo) return {lat: la, lon: lo, sursa: "ip", oras: c}; } catch (e) {}
  }
  return {eroare: "nu am putut detecta locația"};
})()"""


def _cere_gps():
    st.session_state.geo_req = st.session_state.get("geo_req", 0) + 1


def detecteaza_locatia():
    """Rulează JS în browser după apăsarea butonului; când vine răspunsul, caută sucursalele."""
    req = st.session_state.get("geo_req", 0)
    if not req or req == st.session_state.get("geo_done") or streamlit_js_eval is None:
        return
    pos = streamlit_js_eval(js_expressions=GEO_JS, key=f"geo_{req}")
    if not pos:
        st.caption("📍 Caut locația ta… (dacă browserul întreabă, apasă „Permite”)")
        return
    st.session_state.geo_done = req
    if pos.get("eroare"):
        st.session_state.branch_result = {"eroare": "fara_locatie",
                                          "mesaj": "Nu am putut detecta locația. Scrie orașul și cartierul mai sus."}
        return
    eticheta = "locația ta (GPS)" if pos["sursa"] == "gps" else f"{pos.get('oras') or 'zona ta'} (aproximativ, după conexiune)"
    st.session_state.locatie = eticheta
    st.session_state.branch_result = backend.find_branches_coords(pos["lat"], pos["lon"], eticheta)
    st.rerun()


def adresa_din_buletin():
    """Domiciliul citit de P2 de pe primul buletin încărcat (sau None)."""
    for d in st.session_state.get("docs", []):
        if d.get("doc_type") == "buletin" and (d.get("fields") or {}).get("adresa"):
            return d["fields"]["adresa"]
    return None


def _cauta_dupa_buletin():
    adresa = adresa_din_buletin()
    if adresa:
        st.session_state.branch_result = backend.find_branches_from_address(adresa)
        st.session_state.locatie = "domiciliul din buletin"


def best_branch():
    res = st.session_state.get("branch_result") or {}
    return (res.get("sucursale") or [None])[0] or backend.find_branch()


def render_branch():
    with st.container(key="sucursala"):
        st.markdown('<div class="rb-h">📍 Unde mergi</div>', unsafe_allow_html=True)
        with st.form("form_sucursala", border=False):
            st.text_input("Unde ești?", key="loc_input", placeholder="ex: Militari, București  sau  Str. Mihai Viteazu 10, Cluj",
                          label_visibility="collapsed")
            st.form_submit_button("🔎 Caută cea mai apropiată sucursală", on_click=_cauta_sucursala,
                                  use_container_width=True)
        c1, c2 = st.columns(2) if adresa_din_buletin() else (st.container(), None)
        with c1:
            if streamlit_js_eval is not None:
                st.button("📍 Folosește locația mea", on_click=_cere_gps, use_container_width=True, key="btn_gps")
        if c2 is not None:
            with c2:
                st.button("🪪 Lângă adresa din buletin", on_click=_cauta_dupa_buletin,
                          use_container_width=True, key="btn_buletin")
        detecteaza_locatia()

        res = st.session_state.get("branch_result")
        if not res:
            st.caption("Scrie orașul și cartierul (sau adresa) și îți arăt cele mai apropiate unități Raiffeisen.")
            return
        if not res.get("sucursale"):
            st.warning(res.get("mesaj", "Nu am găsit sucursale."))
            if res.get("detalii"):
                with st.expander("Detalii tehnice (pentru echipă)"):
                    st.code(res["detalii"], language=None)
            return

        st.caption(f"Lângă: {res['locatie'].get('gasit', '')[:90]}")
        if res.get("din_buletin"):
            st.caption("🪪 După domiciliul din buletin. Dacă acum stai în altă parte, scrie locația mai sus.")
        for i, b in enumerate(res["sucursale"]):
            with st.container(border=True):
                st.markdown(f"{'⭐ ' if i == 0 else ''}**{b['name']}** · {b['distance']}  \n{b['address']}")
                st.caption(b["hours"] + (f" · ☎ {b['phone']}" if b.get("phone") else ""))
                st.link_button("🧭 Navighează aici", b["booking_url"], use_container_width=True)
        loc = res.get("locatie", {})
        puncte = [{"lat": b["lat"], "lon": b["lon"], "color": "#1C161C", "size": 60} for b in res["sucursale"]]
        if loc.get("lat") is not None:
            puncte.append({"lat": loc["lat"], "lon": loc["lon"], "color": "#E5C700", "size": 90})
        if puncte:
            import pandas as pd
            st.map(pd.DataFrame(puncte), latitude="lat", longitude="lon", color="color", size="size", zoom=12, height=230)
            st.caption("⚫ sucursale · 🟡 tu")
        st.caption("Sursa: OpenStreetMap. Confirmă programul pe raiffeisen.ro sau la *2000.")


def render_chat(event, verdict):
    box = st.container(height=600, key="chatbox")
    with box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"], avatar=str(LOGO) if m["role"] == "assistant" and LOGO.exists() else None):
                st.markdown(m["content"])

    if prompt := st.chat_input("Scrie-mi ce situație ai…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        ctx = {
            "event": event,
            "docs": [{k: d[k] for k in ("doc_type", "label", "status", "reasons")} for d in st.session_state.docs],
            "verdict": verdict,
            "history": st.session_state.messages,
            "locatie": st.session_state.get("locatie"),
            "are_adresa_in_buletin": bool(adresa_din_buletin()),
        }
        with box, st.spinner("Mă gândesc…"):
            result = backend.agent_turn(prompt, ctx)
        st.session_state.messages.append({"role": "assistant", "content": result["reply"]})
        br = result.get("branches")
        if br and br.get("sucursale"):  # agentul a căutat sucursale din chat -> le arătăm și în card
            st.session_state.branch_result = br
            st.session_state.locatie = br.get("locatie", {}).get("text")
        if result.get("event") and result["event"] != event:
            st.session_state.pending_event = result["event"]
        st.rerun()


def render_sidebar():
    """Bara laterală rămâne doar pentru echipă (închisă implicit, nu încurcă pe telefon)."""
    with st.sidebar:
        with st.expander("Stare module (pentru echipă)", expanded=True):
            for name, mocked in backend.MOCKED.items():
                st.write(f"{'🟡 mock' if mocked else '🟢 real'} · {name}")


def main():
    init_state()
    render_header()
    render_sidebar()

    chat_col, side_col = st.columns([3, 2], gap="large")
    with side_col:
        event, verdict = render_dosar()
        render_branch()
        st.button("🗑️ Începe din nou (șterge actele)", on_click=reset_session, use_container_width=True)
    with chat_col:
        render_chat(event, verdict)

    st.markdown('<div class="rb-foot">Asistent AI consultativ · nu ia decizii și nu face operațiuni bancare · '
                'prototip realizat în cadrul hackathonului</div>', unsafe_allow_html=True)


main()
