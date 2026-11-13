# Void Desk — desktop Pygame input map

This is the desktop keyboard fallback for the Pygame engine. It translates
ordinary pygame KEYDOWN events into the same logical actions that the
handheld engine receives from evinput.

| Logical control | Desktop key |
|---|---|
| D-pad up / down / left / right | Arrow keys |
| A | Enter or A |
| B / back | Escape or B |
| X | X |
| Y | Y |
| L1 | 1 |
| L2 | 2 |
| R2 | 3 |
| R1 | 4 |
| L3 | Q |
| R3 | E |
| Select | F8 |
| Start | F9 |
| Menu | M |

**Important:** Escape is a back action, not Menu. The Menu action is bound only
to M, so pressing Escape while selecting an item cannot accidentally invoke a
system/menu action. End Session remains available through the explicit NEXUS
flow.

The desktop bridge opens connected SDL joysticks at startup and handles device hot-plug.
For common XInput-style JOY events, button indices map as follows: 0/1/2/3 =
A/B/X/Y, 4/5 = L1/R1, 6/7 = Select/Start, 8/9 = L3/R3 and 10 = Menu.
SDL GameController events use their standardized button order. Hat events drive
the D-pad; trigger axes 4/5 drive L2/R2 with edge detection.

The desktop event bridge drains its action queue and always returns a list,
including when the queue contains input. The handheld evdev reader and its
muOS-specific physical button layouts are unchanged.
