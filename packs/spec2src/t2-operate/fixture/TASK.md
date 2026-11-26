This directory is the `form` app, already built from its spec. `dag.md` is its lifecycle. Carry out the steps below, in order. For each step, run the code block of that step in `dag.md` with `sh` from this directory, exactly as it is written. Do not change or delete any file that is here now, and do not replace a step with commands of your own. bashy is not available here; `conform` is on your PATH.

1. `build`.
2. `test`.
3. `install`, to the default place.
4. `serve`: start it and leave it running while you do steps 5 and 6.
5. `run`, with `ARGS='add --id drill-1 --def examples/contact.json --json'`. Save what it prints to `answer.json` in this directory.
6. Fetch the page at the `url` given in `answer.json` with `curl` and save it to `page.html` in this directory.
7. `stop`. After it, the service must no longer be running.

Then write `report.txt` in this directory: one line per step, the step name and its exit status.
