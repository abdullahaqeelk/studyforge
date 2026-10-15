# Prompt versioning (SF-6)

Prompts live in `prompts/` as UTF-8 Markdown files. Use one file for each named
prompt version, for example `question_generation_v1.md`. The header records
Version, Author, Date (YYYY-MM-DD), and Change note. Record assistance in the
author field when applicable; Git history records who submitted each change.

Agents call `prompt_loader.load_prompt(filename)` at runtime. Paths are resolved
relative to the module, so launching from another directory does not break
loading. Missing, unreadable, or empty prompts raise `PromptError`, a subclass
of the shared `StudyForgeError`. There is no inline fallback that could silently
use an untracked prompt.

For a wording correction, update the version and change note in the same file
and commit with the Jira key. For an intentional behaviour change, add `_v2.md`,
retain `_v1.md`, update the agent's filename, and rerun output-validation and
prompt checks. Review the prompt diff alongside code before merging.

The initial question prompt treats uploaded material as untrusted data and
requires a cited page for every question. A valid page number establishes a
reference, but does not prove that a question is supported by the text. Manual
source review is still required. Record the prompt version, model, input,
output, and review findings for live prompt tests; never commit API keys or
private lecture material.
