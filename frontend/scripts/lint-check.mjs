import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const sourceRoots = ["src", "e2e"];
const forbiddenPatterns = [
  { label: "merge conflict marker", pattern: /<<<<<<<|=======|>>>>>>>/ },
  { label: "debugger statement", pattern: /\bdebugger\b/ },
  { label: "mojibake shortcut glyph", pattern: /âŒ˜|â|Œ/ },
];

function walk(directory) {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    const stats = statSync(path);
    if (stats.isDirectory()) {
      return walk(path);
    }
    return path;
  });
}

const files = sourceRoots
  .flatMap((root) => {
    try {
      return walk(root);
    } catch {
      return [];
    }
  })
  .filter((path) => /\.(js|jsx|css|html)$/.test(path));

const failures = [];
for (const file of files) {
  const text = readFileSync(file, "utf8");
  for (const rule of forbiddenPatterns) {
    if (rule.pattern.test(text)) {
      failures.push(`${file}: contains ${rule.label}`);
    }
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Lint guard passed for ${files.length} frontend files.`);
