## Brain workflow

1. When {{owner}} provides durable signal, run the brain's `signal-detector` skill in parallel where practical, or capture inline. Skip acknowledgments, duplicate material and unsafe private material.
2. Before answering durable questions, search with `gbrain search` and read the relevant page with `gbrain get`. Use `timeline` for chronology and `query` for broader synthesis.
3. Before writing, read `{{published_copy}}/skills/RESOLVER.md` and its routed skill. Before creating or moving pages, read root `RESOLVER.md`; follow `schema.md` and the directory resolver.
4. Update existing pages first, cite sources, keep current truth above the timeline and dated evidence below it, and preserve meaningful graph links.
5. In `#brain-review`, a reply from {{owner}} that answers a numbered digest item, such as `1: yes` or `2: option 3`, settles that needs-attention item: record it with `python3 {{published_copy}}/ops/brain-infra/skills/brain-digest/scripts/digest.py answer --item <n> --reply "<the reply>" --who {{owner}}`, then say in the channel which issue it settled. In a chat, record an answer with `--issue <number> --where "a chat"`. Answer follow-up questions on the digest from `digest.py items` and the issues; record only answers {{owner}} gives.
6. Write, commit and push as below, then verify targeted retrieval when the next step depends on indexed content.

{{agent_write_flow}}

{{local}}
