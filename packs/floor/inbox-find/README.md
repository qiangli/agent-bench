# floor/inbox-find

The agent is told only: *Check your inbox for the message from iris and reply to it.*
No tool, command, token or store is named (`fixture/TASK.md` is that one sentence).

## How a run works

1. The runner creates `WORKSPACE.bashy-home`, a sibling of the workspace, and runs `setup.py`
   against it with the real `bashy`. Five variables point every store there (`BASHY_HOME`,
   `BASHY_MB_DIR`, `BASHY_MEET_DIR`, `BASHY_MAILBOX_DIR`, `BASHY_ROOM_DIR`); `BASHY_HOME` alone
   does not move the message board. The agent is launched with the same variables, so the
   operator's real board is never touched.
2. `setup.py` sends directed mail to the agent under test (the `AGENT` binding name, which must
   resolve on the host): four unrelated messages from marlow, tobias, sedge and fennel, and one from
   iris asking for a reply with `ORCHID-<8 hex>`. The word is random per run and written only
   to the sibling store, never to the workspace.
3. The grader (`grader/grade.py`) never opens the workspace. Through bashy, in the isolated store:
   `mb --history --peek --json` finds a post from the agent to iris carrying the word, and
   `inbox --peek --json` (non-consuming) shows which unrelated messages are still unread.

## Score

| points | meaning |
|---|---|
| 2 | correct reply exists and all four unrelated messages are still unread |
| 1 | correct reply exists but one or more unrelated messages were consumed (e.g. a bare `bashy inbox` drain) |
| 0 | no correct reply |

"Found via another tool" is deliberately not scored. It cannot be proven from trusted
evidence: the only trusted facts are the store's contents and cursors. An agent that reads
`posts.jsonl` directly still has to send a correct reply and leave the cursors alone.

## Limits and checks

- The agent can read the sibling store (it is the inbox). It cannot score by writing to its workspace.
- Use a fresh `AGENT` name per K attempt only if the matrix requires fresh identities; the setup reseeds each run.
- `python3 packs/floor/inbox-find/selfcheck.py [AGENT]` (needs the real bashy, no model) asserts: no reply 0;
  fake reply file/log in the workspace 0; wrong word 0; reply after an ack-all read 1; reference 2;
  the operator's real board unchanged.
- `reference/solve.py` is an action against the store, not an overlay; `validate` runs it
  for tasks with `setup.py`. The zero-quota `dry` agent (benchbot) only copies reference files and
  cannot solve this task.
- Not run: any model. The K=3 matrix, and whether `bashy chat -i` forwards the isolation variables to each
  binding's session, is for the conductor to confirm.
