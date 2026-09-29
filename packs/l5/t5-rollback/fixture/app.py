"""Tiny notes app on top of store.py."""
import store


def add_note(text):
    db = store.load()
    note = {"id": len(db["notes"]) + 1, "text": text}
    db["notes"].append(note)
    store.save(db)
    return note["id"]


def list_notes():
    return [n["text"] for n in store.load()["notes"]]
