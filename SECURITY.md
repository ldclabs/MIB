# Security Policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub, not in a public issue, pull request,
or discussion.

1. Go to <https://github.com/ldclabs/MIB/security/advisories/new> (the **Security**
   tab of the `ldclabs/MIB` repository, then **Report a vulnerability**).
2. Describe the issue, the affected version or commit, the platform you observed it
   on, and the impact you believe it has.
3. Include a minimal reproduction where possible. If a proof of concept executes
   code, say so plainly and keep it inert.

You will get an acknowledgement of the report and, once the issue is understood, an
assessment and a fix timeline. Please do not disclose the issue publicly until a fix
is available or you have been told the report is out of scope.

There is no separate security mailing address for this project; the GitHub private
advisory flow is the reporting channel.

## Scope

In scope:

- The reference Runner, evaluators, and CLI in `src/mib_runner/`.
- The submission sandbox (`src/mib_runner/sandbox.py`) — in particular any escape
  from the mount or network namespace, any way for a submission to read the private
  evaluation store, and any way for a submission to influence its own score.
- The evaluation service: job manifest and result attestation signing, the redaction
  boundary between internal and public reports, and the local HTTP API.
- Any leakage of evaluator-only content — hidden Template bodies, Oracle data, secret
  instance seeds, or evaluator keys — through a published artifact.

Out of scope:

- Benchmark results you disagree with, or Scenario difficulty.
- The local HTTP API's lack of authentication and multi-tenant controls. It is a
  localhost development service and is documented as such; deploying it on a public
  interface is a deployment error, not a vulnerability.
- Vulnerabilities in a participant's own agent.

## Running untrusted submissions

The evaluation service exists to execute code written by other people. Treat every
submission as hostile.

**Run the evaluation service only on an isolated Linux host dedicated to that
purpose.** The reference submission sandbox contains a stdio submission with Linux
unprivileged user, mount, and network namespaces via `unshare`, plus resource limits,
a scrubbed environment, an ephemeral working directory, and `tmpfs` masking of
evaluator paths. That machinery exists only on Linux: on macOS and Windows no
namespace is created, address-space limits are not enforced, and evaluator paths
cannot be masked. Do not evaluate stdio submissions there.

The local sandbox is the **reference enforcement layer**, not a claim that a Python
process launcher replaces production isolation. For public or adversarial
submissions:

- Give the evaluation host no credentials, no cloud instance-metadata access, and no
  network route to anything you care about.
- Keep the private evaluation store, evaluator keys, and the service root secret off
  that host wherever the architecture allows, and never in a directory a submission
  can reach.
- Prefer a hardened container or microVM runtime around the whole worker. The
  `oci_command` and `microvm_command` backend IDs are routing contracts reserved for
  exactly this; neither is validated in the current reference environment.
- Treat a `submission_sandbox` warning in a report as a failed run, not a note. A
  report that records `network_isolated: false` or a non-empty `warnings` list
  describes a submission that was not contained.
- Never run a submission under a policy of `network: "inherit"`. The sandbox emits a
  warning for it because it grants full host network and filesystem visibility.

`http` submissions are not sandboxed by the Runner at all. The participant's endpoint
is a remote process; isolating the traffic to and from it is the operator's
responsibility.

## Secrets

The service root secret (`MIB_SERVICE_ROOT_SECRET`) and the evaluator key
(`MIB_EVAL_KEY`) derive hidden-instance generation, public redaction, job signing,
and result signing. Provide them through the environment or a secret manager, never
on a command line and never in a committed file. The reference service does not
persist them.

No service database, artifact tree, or secret is committed to this repository;
`service/state/` and `service/artifacts/` are gitignored runtime directories.
