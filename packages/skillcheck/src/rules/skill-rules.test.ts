import { describe, it, expect } from "vitest";
import { resolve } from "node:path";
import type { SkillContext, MarkdownText } from "../types.js";
import { skillMdExists } from "./skill-md-exists.js";
import { frontmatterValid } from "./frontmatter-valid.js";
import { frontmatterKeys } from "./frontmatter-keys.js";
import { nameConstraints } from "./name-constraints.js";
import { nameMatchesDir } from "./name-matches-dir.js";
import { descriptionConstraints } from "./description-constraints.js";
import { lineCount } from "./line-count.js";
import { noPlaceholders } from "./no-placeholders.js";
import { linksResolve, extractLocalMarkdownLinks } from "./links-resolve.js";
import { noDeepChaining } from "./no-deep-chaining.js";

const FIXTURES = resolve(import.meta.dirname, "../../fixtures");

function makeCtx(overrides: Partial<SkillContext> = {}): SkillContext {
  return {
    dir: resolve(FIXTURES, "valid-skill"),
    text: "---\nname: valid-skill\ndescription: A valid test skill.\n---\n\n# Valid Skill\n" as MarkdownText,
    frontmatter: {
      keys: new Set(["name", "description"]),
      name: "valid-skill",
      description: "A valid test skill.",
    },
    maxLines: 500,
    openaiYaml: undefined,
    files: new Set<string>(),
    markdownFiles: new Map<string, MarkdownText>(),
    ...overrides,
  };
}

describe("skill-md-exists", () => {
  it("passes when text exists", () => {
    expect(skillMdExists(makeCtx())).toEqual([]);
  });

  it("fails when text is empty", () => {
    const d = skillMdExists(makeCtx({ text: "" as MarkdownText }));
    expect(d).toHaveLength(1);
    expect(d[0].rule).toBe("skill-md-exists");
  });
});

describe("frontmatter-valid", () => {
  it("passes when frontmatter is parsed", () => {
    expect(frontmatterValid(makeCtx())).toEqual([]);
  });

  it("fails when frontmatter is undefined", () => {
    const d = frontmatterValid(makeCtx({ frontmatter: undefined }));
    expect(d).toHaveLength(1);
    expect(d[0].rule).toBe("frontmatter-valid");
  });
});

describe("frontmatter-keys", () => {
  it("passes with allowed keys", () => {
    expect(frontmatterKeys(makeCtx())).toEqual([]);
  });

  it("passes with documented Claude Code extension keys", () => {
    const d = frontmatterKeys(
      makeCtx({
        frontmatter: {
          keys: new Set([
            "name",
            "description",
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
          ]),
          name: "test",
          description: "test",
        },
      })
    );
    expect(d).toEqual([]);
  });

  it("fails with unexpected keys", () => {
    const d = frontmatterKeys(
      makeCtx({
        frontmatter: {
          keys: new Set(["name", "description", "custom-key"]),
          name: "test",
          description: "test",
        },
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("custom-key");

    const [portable, claude] = d[0].message
      .split("Agent Skills keys: ")[1]
      .split(". Recognized Claude Code extensions: ");
    expect(portable).toContain("allowed-tools");
    expect(portable).not.toContain("argument-hint");
    expect(claude).toContain("argument-hint");
  });
});

describe("name-constraints", () => {
  it("passes with valid name", () => {
    expect(nameConstraints(makeCtx())).toEqual([]);
  });

  it("fails with uppercase name", () => {
    const d = nameConstraints(
      makeCtx({
        frontmatter: {
          keys: new Set(["name", "description"]),
          name: "BadName",
          description: "test",
        },
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("^[a-z0-9-]+$");
  });

  it("fails with name too long", () => {
    const d = nameConstraints(
      makeCtx({
        frontmatter: {
          keys: new Set(["name", "description"]),
          name: "a".repeat(65),
          description: "test",
        },
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("too long");
  });

  it("fails with leading dash", () => {
    const d = nameConstraints(
      makeCtx({
        frontmatter: {
          keys: new Set(["name", "description"]),
          name: "-bad",
          description: "test",
        },
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("cannot start/end");
  });
});

describe("name-matches-dir", () => {
  it("passes when name matches dir", () => {
    expect(nameMatchesDir(makeCtx())).toEqual([]);
  });

  it("fails when name does not match dir", () => {
    const d = nameMatchesDir(
      makeCtx({
        frontmatter: {
          keys: new Set(["name", "description"]),
          name: "wrong-name",
          description: "test",
        },
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("wrong-name");
  });
});

describe("description-constraints", () => {
  it("passes with valid description", () => {
    expect(descriptionConstraints(makeCtx())).toEqual([]);
  });

  it("fails with description containing angle brackets", () => {
    const d = descriptionConstraints(
      makeCtx({
        frontmatter: {
          keys: new Set(["name", "description"]),
          name: "valid-skill",
          description: "Contains <html> tag",
        },
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("'<' or '>'");
  });

  it("fails with description too long", () => {
    const d = descriptionConstraints(
      makeCtx({
        frontmatter: {
          keys: new Set(["name", "description"]),
          name: "valid-skill",
          description: "a".repeat(1025),
        },
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("too long");
  });
});

describe("line-count", () => {
  it("passes with few lines", () => {
    expect(lineCount(makeCtx())).toEqual([]);
  });

  it("fails when exceeding max lines", () => {
    const d = lineCount(
      makeCtx({
        text: "line\n".repeat(501) as MarkdownText,
        maxLines: 500,
      })
    );
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("too long");
  });
});

describe("no-placeholders", () => {
  it("passes with clean text", () => {
    expect(noPlaceholders(makeCtx())).toEqual([]);
  });

  it("fails with [TODO]", () => {
    const d = noPlaceholders(makeCtx({ text: "Some text [TODO: add this]." as MarkdownText }));
    expect(d).toHaveLength(1);
    expect(d[0].rule).toBe("no-placeholders");
  });

  it("fails with TODO:", () => {
    const d = noPlaceholders(makeCtx({ text: "Some text\nTODO: add this" as MarkdownText }));
    expect(d).toHaveLength(1);
  });

  it("fails with [TBD]", () => {
    const d = noPlaceholders(makeCtx({ text: "Some text [TBD]." as MarkdownText }));
    expect(d).toHaveLength(1);
  });
});

describe("extractLocalMarkdownLinks", () => {
  it("extracts relative links", () => {
    const links = extractLocalMarkdownLinks(
      "See [ref](references/foo.md) and [bar](bar.txt)." as MarkdownText
    );
    expect(links).toEqual(new Set(["references/foo.md", "bar.txt"]));
  });

  it("ignores external URLs", () => {
    const links = extractLocalMarkdownLinks(
      "See [google](https://google.com)." as MarkdownText
    );
    expect(links.size).toBe(0);
  });

  it("ignores absolute paths", () => {
    const links = extractLocalMarkdownLinks("See [root](/etc/passwd)." as MarkdownText);
    expect(links.size).toBe(0);
  });

  it("strips fragment identifiers", () => {
    const links = extractLocalMarkdownLinks("See [ref](foo.md#section)." as MarkdownText);
    expect(links).toEqual(new Set(["foo.md"]));
  });
});

describe("links-resolve (with fixtures)", () => {
  it("passes for valid-skill (no links)", () => {
    const ctx = makeCtx();
    expect(linksResolve(ctx)).toEqual([]);
  });

  it("detects broken links", () => {
    const ctx = makeCtx({
      text: "See [broken](nonexistent-file.md)." as MarkdownText,
      dir: resolve(FIXTURES, "valid-skill"),
    });
    const d = linksResolve(ctx);
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("Broken link");
  });

  it("detects links outside skill dir", () => {
    const ctx = makeCtx({
      text: "See [escape](../../../etc/passwd)." as MarkdownText,
      dir: resolve(FIXTURES, "valid-skill"),
    });
    const d = linksResolve(ctx);
    expect(d).toHaveLength(1);
    expect(d[0].message).toContain("links outside skill dir");
  });
});

describe("no-deep-chaining (with fixtures)", () => {
  it("passes for valid-skill (no links)", () => {
    const ctx = makeCtx();
    expect(noDeepChaining(ctx)).toEqual([]);
  });

  it("returns empty for empty text", () => {
    const ctx = makeCtx({ text: "" as MarkdownText });
    expect(noDeepChaining(ctx)).toEqual([]);
  });
});
