# notes

A tiny command-line notes tool.

    notes add TITLE [BODY]     add a note, prints its id
    notes list                 list notes (id and title)
    notes show ID              print one note
    notes export [--out FILE]  export all notes as JSON lines

Notes are stored in `~/.notes.json` (override with `NOTES_FILE`).
