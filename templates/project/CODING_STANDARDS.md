# Coding standards

The rules a diff is reviewed against: `code-review` reads this file inside Build, and Review and Audit read it again.
A breach of a rule written here is a blocking Review finding.
A rule a lint rule can enforce becomes that lint rule and leaves this file.

## Code

- **Residue leaves in the same diff.** A replacement deletes what it replaces: the old function, its tests, its docs, its exports, its dependency.
  Code and comments describe what is; the diff adds no commented-out code, no debug instrumentation and no comment about what the code used to do.
- **One implementation per rule.** Before writing a helper, hook or check, search for the existing one and use or extend it.
  A second implementation of an existing one is a breach, whatever its name.
- **Dead data gets a removal ticket.** A schema field nothing reads or an index no query uses is removed through its own ticket, filed when it is found.
- **Every `TODO` carries an issue number.**

<Project rules, one per bullet, each with the judgment a reviewer applies.>

## The test bar

1. Every public function is tested per outcome: allowed, refused, a refusal writes nothing, and each named boundary.
2. Pure domain logic is tested once, at its interface; an integration test adds one case, never the table again.
3. A test asserts the fields it is about; whole-object equality only where the shape is the contract.
4. One browser test per user action per surface; every control that triggers a write is exercised by a test.
5. One shared harness and fixture set; a new test file copies no setup.
6. A flaky test is fixed or deleted in the ticket that meets it; a test is never retried.
7. Tests mock at system boundaries, never the framework or the module under test.
