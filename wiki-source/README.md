# GitHub Wiki source and publishing

The repository is the canonical editing location. The live GitHub Wiki is the practical reading surface for FAQs, short guides, manuals and troubleshooting.

## Page model

Use the reusable [Wiki page template](../docs/WIKI_PAGE_TEMPLATE.md) when creating a new guide; remove sections that do not fit the topic.
- Give every distinct topic its own page.
- Start with a short explanation of what the topic is and when it is useful.
- Use one concept per bullet; keep bullets short and scannable.
- Use **MUST KNOW!!** for required safety, compatibility or prerequisite information.
- Use **Optional** for enhancements and non-essential steps.
- Leave basic items unlabelled; readers can work through them gradually.
- Link to the next practical page at the end.
- Keep implementation internals in docs/; Wiki pages explain how to use the product.

## First-time Wiki activation
GitHub creates the special Wiki repository only after its first page has been saved.

1. Open [Void Desk Wiki](https://github.com/SilverCrow2323/Void-Desk-Project/wiki).
2. Create a page titled **Home**.
3. Paste the content of [Home.md](Home.md) and save it.
4. From a clone with Git credentials, run:

~~~bash
sh tools/publish_wiki.sh
~~~

The publisher copies reviewed Markdown pages and visual assets to the Wiki repository.

## Editing rules
- Edit files here, not only in the live Wiki.
- Keep Wiki page links extension-free.
- Use short, direct titles and short paragraphs.
- Use diagrams for processes, tables for comparisons and expandable sections for advanced detail.
- Keep button labels as actual icon assets wherever a matching icon exists; do not invent device-specific mappings.
- Keep diagrams under docs/assets/; the publisher copies them into Wiki assets/.
- Mark roadmap/preview content clearly.
- Redact network and device identifiers from captures.
