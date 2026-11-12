# GitHub Wiki source and publishing

The source-controlled pages live in this directory. The repository is the canonical editing location; the GitHub Wiki is a published reading surface.

## First-time Wiki activation

GitHub creates the special Wiki repository only after its first page has been saved.

1. Open [Void Desk Wiki](https://github.com/SilverCrow2323/Void-Desk-Project/wiki).
2. Create a page titled **Home**.
3. Paste the content of [Home.md](Home.md) and save it.
4. On a machine with Git credentials and this repository cloned, run:

~~~bash
sh tools/publish_wiki.sh
~~~

The publisher clones the Wiki repo, copies all reviewed Markdown pages and the four SVG diagrams to its local assets folder, commits and pushes. It does not rewrite the main repository.

## Editing rules

- Edit files here, not only in the live Wiki.
- Keep Wiki page links extension-free.
- Keep diagrams under <code>docs/assets/</code>; the publisher copies them into Wiki <code>assets/</code>.
- Use PNG for screenshots and logos; use editable SVG for diagrams.
- Mark v12/preview content clearly as roadmap.
- Redact network and device identifiers from captures.
