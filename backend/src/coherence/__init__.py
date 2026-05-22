"""Coherence Engine — keeps the user's universe consistent over time.

Every agent write goes through here: find-existing → match-or-create → merge
by declarative rules → record the delta in `universe_change_log` → auto-link
evidence to the source entity that triggered the write. This is the layer
that distinguishes "captura" from "mantenimiento".
"""
