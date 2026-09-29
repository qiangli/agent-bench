# Conventions for changes to `notes`

1. **Storage format.** Notes live in one JSON file whose top level carries
   `"format": <int>`. Any change to what is stored bumps `FORMAT_VERSION` in
   `notes/store.py` and adds a migration from the previous format in
   `notes/migrate.py`, with a test that loads a file written in the previous
   format. Users upgrade in place; their existing files must keep loading.
2. **Export is a public interface.** `notes export` output is read by other
   people's scripts. Existing fields keep their names and meaning; new data
   is only ever added as new fields. A change to export needs a test proving
   an old consumer still works.
3. **Every command is documented.** A new command or option gets its usage
   line in `README.md` and in the `--help` output, with a test for the help
   text.
