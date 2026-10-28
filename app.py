"""Raiffeisen Family Agent: frontend Streamlit (P4).

Rulează cu:  streamlit run app.py
Tot ce ține de agent / acte / validare trece prin backend.py.
"""
import streamlit as st

import backend
from pdf_export import build_checklist_pdf

st.set_page_config(page_title="Raiffeisen Family Agent", page_icon="🏦", layout="wide")

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


def init_state():
    st.session_state.setdefault("messages", [{"role": "assistant", "content": WELCOME}])
    st.session_state.setdefault("docs", [])
    st.session_state.setdefault("uploader_gen", 0)
    # Agentul poate detecta situația din chat; radio-ul se actualizează la rerun-ul următor.
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
    rows = []
    for req in backend.required_docs(event):
        doc = next((d for d in docs if d["doc_type"] == req["type"]), None)
        rows.append({
            "label": req["label"],
            "status": doc["status"] if doc else "pending",
            "reasons": doc["reasons"] if doc else [],
            "doc": doc,
        })
    return rows


def render_sidebar():
    with st.sidebar:
        st.header("🏦 Family Agent")
        event = st.radio(
            "Ce situație ai?",
            list(backend.EVENTS),
            format_func=backend.EVENTS.get,
            index=None,
            key="event_picker",
        )
        st.divider()
        consent = st.checkbox(
            "Sunt de acord ca actele mele să fie procesate temporar, doar pentru această sesiune.",
            key="consent",
        )
        files = st.file_uploader(
            "Încarcă actele (poze sau PDF)",
            type=["pdf", "jpg", "jpeg", "png"],
            accept_multiple_files=True,
            disabled=not consent,
            key=f"uploader_{st.session_state.uploader_gen}",
        )
        st.caption("Actele se șterg la finalul sesiunii. CNP-ul nu apare în log-uri.")
        st.button("🗑️ Șterge sesiunea și actele", on_click=reset_session, use_container_width=True)

        with st.expander("Stare module (pentru echipă)"):
            for name, mocked in backend.MOCKED.items():
                st.write(f"{'🟡 mock' if mocked else '🟢 real'} · {name}")
    return event, files


def render_chat(event, verdict):
    box = st.container(height=560)
    with box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"], avatar="🏦" if m["role"] == "assistant" else None):
                st.markdown(m["content"])

    if prompt := st.chat_input("Scrie aici ce situație ai sau ce te îngrijorează…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        ctx = {
            "event": event,
            "docs": [{k: d[k] for k in ("doc_type", "label", "status", "reasons")} for d in st.session_state.docs],
            "verdict": verdict,
            "history": st.session_state.messages,
        }
        with box, st.spinner("Mă gândesc…"):
            result = backend.agent_turn(prompt, ctx)
        st.session_state.messages.append({"role": "assistant", "content": result["reply"]})
        if result.get("event") and result["event"] != event:
            st.session_state.pending_event = result["event"]
        st.rerun()


def render_verdict(verdict):
    show = {"ok": st.success, "warn": st.warning, "fail": st.error}[verdict["status"]]
    reasons = "".join(f"\n- {r}" for r in verdict["reasons"])
    show(f"{ICON[verdict['status']]} **{HEADLINE[verdict['status']]}**{reasons}")
    st.caption("Verificare consultativă. Decizia finală o ia consilierul din sucursală.")


def render_checklist(rows, docs):
    st.subheader("Checklist")
    for row in rows:
        st.markdown(f"{ICON[row['status']]} **{row['label']}** · {STATUS_TEXT[row['status']]}")
        for r in row["reasons"]:
            st.caption(f"↳ {r}")

    required = {id(r["doc"]) for r in rows if r["doc"]}
    extra = [d for d in docs if id(d) not in required]
    if extra:
        st.markdown("**Alte acte încărcate**")
        for d in extra:
            st.markdown(f"{ICON[d['status']]} {d['label']} ({d['filename']})")

    if docs:
        with st.expander("Ce am citit din acte"):
            for d in docs:
                st.markdown(f"**{d['label']}** · `{d['filename']}`")
                fields = {k: mask_cnp(v) if "cnp" in k else v for k, v in d["fields"].items()}
                st.json(fields, expanded=False)


def render_branch(branch):
    with st.container(border=True):
        st.markdown(f"📍 **{branch['name']}**")
        st.write(branch["address"])
        st.caption(f"{branch['hours']} · la {branch['distance']} de tine")
        st.link_button("Programează-te", branch["booking_url"], use_container_width=True)


def main():
    init_state()
    event, files = render_sidebar()
    sync_docs(files, event)
    docs = st.session_state.docs
    verdict = backend.crosscheck(docs, event) if event else None

    st.title("Raiffeisen Family Agent")
    st.caption("Te ajut să vii pregătit la bancă, cu toate actele, dintr-o singură vizită.")

    chat_col, side_col = st.columns([3, 2], gap="large")
    with side_col:
        if not event:
            st.info("Alege situația în stânga sau povestește-mi în chat și îți arăt ce acte îți trebuie.")
        else:
            render_verdict(verdict)
            rows = checklist_rows(event, docs)
            render_checklist(rows, docs)
            st.download_button(
                "📄 Descarcă checklist-ul (PDF)",
                data=build_checklist_pdf(backend.EVENTS[event], rows, HEADLINE[verdict["status"]], verdict["reasons"], backend.find_branch()),
                file_name="checklist_raiffeisen.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.subheader("Unde mergi")
            render_branch(backend.find_branch())
    with chat_col:
        render_chat(event, verdict)


main()
