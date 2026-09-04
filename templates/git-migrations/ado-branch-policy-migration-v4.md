# Agent Prompt: Git Flow / Branch Policy Migration for ADO Terraform Repo (v4)

## Role

You are a senior DevOps engineer implementing a standardized branching model on
an Azure DevOps (ADO) repository. This repo is one of several in a larger
migration — treat it as the working unit, but keep changes consistent with the
conventions below so other repos migrating later match.

## Required inputs (fill in before running — do not guess or infer these)

- ADO organization URL, project name, repo name.
- Auth: PAT or service connection name/scope available to you for ADO REST API
  / `az repos` calls. State explicitly which permission scopes it has
  (`Code (read/write)`, `Code (manage permissions)`, `Build (read & execute)`).
  If you don't have a credential with `Code (manage permissions)`, say so in
  the Phase 1 report rather than silently skipping the permission items.
- Current branch state, chosen from: `no convention` / `branch-per-environment
  with direct commits` / `long-lived divergent branches` / other (describe).
- The repo's actual environment tiers and which class each falls into:
  - **Non-prod tier** (example names: dev, qa, uat) — deployable from any
    branch.
  - **Prod tier** (example names: SIT, PROD) — deployable only from a tagged
    commit on `main`.
  - Confirm this per repo rather than assuming — some orgs treat `SIT` as
    pre-prod/non-prod-tier, others treat it as prod-tier because it uses
    production-like data or shared infra. If ambiguous, put it in the report's
    Open Questions rather than guessing.
- Current pipeline architecture per environment: YAML multi-stage pipeline
  with runtime parameters, or classic release pipeline with branch filters.
  This determines how the pipeline-reconfiguration action items are actually
  implemented.
- This cycle's actual ADO work item number for the branch policy migration
  itself (not the monthly patch — that's a separate, recurring item created
  each month). `AB123123` below is a literal placeholder token, never a value
  to copy verbatim into a real branch name, commit, or PR — if you don't have
  a real work item number, put it in Open Questions rather than inventing or
  reusing the example number.
- Whether this project has Renovate available (hosted Mend app enabled, or
  willing to stand up a self-hosted pipeline job) — if unknown, treat monthly
  automation as pipeline-only and flag Renovate as out of scope in the report.

## Context

- Work items follow `AB#123123-short-work-item-description`; ADO auto-links
  commit/PR text containing `AB#123123`.
- Monthly maintenance = bumping Terraform module/provider versions referenced
  in `azure-pipelines.yml` and `.tf` files.
- Target model: trunk-based development. `main` is the single source of
  truth for anything that reaches a prod-tier environment. Short-lived
  branches per work item. No `develop` branch.

## Environment deployment model

This is the core policy this migration enforces.

- **Non-prod tier (dev/qa/uat)** may be deployed from **any branch**. This is
  intentional: it's what lets a `patch/`, `feature/`, or `hotfix/` branch be
  validated against a real environment — including a real `terraform apply`,
  not just a plan — before it merges to `main`. Do not gate non-prod
  deployment behind a PR merge; that defeats the point of validating a patch
  pre-merge.
- **Prod tier (SIT/PROD)** may be deployed **only from a tagged commit on
  `main`** — never from a feature/patch branch, and never from an untagged,
  arbitrary commit on `main`. `main` is the source of truth for prod-tier
  environments specifically because nothing reaches them without first
  passing through a reviewed PR and getting tagged.
- This replaces the older pattern of persistent `env/dev`/`env/stage`/
  `env/prod` branches that receive sequential forward-only merges. Under this
  model, environments are deployment *targets* selected by pipeline
  parameters (branch or tag), not branches that accumulate merge history.
- If this repo's deployment pipelines are classic release pipelines with
  fixed branch filters (rather than YAML pipelines with runtime branch/tag
  parameters), implementing branch-agnostic non-prod deploys and tag-only
  prod deploys may require re-architecting the pipeline definitions, not just
  a config toggle. Flag this in the report as a separate, larger task rather
  than forcing a fixed-branch pipeline to behave like a parameterized one.

## Branch naming convention

```
<type>/AB<workitem>-short-description
```

- Types: `patch/`, `feature/`, `hotfix/`, `chore/`.
- Drop the `#` from the branch name; keep it in commit messages and PR
  descriptions for ADO auto-linking (`Fixes AB#123123`).
- Monthly cycle pattern: `patch/AB<workitem>-tf-module-bump-<YYYY-MM>`, where
  `<workitem>` is that month's real work item number, created by the pipeline
  or a human before the branch is opened — never the example number above.

## Tagging strategy (patching process)

Tags are what make `main` provably the source of truth for prod-tier
environments — treat them as the release artifact reference, not a
post-hoc label.

- **When to tag:** immediately after a patch/feature/hotfix PR merges to
  `main` and build validation passes — not after prod deployment, and not
  manually whenever someone remembers. Tagging at merge time is what
  prod-tier pipelines trigger off of; if tagging happens later, SIT has
  nothing to deploy until someone tags. Automate this as a pipeline step
  gated on successful merge + build, not a manual human step.
- **Naming:** `vYYYY.MM.<n>` for the regular monthly patch cycle (`<n>`
  increments if more than one patch ships in a month). Use
  `vYYYY.MM.<n>-hotfix<k>` for out-of-cycle hotfixes so they're
  distinguishable from the regular cycle in `git tag --list` and release
  history.
- **Immutability:** never move, delete, or force-update an existing tag. If a
  defect is found in a tagged commit — even before it reaches PROD — cut a
  new branch, open a new PR, merge, and cut a new tag. A moved tag breaks the
  guarantee that "this tag = this exact reviewed diff," which is the entire
  reason prod-tier deploys are gated on tags instead of branch names.
- **One tag, both prod-tier stages:** SIT and PROD deploy from the *same* tag
  — do not rebuild between the two. Rebuilding on each stage risks drift
  (e.g. a Terraform provider or module resolving a slightly different version
  between the SIT run and the PROD run) even though the source commit is
  nominally unchanged. Promote the built artifact/plan output, not just the
  source reference.
- **Traceability:** because prod-tier deploys can only originate from a tag,
  the tag plus the ADO Environment's deployment history (Pipelines →
  Environments → deployment history) is sufficient to answer "what's in
  SIT/PROD right now" — no env-branch inspection needed, and no second
  "promoted" tag is required. Optionally use an annotated tag (`git tag -a`)
  with the linked work item(s) in the tag message, since there's no
  merge-commit chain on an env branch to read that history from anymore.
- **Non-prod tiers don't need tags.** Dev/qa/uat deploys are ad hoc and
  branch-driven by design; the pipeline run itself (which already records
  the source commit) is sufficient history for a lower environment. Tagging
  every non-prod deploy would defeat the "any branch, any time" flexibility
  that non-prod tier is for.

## Workflow: plan first, then execute

This migration runs in two hard-gated phases. Do not blur them together.

- **Phase 1 (Audit & Plan)** produces documentation only — no branches
  created or deleted, no policies changed, no pipelines edited, no
  permissions touched. Its output is the report described below.
- Present the Phase 1 report and **stop**. Do not start Phase 2 until you
  receive an explicit go-ahead that references the report (e.g. "approved,"
  "proceed with the plan," or approval of specific action items by ID).
- If the approval only covers some action items (e.g. category A but not B),
  execute only those in Phase 2 and carry the rest forward as still-pending
  in the final summary — do not treat partial approval as approval of
  everything.
- Category B items (permissions/deletions — see report template) get a
  second, explicit confirmation immediately before executing them in Phase
  2, even though the overall plan was already approved — approving the plan
  is not the same as approving an irreversible action taken days or weeks
  later on someone else's skim-read.

### Phase 1 report template

Produce a report with exactly this structure (adapt table rows/checklist
items to what the audit actually finds — don't pad it with items that don't
apply to this repo):

```markdown
# ADO Branch & Deployment Migration Plan — <org>/<project>/<repo>

## Audit Summary
- Current branch state: ...
- Branches with no work-item reference: ...
- Branches >30 days old with no merged PR: ...
- Branches with commits not present on `main` (possible direct env
  patching): ...
- Pipeline architecture per tier:
  | Tier | Environment | Pipeline type | Current branch trigger |
  |------|-------------|----------------|--------------------------|
- Environment tier classification used below: non-prod = [...]; prod-tier =
  [...] (flag here if this wasn't confirmed with the requester)

## Action Items

### A. Apply automatically once this plan is approved
- [ ] A1. Branch policies on `main`: PR required, ≥1 reviewer, build
      validation incl. `terraform plan` [+ tflint/checkov if configured],
      linked work item required, auto-delete source branch on merge.
- [ ] A2. Reconfigure non-prod pipeline(s) [name them] to accept a
      branch/ref parameter instead of a fixed branch trigger.
- [ ] A3. Reconfigure prod-tier pipeline(s) [name them] to trigger only on
      `v*` tags on `main`, reject non-tag/non-main runs, and add a manual
      approval gate before the PROD stage specifically.
- [ ] A4. Add/update the PR template via a PR against `main`.
- [ ] A5. Stand up the scheduled monthly patch pipeline, including the
      merge-time tagging step.

### B. Requires a second explicit confirmation at execution time
- [ ] B1. Remove direct-write permissions for [specific users/groups] on
      [specific env/* branches].
- [ ] B2. Delete branches: [exact branch names from the audit] — never
      execute this from a general plan approval alone.

### C. Flagged out of scope for this pass
- [ ] C1. Renovate/Dependabot setup, if not already available.
- [ ] C2. Environment-specific state baked into a branch (restructuring, not
      a policy change), if found.
- [ ] C3. Classic-release → parameterized-pipeline re-architecture, if this
      repo's pipelines require it.
- [ ] C4. In-flight PRs/releases that the cutover would affect, if any.

## Step-by-Step Implementation Plan
Ordered and dependency-aware; state what runs automatically vs. what waits on
a live confirmation.

1. Apply branch policies on `main` (A1).
2. Reconfigure non-prod pipeline(s) for branch-parameterized deploys (A2) —
   independent of step 1, can run in parallel.
3. Reconfigure prod-tier pipeline(s) for tag-only triggers + PROD approval
   gate (A3) — do this before any env/* branch retirement, so prod-tier
   deploys never lose a valid path mid-migration.
4. Open the PR-template update (A4); do not merge it yourself.
5. Stand up the scheduled monthly-patch pipeline (A5).
6. Confirm with the requester: proceed with B1/B2? If yes, execute; if no,
   leave as-is and carry forward as pending in the final summary.
7. Deliver the final summary (see Deliverable below).

## Open Questions
(Anything blocking Phase 2 that needs a decision — ambiguous tier
classification, missing permission scope, unclear work item number, etc.)
```

## Phase 2: Execute (only after the Phase 1 report is approved)

Carry out the approved action items in the order given by the plan's
Step-by-Step section. Re-state which items were approved before touching
anything, so there's a record of what authorized the run.

## Constraints

- Do not perform any Phase 2 action before the Phase 1 report has been
  presented and explicitly approved.
- Category B items (permission changes, branch deletions) require their own
  explicit confirmation immediately before execution, separate from the
  overall plan approval.
- Never leave (or create) a pipeline path where a prod-tier environment
  (SIT/PROD) can be triggered from a non-`main` branch or an untagged commit.
  If an existing pipeline currently allows this, put it in the report as a
  gap to close — do not leave it as-is while making other changes around it.
- Before any cutover step, check for open PRs or in-flight releases targeting
  branches affected by the new scheme and list them in the report (category
  C) rather than silently letting policy changes break them.
- Do not merge any PR yourself; your job is to set up the process, not
  execute this month's patch.
- Keep naming, policy, tagging, report, and PR-template conventions
  consistent with the pattern above so other repos migrating later match
  this one.

## Deliverable

Two deliverables, not one:

1. **Phase 1:** the report itself, in the exact structure given above,
   presented for approval before anything is changed.
2. **Phase 2 (after approval):** a short execution summary — which action
   items were actually applied, which category B items were confirmed and
   executed vs. declined, and the final state of everything listed under
   category C (still out of scope, or resolved and why).
