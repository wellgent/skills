# <Project name>

<What the product is and who uses it, in one or two lines.>

## Rules for every session

- **Check before report.** A session that changes files has `<check command>` green on its branch tip before it reports: run it yourself on that commit and quote its result. CI runs the same command on every pull request.
- **Production.** Sessions work on their own dev environment per [docs/agents/dev-loop.md](docs/agents/dev-loop.md). A production read or write, a deploy, a data deletion and a message to a user are stops: each goes to the request issue, or to the person in the chat, and waits for the answer.
- **Landing.** Work lands through a pull request squash-merged onto `main`, which stays linear. A run merges only under the landing authority its prompt grants.

## Must-read

Read each file when its trigger matches your work, before you write code.

- <trigger> → `<path>`

## Where things live

- [PRODUCT.md](PRODUCT.md): what the product does, for whom, and the product rules a change must keep.
- [DESIGN.md](DESIGN.md): the design system and the kit map.
- [docs/agents/dev-loop.md](docs/agents/dev-loop.md): the check command, CI, running the app, worktrees and the critical journeys.
- `.agents/playbooks/`: this project's playbooks extending pstack's bundled ones.

@~/.claude/pstack-models.md
