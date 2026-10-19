# Durable Write Reconciliation Convention

Core brain skills define what counts as a durable brain write, but they do not choose how a specific runtime reconciles that write.

## Core Contract

A normal durable brain write must:

1. Search/read existing context first.
2. Edit the markdown source of truth, not only the derived database.
3. Preserve citations, frontmatter, links, and timeline structure.
4. Stage exact paths only.
5. Commit and push when the runtime has a writable checkout.
6. Run the runtime's installed durable-write reconciliation path.
7. Verify the result through the runtime's approved read surface.

## Runtime Reconciliation

The bound runtime owns reconciliation.
The brain host is the sole GBrain database writer, and this is how it turns pushed commits into the index:

{{host_write_mechanism}}

Every other client:

- Thin remote clients do not run host sync/embed locally. They commit/push markdown through a real checkout for the host to reconcile; their `gbrain` CLI scope is read-only.
- Split-engine clients keep local engine work separate from durable brain writes.
- Read-only clients stop before mutation.

If no runtime reconciliation path is installed or documented, stop before mutating durable brain files and ask for the runtime contract.
