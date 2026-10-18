---
type: agent
form: lead
dept: modules_demo
synthetic: true
owns: [M1, M2, M3, M4, M5]
owns_note: "demo-only; production shortlist does not use owns as routing key"
knows: ["[[M1_data_analytics]]", "[[M2_planning]]", "[[M3_engineering]]", "[[M4_outreach]]", "[[M5_feedback]]"]
version: 1
---

# Lead · coord (synthetic)

Demo coordinator: accept a task sheet → read domain cards → pick workers → record handoffs.
**Synthetic only** — not a production persona. Expand or delete locally as needed.
