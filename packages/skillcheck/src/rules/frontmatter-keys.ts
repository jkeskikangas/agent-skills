import type { SkillContext, LintDiagnostic } from "../types.js";
import { join } from "node:path";

const AGENT_SKILLS_FRONTMATTER_KEYS = [
  "name",
  "description",
  "license",
  "compatibility",
  "metadata",
  "allowed-tools",
] as const;

// Claude Code follows Agent Skills and documents these additional fields.
// Keep this list separate so callers are not told the extensions are portable.
const CLAUDE_CODE_EXTENSION_KEYS = [
  "when_to_use",
  "argument-hint",
  "arguments",
  "disable-model-invocation",
  "user-invocable",
  "disallowed-tools",
  "model",
  "effort",
  "context",
  "agent",
  "hooks",
  "paths",
  "shell",
] as const;

const RECOGNIZED_FRONTMATTER_KEYS = new Set<string>([
  ...AGENT_SKILLS_FRONTMATTER_KEYS,
  ...CLAUDE_CODE_EXTENSION_KEYS,
]);

export function frontmatterKeys(ctx: SkillContext): LintDiagnostic[] {
  if (!ctx.frontmatter) return [];

  const unexpected = [...ctx.frontmatter.keys]
    .filter((k) => !RECOGNIZED_FRONTMATTER_KEYS.has(k))
    .sort();

  if (unexpected.length === 0) return [];

  const portable = [...AGENT_SKILLS_FRONTMATTER_KEYS].sort().join(", ");
  const claude = [...CLAUDE_CODE_EXTENSION_KEYS].sort().join(", ");
  return [
    {
      rule: "frontmatter-keys",
      message: `Unexpected frontmatter key(s): ${unexpected.join(", ")}. Agent Skills keys: ${portable}. Recognized Claude Code extensions: ${claude}`,
      file: join(ctx.dir, "SKILL.md"),
    },
  ];
}
