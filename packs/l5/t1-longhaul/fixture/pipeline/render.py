"""Render records to output lines."""


def run(records):
    return [f"{r['id']}|{r['label']}|{r['total']}|{r['rank']}" for r in records]
