**Problem**
The root directory contains a `package.json` file that suggests the project is a Node.js application. However, the `name` is "hive" (the python framework) and the only script explains that it is *not* a Node app. This creates confusion for contributors and automated tools/IDEs that attempt to index it as a Node project.

**Evidence**
File: `package.json`
Lines 11-13:
```json
"scripts": {
  "setup": "echo '⚠️ This npm setup is for the archived web application...'"
}
```

**Impact**
**Developer Experience**. Increases cognitive load for new contributors. It looks like legacy artifact pollution.

**Proposed Solution**
1.  Delete `package.json` and `package-lock.json` if they serve no functional purpose for the current Python-based architecture.
2.  If strictly needed for formatting tools (prettier?), move them to a `scripts/` or `frontend/` subdirectory or clearly document *why* they exist in `CONTRIBUTING.md`.

**Priority**
Low
