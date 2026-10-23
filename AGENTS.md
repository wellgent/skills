# Wellgent skills

Skills, templates and the web-products standard for running product work through pstack from a brain.
Every skill runs from this checkout in either harness (`.claude/skills/` and `.agents/skills/` link to them), and `operate` also installs into a brain with `npx skills`.

- A brain that should plan, operate projects and carry the shared core in `templates/brain/`: run `setup-brain <brain checkout>`.
- A project that should run on pstack: run `setup-project <owner>/<repo>`.
- Work to run on a project: a run request on the brain's tracker, then `/operate <issue>` from the brain.
- A new web product: `setup-web-product`, which drives the two above and `setup-web-stack`.
- The docs every project carries: `standards/project-docs.md`; `setup-project` converges a project on it.
- Stack rules for web products: `standards/web-products.md`; the `setup-web-stack` catalog installs them.

Everything here is company-neutral and works unmodified from a stranger's checkout: no person, project, company or host is named.
