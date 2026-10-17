## Operating projects

Product work on a project runs through pstack, started from this brain with `/operate <issue>`.

- A **run request** is one issue on this tracker labelled `run`, in the shape of the "Run request" issue template: the repo as `<owner>/<repo>`, the goal, a done check that passes or fails, the proof, what is known, constraints. It names no host; the run starts on whichever host `/operate` runs on.
- `/operate <issue>` starts the run as its own herdr session in the project checkout and ends its turn. The run merges what its verifier passes, posts its note on the request and assigns the requester when it is done or when it needs an answer. Open issues labelled `run` and assigned to you are the notes and questions waiting for you.
- A wayfinder map whose route reaches work on a project ends in run requests, one per run, linked from the map; the map stays the record of what to do, the request the record of one run.
- `/operate cost <session id>` prices a finished run from its transcript on this host.
