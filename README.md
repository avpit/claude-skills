# claude-skills

Reusable Claude Code skills and prompt templates.

## Layout

```
skills/
  git-workflow/
    SKILL.md          Git branching strategies, commit conventions, merge vs
                       rebase, conflict resolution, release/tag practices.

templates/
  git-migrations/
    ado-branch-policy-migration-v2.md   Kept for history.
    ado-branch-policy-migration-v3.md   Current — use this for new repos.
```

## templates/git-migrations

Agent prompts for migrating an Azure DevOps Terraform repo to a standardized
trunk-based branching model: branch naming, branch policies, PR template,
monthly dependency-patch automation, and release tagging.

**v3** (current) uses an asymmetric environment deployment model:

- Non-prod tiers (dev/qa/uat) deploy from **any branch**, so a patch/feature
  branch can be validated (including a real `terraform apply`) before it
  merges to `main`.
- Prod-tier environments (SIT/PROD) deploy **only from a tagged commit on
  `main`** — tags are cut at merge time, are immutable, and SIT/PROD promote
  the same tag without rebuilding.
- `env/*` branches are retired in favor of pipeline-parameterized deploys,
  rather than kept as a forward-only merge chain.

Before applying it to a repo, fill in the template's "Required inputs"
section per repo — org/project/repo, auth scope, current branch state, which
environment tiers are actually prod-tier, and current pipeline architecture
(YAML-parameterized vs. classic release with branch filters). Don't reuse
values from a prior run.

v2 is kept for history; see its diff against v3 for what changed and why.
