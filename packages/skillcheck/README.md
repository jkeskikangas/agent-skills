# @jkeskikangas/skillcheck

Linter for **agent skill directories** (for example `skills/<skill-name>/SKILL.md` + `agents/openai.yaml` + `references/`).

Use it to catch broken links, missing frontmatter, and rubric drift **before** you ship skills to your team or publish them.

- Fast local feedback (`npx @jkeskikangas/skillcheck skills/`)
- CI-friendly exit codes + optional JSON output (`--format json`)
- Cross-platform (Node.js 18+, no native deps)

## Why lint skill directories?

In agentic workflows, “looks fine” is not a quality bar. Skills tend to fail at runtime because of small, structural issues that are cheap to catch early:

- A skill references a file that doesn’t exist (`references/`, `scripts/`, `agents/`).
- Frontmatter fields drift or become ambiguous, making activation/behavior inconsistent across agents.
- Rubrics evolve, but your checked-in rubric text no longer matches the rubric your reviewers assume (“rubric drift”).
- Tool configs get out of sync with safety constraints or token budgets, causing brittle behavior.

`skillcheck` exists to make these failures **reviewable and CI-gateable**, so you spend your time improving the skill—not debugging the scaffolding.

## How it fits (with `agnix`)

- `skillcheck`: repo-native structural validation + rubric consistency (fast, deterministic, offline).
- `agnix`: spec-level portability linting across agent environments.

For “ship it” confidence, run both in CI.

## Install

```bash
# Recommended (project devDependency)
npm install -D @jkeskikangas/skillcheck

# Or run without installing (great for CI / one-offs)
npx @jkeskikangas/skillcheck skills/

# Or install globally
npm install -g @jkeskikangas/skillcheck
```

## Quick start

Lint all skills under `skills/`:

```bash
skillcheck skills/
```

Lint a single skill directory:

```bash
skillcheck skills/<skill-name>
```

Help:

```bash
skillcheck --help
```

## Usage

```bash
skillcheck skills/                    # lint all skills
skillcheck skills/<skill-name>        # lint a single skill
skillcheck --fix skills/              # auto-fix rubric drift
skillcheck --format json skills/      # machine-readable output
skillcheck --skills-only skills/      # skip rubric checks
skillcheck --rubrics-only skills/     # skip skill checks
skillcheck --max-lines 500 skills/    # max allowed SKILL.md lines
```

## What it checks

- **Frontmatter** — required fields, valid types, schema conformance
- **Links** — referenced files exist (agents/, references/)
- **Rubrics** — validates markdown rubrics discovered in `references/*rubric*.md`
- **openai.yaml** — tool definitions, token budget, safety constraints

`skillcheck` recognizes the portable Agent Skills frontmatter fields and the documented Claude Code
extensions (`when_to_use`, `argument-hint`, `arguments`, invocation controls, tool restrictions,
model/context controls, skill-scoped hooks, path activation, and shell selection). Recognition means
the field is known to a supported client; it does not make a Claude extension portable. Continue to
run `agnix` for strict cross-agent portability checks.

## Example output

When diagnostics are found, `skillcheck` exits non-zero and prints a one-line summary to stdout, with details on stderr:

```
[FAIL] 4 diagnostics in 1 skill.
P1 frontmatter-invalid  skills/writing-skills/SKILL.md  Missing required field: name
P2 link-missing         skills/writing-skills/SKILL.md  references/portability.md not found
```

When everything is valid:

```
[OK] 4 skills and 2 rubrics valid.
```

## Options

- `--format stylish|json` (default: `stylish`)
- `--max-lines <n>`: max allowed `SKILL.md` lines (default: `500`)
- `--fix`: auto-fix rubric drift (only applies to rubric checks)
- `--skills-only`: skip rubric checks
- `--rubrics-only`: skip skill checks

## Exit codes

- `0` — no diagnostics found
- `1` — diagnostics found
- `2` — CLI usage / argument error

## JSON output

Use `--format json` for tooling and CI integrations:

```bash
skillcheck --format json skills/ > skillcheck.json
```

The JSON shape matches the schema in the source repo:

- `schemas/lint-output.schema.json`

Source: https://github.com/jkeskikangas/skills

## CI (GitHub Actions)

Typical consumer usage (no repo checkout needed):

```yaml
- name: Lint skills
  run: npx @jkeskikangas/skillcheck skills/
```

If you vendor `skillcheck` into a monorepo (this package’s own repo layout):

```yaml
- name: Install
  run: npm ci
  working-directory: packages/skillcheck

- name: Build
  run: npm run build
  working-directory: packages/skillcheck

- name: Lint skills (repo-local)
  run: node packages/skillcheck/bin/skillcheck.js skills/
```

## Development

```bash
cd packages/skillcheck && npm ci
cd packages/skillcheck && npm run build
cd packages/skillcheck && npm test
```

## Design principles

- **Deterministic and offline**: no network calls; same inputs → same diagnostics.
- **Actionable output**: human-friendly default format + JSON for tooling.
- **Composable rules**: checks are small and targeted (easy to extend without breaking consumers).
- **Safety-friendly**: designed for skill repos where secrets must never be read or emitted.

## Related tooling

`skillcheck` focuses on structural validation and rubric consistency. For spec-level portability linting across agents, pair it with `agnix` in CI.

## License

Apache-2.0
