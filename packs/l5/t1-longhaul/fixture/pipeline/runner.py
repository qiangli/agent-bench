"""Chain the pipeline stages over input lines."""
from . import parse, clean, validate, dedupe, enrich, filter, sort, rank, label, render


def run_pipeline(lines):
    records = parse.run(lines)
    for mod in (clean, validate, dedupe, enrich, filter, sort, rank, label):
        records = mod.run(records)
    return render.run(records)
