# QWASAR Desk — Controls and navigation

## Default controls

| Control | Action |
|---|---|
| D-pad | Move through menus and lists |
| A | Confirm / open |
| B | Back / close the current panel |
| X / Y | Context or secondary action where shown |
| L1 / R1 | Change tabs/categories where supported |
| START / SELECT | Panel-specific actions; follow the on-screen footer |

The active screen footer is the source of truth: some tools use additional shortcuts.

## Keyboard controls (LÖVE / PC testing)

The LÖVE input layer maps keyboard arrows to the D-pad, Return/Z to A, Backspace/X to B, Q/W to L1/R1, Tab to SELECT and Space to START. Escape opens the Back/Menu action.

F11 toggles fullscreen. F12 captures a screenshot to data/visual-captures/.

## Screenshot shortcut

Press **F12** while a frontend is visible. The screenshot is saved with a JSON sidecar under data/visual-captures/. Review images for private information before sharing them.
