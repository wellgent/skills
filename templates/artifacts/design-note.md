## Design note

**Hard-to-reverse edge:** <stored-data shape | migration | external contract | money | authorization | production delete>: <what this change touches there>

### Behavioural contracts at the edge

- <public operation>
  - Invariants: <...>
  - Examples: <input with literal values> -> <expected literal result>
    (one per combination of the stored rows the operation decides from; the value past every bound; browser-only behaviour as observable cases)

### Migration or production write

- none | <the write>: governed by <ADR or record line>; dry run, snapshot

### Second opinion

- <verdict; each sentence it changed, with the new wording>
