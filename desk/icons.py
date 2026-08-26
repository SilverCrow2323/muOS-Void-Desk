# -*- coding: utf-8 -*-
# VOIDDESK // icons — icone vettoriali disegnate con pygame.
# Nessun font di sistema contiene queste glifi: le disegniamo noi, cosi'
# restano nitide a 640x480 e seguono il colore del tema.

import math

import pygame


def _r(s, x, y, w, h, col, wd=0, rad=0):
    if rad:
        pygame.draw.rect(s, col, (x, y, w, h), wd, border_radius=rad)
    else:
        pygame.draw.rect(s, col, (x, y, w, h), wd)


def draw(surf, key, x, y, sz, col, t=0.0):
    """Disegna l'icona 'key' in un riquadro sz x sz con angolo in (x, y).
    t (tempo in secondi) e' usato solo dalle icone animate (outer_full)."""
    u = sz / 24.0        # unita': le icone sono progettate su griglia 24x24

    def p(px, py):
        return (int(x + px * u), int(y + py * u))

    def line(a, b, w=2):
        pygame.draw.line(surf, col, p(*a), p(*b), max(1, int(w * u)))

    def rect(rx, ry, rw, rh, w=2, rad=0):
        _r(surf, int(x + rx * u), int(y + ry * u), int(rw * u), int(rh * u),
           col, 0 if w == 0 else max(1, int(w * u)), int(rad * u))

    def circ(cx, cy, r, w=2):
        pygame.draw.circle(surf, col, p(cx, cy), max(2, int(r * u)),
                           0 if w == 0 else max(1, int(w * u)))

    def arc(cx, cy, r, a0, a1, w=2):
        rr = int(r * u)
        box = pygame.Rect(int(x + (cx - r) * u), int(y + (cy - r) * u),
                          rr * 2, rr * 2)
        pygame.draw.arc(surf, col, box, math.radians(a0), math.radians(a1),
                        max(1, int(w * u)))

    # ---- icone di sezione v6.0 ------------------------------------
    if key == "forge":                     # incudine: software
        rect(3, 8, 18, 4, 0)
        rect(9, 12, 6, 4, 0)
        rect(6, 16, 12, 3, 0)
        line((3, 8), (1, 11), 2)
        return
    if key == "toolbox":                   # cassetta attrezzi
        rect(3, 10, 18, 9, 2, 1)
        rect(9, 6, 6, 4, 2)
        line((3, 14), (21, 14))
        line((11, 13), (13, 13), 3)
        return
    if key == "uplink":                    # antenna
        line((12, 21), (12, 10), 2)
        line((6, 21), (12, 14), 2)
        line((18, 21), (12, 14), 2)
        circ(12, 8, 2, 0)
        arc(12, 8, 5, 20, 160)
        arc(12, 8, 8, 30, 150)
        return
    if key == "workshop":                  # chiave inglese
        circ(7, 7, 4, 2)
        rect(6, 6, 3, 3, 0)
        line((9, 10), (18, 19), 3)
        rect(16, 17, 5, 5, 0, 1)
        return
    if key == "book":                      # manuale aperto
        line((12, 5), (12, 20), 2)
        line((12, 5), (4, 7), 2)
        line((12, 5), (20, 7), 2)
        line((4, 7), (4, 19), 2)
        line((20, 7), (20, 19), 2)
        line((4, 19), (12, 20), 2)
        line((20, 19), (12, 20), 2)
        line((6, 10), (10, 11))
        line((14, 11), (18, 10))
        return
    if key == "power":                     # spegnimento
        circ(12, 13, 8, 2)
        rect(11, 3, 3, 9, 0)
        return
    if key == "storage":                   # partizioni impilate
        rect(4, 4, 16, 5, 2, 1)
        rect(4, 11, 16, 5, 2, 1)
        rect(4, 18, 16, 4, 2, 1)
        rect(6, 6, 2, 2, 0)
        rect(6, 13, 2, 2, 0)
        return
    if key == "clock":                     # orologio
        circ(12, 12, 9, 2)
        line((12, 12), (12, 6), 2)
        line((12, 12), (17, 14), 2)
        return
    if key == "shield":                    # protetta / sistema
        line((12, 3), (20, 6), 2)
        line((12, 3), (4, 6), 2)
        line((4, 6), (4, 13), 2)
        line((20, 6), (20, 13), 2)
        line((4, 13), (12, 21), 2)
        line((20, 13), (12, 21), 2)
        line((8, 12), (11, 15), 2)
        line((11, 15), (16, 9), 2)
        return
    if key == "archive":                   # scatola archivio
        rect(3, 4, 18, 4, 2)
        rect(4, 9, 16, 11, 2)
        line((10, 12), (14, 12), 3)
        return
    if key == "trash":                     # rimozione
        rect(6, 7, 12, 13, 2, 1)
        line((4, 7), (20, 7), 2)
        line((10, 4), (14, 4), 2)
        line((10, 10), (10, 17))
        line((14, 10), (14, 17))
        return
    if key == "gauge":                     # governor / tachimetro
        arc(12, 15, 9, 10, 170, 2)
        line((12, 15), (17, 8), 2)
        circ(12, 15, 2, 0)
        return
    if key == "lang":                      # lingua
        circ(12, 12, 9, 2)
        line((3, 12), (21, 12))
        arc(12, 12, 9, 60, 120)
        line((12, 3), (12, 21))
        arc(12, 3, 9, 230, 310)
        return
    if key == "xorg":                      # monitor
        rect(2, 4, 20, 13, 2, 2)
        line((9, 21), (15, 21))
        line((12, 17), (12, 21))
    elif key == "driver":                  # scheda/chip
        rect(5, 5, 14, 14, 2, 1)
        rect(9, 9, 6, 6, 0)
        for i in (8, 12, 16):
            line((i, 2), (i, 5)); line((i, 19), (i, 22))
            line((2, i), (5, i)); line((19, i), (22, i))
    elif key == "gear":                    # ingranaggio
        circ(12, 12, 5, 2)
        circ(12, 12, 1.6, 0)
        for a in range(0, 360, 45):
            r1, r2 = 6.5, 9
            line((12 + r1 * math.cos(math.radians(a)),
                  12 + r1 * math.sin(math.radians(a))),
                 (12 + r2 * math.cos(math.radians(a)),
                  12 + r2 * math.sin(math.radians(a))), 1.6)
    elif key == "start":                   # monitor con avvio dentro
        rect(3, 3, 18, 13, 2, 2)
        line((10, 20), (14, 20), 2)
        line((12, 16), (12, 20), 2)
        pygame.draw.polygon(surf, col, [p(9.5, 7), p(9.5, 12.5),
                                        p(15, 9.75)])
    elif key == "panel":                   # barra applicazioni
        rect(2, 5, 20, 14, 2, 1)
        line((2, 15), (22, 15), 1.5)
        rect(4, 16.5, 3, 2, 0)
        rect(8, 16.5, 3, 2, 0)
    elif key == "desktop":                 # scrivania con icone
        rect(2, 4, 20, 16, 2, 1)
        rect(5, 7, 3.5, 3.5, 0)
        rect(5, 12, 3.5, 3.5, 0)
    elif key == "window":                  # griglia app 2x2
        rect(3, 3, 8, 8, 2, 1.5)
        rect(13, 3, 8, 8, 2, 1.5)
        rect(3, 13, 8, 8, 2, 1.5)
        rect(13, 13, 8, 8, 2, 1.5)
    elif key == "folder":                  # cartella
        line((2, 7), (9, 7), 2)
        rect(2, 7, 20, 13, 2, 1.5)
        line((2, 11), (22, 11), 1.2)
    elif key == "terminal":                # terminale
        rect(2, 4, 20, 16, 2, 1.5)
        line((6, 9), (10, 12), 1.8)
        line((10, 12), (6, 15), 1.8)
        line((12, 15), (17, 15), 1.8)
    elif key == "task":                    # barre attività
        line((4, 18), (4, 10), 2.5)
        line((9, 18), (9, 6), 2.5)
        line((14, 18), (14, 13), 2.5)
        line((19, 18), (19, 8), 2.5)
    elif key == "camera":                  # screenshot
        rect(2, 7, 20, 13, 2, 2)
        rect(8, 4, 8, 3, 2, 1)
        circ(12, 13.5, 3.4, 2)
    elif key == "text":                    # documento di testo
        rect(4, 3, 16, 18, 2, 1.5)
        for yy in (8, 11.5, 15):
            line((7, yy), (17, yy), 1.4)
    elif key == "gamepad":                 # controller
        rect(2, 8, 20, 10, 2, 4)
        line((6, 13), (9, 13), 1.8)
        line((7.5, 11.5), (7.5, 14.5), 1.8)
        circ(16, 12, 1.2, 0)
        circ(18.5, 14, 1.2, 0)
    elif key == "keyboard":                # tastiera
        rect(1.5, 6, 21, 12, 2, 2)
        for xx in (4.5, 8, 11.5, 15, 18.5):
            line((xx, 10), (xx, 10), 1.8)
        line((4.5, 10), (18.5, 10), 1.6)
        line((7, 14.5), (17, 14.5), 2)
    elif key == "access":                  # accessibilita'
        circ(12, 5, 2, 0)
        line((12, 8), (12, 15))
        line((6, 10), (18, 10))
        line((12, 15), (8, 21))
        line((12, 15), (16, 21))
    elif key == "dialog":                  # finestra di dialogo
        rect(2, 5, 20, 13, 2, 2)
        pygame.draw.polygon(surf, col, [p(7, 18), p(11, 18), p(7, 22)])
        line((6, 11), (18, 11), 1.4)
    elif key == "speaker":                 # audio
        pygame.draw.polygon(surf, col, [p(3, 9), p(7, 9), p(11, 5),
                                        p(11, 19), p(7, 15), p(3, 15)])
        arc(11, 12, 5, -60, 60, 1.8)
        arc(11, 12, 8, -55, 55, 1.8)
    elif key == "mixer":                   # cursori mixer
        for i, (xx, yy) in enumerate(((6, 9), (12, 14), (18, 7))):
            line((xx, 3), (xx, 21), 1.4)
            rect(xx - 2.5, yy, 5, 3, 0, 1)
    elif key == "bt":                      # bluetooth
        line((12, 3), (12, 21), 1.8)
        line((12, 3), (17, 8), 1.8)
        line((17, 8), (7, 16), 1.8)
        line((12, 21), (17, 16), 1.8)
        line((17, 16), (7, 8), 1.8)
    elif key == "wifi":                    # wifi
        circ(12, 18, 1.3, 0)
        arc(12, 18, 5, 200, 340, 2)
        arc(12, 18, 9, 205, 335, 2)
        arc(12, 18, 13, 210, 330, 2)
    elif key == "disk":                    # disco / usb
        rect(4, 2, 16, 20, 2, 2)
        circ(12, 9, 3.5, 2)
        rect(7, 15, 10, 5, 2, 1)
    elif key == "cd_disc":                 # disco ottico vero
        circ(12, 12, 10, 2)
        circ(12, 12, 3, 1.6)
        arc(12, 12, 6.5, -60, 30, 1.4)
    elif key == "globe":                   # browser
        circ(12, 12, 9, 2)
        line((3, 12), (21, 12), 1.5)
        pygame.draw.ellipse(surf, col, pygame.Rect(
            int(x + 7 * u), int(y + 3 * u), int(10 * u), int(18 * u)),
            max(1, int(1.5 * u)))
    elif key == "download":                # download / torrent
        line((12, 3), (12, 15), 2)
        line((12, 15), (7, 10), 2)
        line((12, 15), (17, 10), 2)
        line((4, 20), (20, 20), 2)
    elif key == "remote":                  # desktop remoto
        rect(2, 4, 14, 11, 2, 1.5)
        rect(9, 11, 13, 10, 2, 1.5)
    elif key == "video":                   # player video
        rect(2, 5, 20, 14, 2, 2)
        pygame.draw.polygon(surf, col, [p(10, 9), p(10, 15), p(15, 12)])
    elif key == "music":                   # nota musicale
        circ(8, 17, 2.6, 2)
        circ(17, 15, 2.6, 2)
        line((10.6, 17), (10.6, 6), 1.8)
        line((19.6, 15), (19.6, 4), 1.8)
        line((10.6, 6), (19.6, 4), 1.8)
    elif key == "image":                   # immagine
        rect(2, 4, 20, 16, 2, 1.5)
        circ(8, 9, 1.6, 0)
        pygame.draw.polygon(surf, col, [p(4, 19), p(11, 11), p(17, 19)])
    elif key == "film":                    # codec / ffmpeg
        rect(2, 5, 20, 14, 2, 1.5)
        for xx in (5, 9, 13, 17):
            rect(xx, 5, 2, 2, 0)
            rect(xx, 17, 2, 2, 0)
    elif key == "paint":                   # disegno
        line((4, 20), (9, 15), 2)
        pygame.draw.polygon(surf, col, [p(9, 13), p(13, 17), p(20, 6),
                                        p(18, 4)])
    elif key == "doc":                     # documento word
        rect(4, 2, 16, 20, 2, 1.5)
        line((7, 7), (17, 7), 1.4)
        line((7, 11), (17, 11), 1.4)
        line((7, 15), (13, 15), 1.4)
    elif key == "sheet":                   # foglio di calcolo
        rect(3, 3, 18, 18, 2, 1.5)
        line((3, 9), (21, 9), 1.3)
        line((3, 15), (21, 15), 1.3)
        line((9, 3), (9, 21), 1.3)
        line((15, 3), (15, 21), 1.3)
    elif key == "pdf":
        rect(4, 2, 16, 20, 2, 1.5)
        line((8, 16), (8, 9), 1.8)
        arc(9.5, 10.5, 1.8, 90, 270, 1.8)
        line((13, 16), (13, 9), 1.8)
        line((16, 9), (16, 16), 1.8)
    elif key == "calc":                    # calcolatrice
        rect(4, 2, 16, 20, 2, 2)
        rect(7, 5, 10, 4, 0, 1)
        for cy in (12, 16, 19.5):
            for cx in (8, 12, 16):
                circ(cx, cy, 0.9, 0)
    elif key == "zip":                     # archivio zip vero
        rect(3, 5, 18, 15, 2, 1.5)
        line((3, 9), (21, 9), 1.3)
        rect(10.5, 9, 3, 5, 0)
        rect(10.5, 15, 3, 3, 2, 0.5)
    elif key == "monitor":                 # htop / monitor
        rect(2, 4, 20, 13, 2, 2)
        line((4, 13), (7, 13), 1.6)
        line((7, 13), (9, 8), 1.6)
        line((9, 8), (12, 15), 1.6)
        line((12, 15), (14, 11), 1.6)
        line((14, 11), (20, 11), 1.6)
    elif key == "git":                     # rami git
        circ(6, 6, 2.2, 2)
        circ(6, 18, 2.2, 2)
        circ(18, 12, 2.2, 2)
        line((6, 8.2), (6, 15.8), 1.6)
        line((6, 12), (15.8, 12), 1.6)
    elif key == "python":
        circ(9, 8, 4, 2)
        circ(15, 16, 4, 2)
        line((9, 12), (15, 12), 1.6)
    elif key == "edit":                    # nano / editor
        line((3, 20), (7, 19), 2)
        pygame.draw.polygon(surf, col, [p(6, 16), p(9, 19), p(19, 6),
                                        p(16, 3)])
    elif key == "net":                     # wget/curl
        circ(12, 12, 8, 2)
        line((12, 4), (12, 20), 1.3)
        line((4, 12), (20, 12), 1.3)
    elif key == "info":                    # info
        circ(12, 12, 9, 2)
        circ(12, 7.5, 1, 0)
        line((12, 11), (12, 17), 2)
    elif key == "search":                  # lente d'ingrandimento
        circ(10, 10, 6, 2)
        line((14.3, 14.3), (20, 20), 2.4)
    elif key == "goto":                    # vai a: freccia in avanti
        line((4, 12), (18, 12), 2)
        line((12, 6), (18, 12), 2)
        line((12, 18), (18, 12), 2)
    elif key == "font":
        line((5, 19), (11, 5), 2)
        line((11, 5), (17, 19), 2)
        line((7.5, 14), (14.5, 14), 1.6)
    elif key == "cert":                    # certificato
        circ(12, 9, 6, 2)
        line((9, 14), (9, 21), 1.8)
        line((9, 21), (12, 19), 1.8)
        line((12, 19), (15, 21), 1.8)
        line((15, 21), (15, 14), 1.8)
    elif key == "dbus":                    # bus di comunicazione
        line((3, 12), (21, 12), 1.6)
        circ(6, 12, 2.2, 0)
        circ(12, 12, 2.2, 0)
        circ(18, 12, 2.2, 0)
        line((12, 12), (12, 5), 1.4)
        line((6, 12), (6, 19), 1.4)
    elif key == "mouse":
        rect(6, 2, 12, 20, 2, 6)
        line((12, 3), (12, 10), 1.6)
    elif key == "pkg":                     # pacchetto generico
        pygame.draw.polygon(surf, col, [p(12, 2), p(21, 7), p(21, 17),
                                        p(12, 22), p(3, 17), p(3, 7)], 2)
        line((3, 7), (12, 12), 1.4)
        line((21, 7), (12, 12), 1.4)
        line((12, 12), (12, 22), 1.4)
    elif key == "outer":                       # pianeta + satellite (icona statica)
        circ(12, 12, 4.5, 2)                   # pianeta
        # orbita ellittica della luna
        orb_r = 7
        for _deg in (30, 150, 270):
            _a = math.radians(_deg)
            _dx = orb_r * math.cos(_a)
            _dy = orb_r * math.sin(_a) * 0.6
            pygame.draw.circle(surf, col, p(12 + _dx, 12 + _dy), max(1, int(1.0 * u)), 0)
        circ(12 + orb_r * math.cos(0.7), 12 + orb_r * math.sin(0.7) * 0.6, 1.8, 0)
    elif key == "outer_full":                  # OUTER-DESK logo animato (pianeta+sat)
        _cx, _cy = x + 12 * u, y + 12 * u     # centro del pianeta in assoluto
        _pr = 4.5 * u                        # raggio pianeta
        _ar = 7.5 * u                        # raggio orbita
        _sat_a = t * 1.4
        _sat_x = int(_cx + _ar * math.cos(_sat_a))
        _sat_y = int(_cy + _ar * math.sin(_sat_a) * 0.6)
        # orbita ellittica sottile
        ell_surf = pygame.Surface((int(_ar * 2.2), int(_ar * 1.4)), pygame.SRCALPHA)
        ex, ey = ell_surf.get_size()
        pygame.draw.ellipse(ell_surf, (*col, 80), (0, 0, ex, ey), max(1, int(1.2 * u)))
        surf.blit(ell_surf, (int(_cx - ex / 2), int(_cy - ey / 2)))
        # sat
        pygame.draw.circle(surf, col, (_sat_x, _sat_y), max(2, int(1.6 * u)))
        pygame.draw.circle(surf, col, (int(_cx), int(_cy)),
                           max(4, int(_pr)), max(1, int(1.5 * u)))
        hi = tuple(min(255, c + 40) for c in col)
        pygame.draw.circle(surf, hi, (int(_cx - _pr * 0.3),
                           int(_cy - _pr * 0.3)),
                           max(2, int(_pr * 0.3)))
    elif key == "usb":                     # connettore USB (MTP)
        rect(10, 2, 4, 6, 0)
        line((12, 8), (12, 13), 2)
        line((12, 13), (7, 17), 2)
        line((12, 13), (17, 17), 2)
        circ(7, 19, 2, 0)
        circ(17, 19, 2, 0)
        line((5, 5), (8, 5), 1.4)
        line((16, 4), (19, 6), 1.4)
    elif key == "android":                 # omino Android (ADB)
        arc(12, 11, 7, 200, 340, 2)
        rect(6, 11, 12, 8, 0, 2)
        line((6, 19), (6, 22), 2)
        line((18, 19), (18, 22), 2)
        line((3, 7), (6, 10), 1.6)
        line((21, 7), (18, 10), 1.6)
        circ(9, 8, 1, 0)
        circ(15, 8, 1, 0)
    elif key == "w_sunny":                 # sole pieno
        circ(12, 12, 5, 2)
        for a in range(0, 360, 45):
            x1 = 12 + 8 * math.cos(math.radians(a))
            y1 = 12 + 8 * math.sin(math.radians(a))
            x2 = 12 + 11 * math.cos(math.radians(a))
            y2 = 12 + 11 * math.sin(math.radians(a))
            line((x1, y1), (x2, y2), 1.6)
    elif key == "w_cloudy":                # nuvola piena
        circ(9, 13, 5, 0)
        circ(14, 10, 6, 0)
        circ(18, 14, 4, 0)
        rect(7, 13, 13, 6, 0, 3)
    elif key == "w_partly":                # sole+nuvola
        circ(8, 8, 4, 2)
        circ(11, 15, 4, 0)
        circ(15, 13, 5, 0)
        rect(9, 15, 10, 5, 0, 2)
    elif key == "w_rain":                  # nuvola + pioggia
        circ(9, 8, 4, 0)
        circ(14, 6, 5, 0)
        rect(6, 8, 13, 5, 0, 3)
        line((8, 15), (6, 21), 1.8)
        line((13, 15), (11, 21), 1.8)
        line((18, 15), (16, 21), 1.8)
    elif key == "w_snow":                  # nuvola + fiocchi
        circ(9, 8, 4, 0)
        circ(14, 6, 5, 0)
        rect(6, 8, 13, 5, 0, 3)
        for sx in (8, 13, 18):
            line((sx - 2, 18), (sx + 2, 22), 1.6)
            line((sx + 2, 18), (sx - 2, 22), 1.6)
    elif key == "w_storm":                 # nuvola + fulmine
        circ(9, 7, 4, 0)
        circ(14, 5, 5, 0)
        rect(6, 7, 13, 5, 0, 3)
        pygame.draw.polygon(surf, col, [p(14, 13), p(10, 19), p(13, 19),
                                        p(10, 24), p(16, 17), p(13, 17)])
    elif key == "w_fog":                   # nebbia a bande
        for fy in (7, 11, 15, 19):
            line((3, fy), (21, fy), 1.8)
    elif key == "w_clear_night":           # falce di luna + stelle
        pts = []
        for a in range(-100, 101, 10):     # arco esterno convesso
            rad = math.radians(a)
            pts.append(p(11.5 + 8 * math.sin(rad),
                         12 - 8 * math.cos(rad)))
        for a in range(75, -76, -10):      # arco interno concavo
            rad = math.radians(a)
            pts.append(p(16 + 7.2 * math.sin(rad),
                         12 - 7.2 * math.cos(rad)))
        pygame.draw.polygon(surf, col, pts)
        circ(20, 6, 1.4, 0)
        circ(20.5, 13, 1.1, 0)
    else:                                  # ripiego: quadratino
        rect(4, 4, 16, 16, 2, 2)


# ---------------------------------------------------------------- indicatori
def battery_icon(surf, x, y, sz, pct, charging, col_ok, col_low, col_bg):
    u = sz / 24.0
    w, h = int(20 * u), int(11 * u)
    bx, by = int(x), int(y + 6 * u)
    pygame.draw.rect(surf, col_bg, (bx, by, w, h), max(1, int(1.5 * u)),
                     border_radius=int(2 * u))
    pygame.draw.rect(surf, col_bg, (bx + w, by + int(3 * u),
                                    max(2, int(2 * u)), int(5 * u)))
    if pct is not None:
        fill = int((w - 4 * u) * max(0, min(100, pct)) / 100.0)
        col = col_low if pct <= 20 else col_ok
        if fill > 0:
            pygame.draw.rect(surf, col, (bx + int(2 * u), by + int(2 * u),
                                         fill, h - int(4 * u)))
        if charging:
            pygame.draw.polygon(surf, (20, 20, 20), [
                (bx + int(11 * u), by + int(1 * u)),
                (bx + int(7 * u), by + int(6 * u)),
                (bx + int(10 * u), by + int(6 * u)),
                (bx + int(8 * u), by + int(10 * u)),
                (bx + int(13 * u), by + int(5 * u)),
                (bx + int(10 * u), by + int(5 * u))])


def wifi_icon(surf, x, y, sz, level, col_on, col_off):
    """level: None = assente, 0..3 = tacche."""
    u = sz / 24.0
    cx, cy = x + 12 * u, y + 18 * u
    pygame.draw.circle(surf, col_on if level else col_off, (int(cx), int(cy)),
                       max(2, int(1.6 * u)))
    for i, r in enumerate((6, 10, 14)):
        col = col_on if (level or 0) > i else col_off
        box = pygame.Rect(int(cx - r * u), int(cy - r * u),
                          int(2 * r * u), int(2 * r * u))
        pygame.draw.arc(surf, col, box, math.radians(215 - i * 4),
                        math.radians(325 + i * 4), max(1, int(2 * u)))
    if level is None:   # sbarrato
        pygame.draw.line(surf, col_off, (int(x + 3 * u), int(y + 3 * u)),
                         (int(x + 21 * u), int(y + 21 * u)),
                         max(1, int(1.8 * u)))


def bt_icon(surf, x, y, sz, on, col_on, col_off):
    draw(surf, "bt", x, y, sz, col_on if on else col_off)
    if not on:
        u = sz / 24.0
        pygame.draw.line(surf, col_off, (int(x + 3 * u), int(y + 3 * u)),
                         (int(x + 21 * u), int(y + 21 * u)),
                         max(1, int(1.8 * u)))


def volume_icon(surf, x, y, sz, pct, col, col_off):
    u = sz / 24.0

    def p(px, py):
        return (int(x + px * u), int(y + py * u))
    pygame.draw.polygon(surf, col, [p(2, 9), p(6, 9), p(10, 5), p(10, 19),
                                    p(6, 15), p(2, 15)])
    if pct is None or pct == 0:
        pygame.draw.line(surf, col_off, p(13, 8), p(21, 16),
                         max(1, int(1.8 * u)))
        pygame.draw.line(surf, col_off, p(21, 8), p(13, 16),
                         max(1, int(1.8 * u)))
        return
    for i, r in enumerate((4, 7, 10)):
        c = col if pct > i * 33 else col_off
        box = pygame.Rect(int(x + (10 - r) * u), int(y + (12 - r) * u),
                          int(2 * r * u), int(2 * r * u))
        pygame.draw.arc(surf, c, box, math.radians(-55), math.radians(55),
                        max(1, int(1.8 * u)))
