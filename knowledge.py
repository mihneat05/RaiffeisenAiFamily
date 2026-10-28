"""knowledge.py - puntea dintre frontend (P4) și knowledge base (P5).

Frontendul cere:  required_docs(event) -> [{"type": tip_act, "label": nume afișat}]
`type` e tip_act-ul pe care îl întoarce read_document (P2), ca să se potrivească în checklist.
"""
from agent import KB, KB_TO_TIP, P4_TO_FLUX, SCENARIU_IMPLICIT, act_name, find_scenario


def required_docs(event):
    flux = P4_TO_FLUX.get(event)
    if not flux or flux not in KB:
        return []
    sc = find_scenario(flux, SCENARIU_IMPLICIT[flux])
    return [{"type": KB_TO_TIP.get(a, a), "label": act_name(flux, a).split(" (")[0]} for a in sc["acte_necesare"]]
