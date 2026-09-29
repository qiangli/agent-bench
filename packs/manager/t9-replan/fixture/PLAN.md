# Sprint 31 plan (as of day 3 morning)

| story | points | priority | band | depends on | assigned | status      | title                          |
|-------|--------|----------|------|------------|----------|-------------|--------------------------------|
| S1    | 3      | P1       | L3   |            | vega     | done        | audit log schema               |
| S2    | 2      | P1       | L3   |            | lyra     | done        | audit write path               |
| S3    | 2      | P2       | L3   |            | juno     | done        | audit retention setting        |
| S4    | 5      | P1       | L3   | S2         | nova     | in progress | audit log API with paging      |
| S5    | 3      | P1       | L3   | S2         | nova     | todo        | audit export to CSV            |
| S6    | 2      | P2       | L3   |            | vega     | todo        | audit filters by user          |
| S7    | 3      | P2       | L3   | S5         | rhea     | todo        | scheduled audit export         |
| S8    | 2      | P3       | L3   |            | vega     | todo        | audit UI column chooser        |
| S9    | 1      | P3       | L3   | S8         | lyra     | todo        | remember chosen columns        |
| S10   | 5      | P2       | L4   | S4, S5     | orion    | todo        | integrate and review the epic  |
