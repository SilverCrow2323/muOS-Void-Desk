![Void Desk documentation cover](assets/voiddesk-docs-banner.svg)

# 🎨 Documentation style guide

The manual should feel like a guided field interface, not an unformatted dump of engineering notes. It uses the QWASAR visual language while prioritising legibility, predictable navigation and useful information density.

## Page anatomy

Use short, direct titles such as **Install**, **First launch**, **Controls**, **Network** and **Troubleshooting**. Avoid slogans and abstract headings. Every page covers one topic and starts with a short explanation.

On handheld displays, body copy must be readable at normal viewing distance. Essential instructions must never be hidden in tiny metadata. Use short paragraphs, generous spacing and collapsible advanced details.

## Button and key icons

When a guide mentions a physical control, show its matching button glyph inline instead of repeating a text-only label. Use device-specific artwork where available. Never imply a universal mapping: the active screen footer and input profile remain authoritative. If an exact glyph is unavailable, use a semantic icon with accessible text rather than inventing a physical mapping.


1. A clear title and one-line purpose.
2. A visual overview when it improves understanding.
3. A short “what is current” or “important” callout.
4. Scannable sections with descriptive headings.
5. Tables for comparison, status and reference data.
6. Details blocks for advanced/optional topics.
7. Related links and a clear next step.

## Reusable GitHub Markdown patterns

### Information boxes

```markdown
> [!NOTE]
> Background context or a useful detail.

> [!TIP]
> A practical shortcut or recommendation.

> [!IMPORTANT]
> A required step or compatibility constraint.

> [!WARNING]
> A risk that the reader must understand before proceeding.

> [!CAUTION]
> A destructive or potentially irreversible action.
```

### Expandable detail

```markdown
<details>
<summary>Advanced options</summary>

Longer or less frequently needed details go here.

</details>
```

### Diagrams

Prefer editable SVG for architecture maps, navigation layouts and signal flows. Use Mermaid for sequence/decision diagrams when it stays readable in GitHub. Use PNG for actual product screenshots, logos or raster artwork.

### Images and accessibility

- Add meaningful alt text to every informative image.
- Use captions to explain what a screenshot proves—and what it does not prove.
- Keep diagrams high contrast and readable at handheld resolution.
- Do not use colour as the only way to communicate state.
- Check every screenshot for SSIDs, IP addresses, tokens, hostnames and personal filenames before publication.

## Status vocabulary

| Label | Meaning |
|---|---|
| ✅ Implemented | Code is present and the described path is verified at the stated level |
| 🧪 Experimental | Exists, but behaviour or compatibility is not release-certified |
| 🧩 Partial | Some paths are working; named gaps remain |
| 🗺️ Planned | Design or roadmap only; not shipped |
| ⚠️ Hardware pending | CI/desktop checks exist, but target-device validation remains |

## Review checklist

- [ ] The title describes the task or system clearly.
- [ ] Current implementation and roadmap are not mixed together.
- [ ] Tables are used for comparisons, not for long prose.
- [ ] Callouts are reserved for genuinely important information.
- [ ] Long advanced material is collapsible.
- [ ] Image paths resolve in both repository docs and the GitHub Wiki.
- [ ] Diagrams have source files and descriptive alt text.
- [ ] PNG screenshots have been reviewed for private data.
- [ ] Relative links and anchor links have been checked.
