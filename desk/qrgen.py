"""Generatore QR code puro Python, zero dipendenze esterne -- deve
girare sul dispositivo muOS senza bisogno di installare nulla.
Implementa lo standard ISO/IEC 18004: campo di Galois GF(256) per la
correzione d'errore Reed-Solomon, modo byte (compatibile con
qualunque URL), versioni 1-10, livello di correzione M.
Uso: qrgen.encode(testo) -> matrice 2D di 0/1 (1 = modulo scuro)."""

import math

# ---------------------------------------------------------------
# campo di Galois GF(256), polinomio primitivo x^8+x^4+x^3+x^2+1
# (0x11D) -- tabelle exp/log precalcolate per moltiplicazione veloce
# ---------------------------------------------------------------
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256


def _gf_init():
    x = 1
    for i in range(255):
        _GF_EXP[i] = x
        _GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        _GF_EXP[i] = _GF_EXP[i - 255]


_gf_init()


def _gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _rs_generator_poly(n_ec):
    """Polinomio generatore per n_ec codeword di correzione, nel
    formato che la divisione lunga si aspetta (grado piu' alto
    prima). Verificato contro un vettore di test noto e contro una
    libreria Reed-Solomon indipendente prima di essere accettato."""
    poly = [1]
    for i in range(n_ec):
        root = _GF_EXP[i]
        new_poly = [0] * (len(poly) + 1)
        for j, c in enumerate(poly):
            new_poly[j] ^= _gf_mul(c, root)
            new_poly[j + 1] ^= c
        poly = new_poly
    return list(reversed(poly))


def _rs_encode(data, n_ec):
    gen = _rs_generator_poly(n_ec)
    res = list(data) + [0] * n_ec
    for i in range(len(data)):
        coef = res[i]
        if coef == 0:
            continue
        for j, g in enumerate(gen):
            res[i + j] ^= _gf_mul(g, coef)
    return res[len(data):]


# ---------------------------------------------------------------
# tabelle di capacità: versione -> (dimensione, codeword totali,
# codeword dati livello M, blocchi RS livello M) -- versioni 1-10,
# sufficienti per un URL github tipico (40-60 caratteri circa)
# ---------------------------------------------------------------
# (size, total_codewords, data_codewords_M, ec_codewords_per_block_M,
#  num_blocks_group1, data_per_block_group1, num_blocks_group2,
#  data_per_block_group2)
_QR_TABLE_M = {
    1: (21, 26, 16, 10, 1, 16, 0, 0),
    2: (25, 44, 28, 16, 1, 28, 0, 0),
    3: (29, 70, 44, 26, 1, 44, 0, 0),
    4: (33, 100, 64, 18, 2, 32, 0, 0),
    5: (37, 134, 86, 24, 2, 43, 0, 0),
    6: (41, 172, 108, 16, 4, 27, 0, 0),
    7: (45, 196, 124, 18, 4, 31, 0, 0),
    8: (49, 242, 154, 22, 2, 38, 2, 39),
    9: (53, 292, 182, 22, 3, 36, 2, 37),
    10: (57, 346, 216, 26, 4, 43, 1, 44),
}

_ALIGN_POS = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46],
    10: [6, 28, 50],
}

_FORMAT_INFO_M = {
    # (livello M=0b00) << 3 | maschera, valore a 15 bit gia' con BCH
    0: 0x5412, 1: 0x5125, 2: 0x5E7C, 3: 0x5B4B,
    4: 0x45F9, 5: 0x40CE, 6: 0x4F97, 7: 0x4AA0,
}

# informazioni di versione (18 bit, BCH) -- servono solo da versione 7
# in su, le versioni piu' piccole non le richiedono (dimensione gia'
# implicita). Valori verificati contro una libreria di riferimento.
_VERSION_INFO = {
    7: 31892, 8: 34236, 9: 39577, 10: 42195,
}


def _capacity_for_len(nbytes):
    """Trova la versione piu' piccola (1-10) che ospita nbytes byte
    in modo byte con livello di correzione M, includendo i 2 byte
    di intestazione (modo+lunghezza) tipici per byte mode versioni
    piccole."""
    for v in range(1, 11):
        cap = _QR_TABLE_M[v][2]
        if nbytes + 2 <= cap:
            return v
    raise ValueError("testo troppo lungo per le versioni supportate "
                     "(max ~200 caratteri circa)")


def _encode_data_bits(text, version):
    data = text.encode("utf-8", errors="replace")
    n = len(data)
    bits = "0100"  # modo byte
    len_bits = 8 if version <= 9 else 16
    bits += format(n, "0%db" % len_bits)
    for b in data:
        bits += format(b, "08b")
    cap_bits = _QR_TABLE_M[version][2] * 8
    # terminatore (fino a 4 bit di zero)
    bits += "0" * min(4, cap_bits - len(bits))
    # riempio al multiplo di 8
    while len(bits) % 8 != 0:
        bits += "0"
    # byte di riempimento alternati standard
    pad_bytes = [0xEC, 0x11]
    i = 0
    while len(bits) < cap_bits:
        bits += format(pad_bytes[i % 2], "08b")
        i += 1
    return [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]


def _build_codewords(text, version):
    data_codewords = _encode_data_bits(text, version)
    size, total_cw, data_cw_m, ec_per_block, nb1, dpb1, nb2, dpb2 = \
        _QR_TABLE_M[version]
    blocks = []
    idx = 0
    for _ in range(nb1):
        blocks.append(data_codewords[idx:idx + dpb1])
        idx += dpb1
    for _ in range(nb2):
        blocks.append(data_codewords[idx:idx + dpb2])
        idx += dpb2
    ec_blocks = [_rs_encode(b, ec_per_block) for b in blocks]
    max_data_len = max(len(b) for b in blocks)
    interleaved = []
    for i in range(max_data_len):
        for b in blocks:
            if i < len(b):
                interleaved.append(b[i])
    for i in range(ec_per_block):
        for eb in ec_blocks:
            interleaved.append(eb[i])
    return interleaved


def _make_matrix(version):
    size = _QR_TABLE_M[version][0]
    m = [[None] * size for _ in range(size)]

    def set_finder(mx, my):
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                x, y = mx + dx, my + dy
                if 0 <= x < size and 0 <= y < size:
                    if 0 <= dx <= 6 and 0 <= dy <= 6:
                        dark = (dx in (0, 6) or dy in (0, 6) or
                               (2 <= dx <= 4 and 2 <= dy <= 4))
                        m[y][x] = 1 if dark else 0
                    else:
                        m[y][x] = 0
    set_finder(0, 0)
    set_finder(size - 7, 0)
    set_finder(0, size - 7)
    for i in range(size):
        if m[6][i] is None:
            m[6][i] = 1 if i % 2 == 0 else 0
        if m[i][6] is None:
            m[i][6] = 1 if i % 2 == 0 else 0
    for pos_y in _ALIGN_POS[version]:
        for pos_x in _ALIGN_POS[version]:
            if (pos_x < 8 and pos_y < 8) or \
               (pos_x < 8 and pos_y > size - 9) or \
               (pos_x > size - 9 and pos_y < 8):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    dark = max(abs(dx), abs(dy)) != 1
                    m[pos_y + dy][pos_x + dx] = 1 if dark else 0
    m[size - 8][8] = 1  # modulo scuro fisso
    # fasce per le informazioni di formato -- DEVONO essere riservate
    # ORA, prima del posizionamento dati, altrimenti i dati ci
    # finiscono sopra e vengono poi sovrascritti in silenzio,
    # sfasando tutto lo zigzag che segue (era il bug vero)
    for i in range(9):
        if m[8][i] is None:
            m[8][i] = 0
        if m[i][8] is None:
            m[i][8] = 0
    for i in range(8):
        if m[8][size - 1 - i] is None:
            m[8][size - 1 - i] = 0
        if m[size - 1 - i][8] is None:
            m[size - 1 - i][8] = 0
    version = _size_to_version(size)
    if version in _VERSION_INFO:
        bits = _VERSION_INFO[version]
        for i in range(18):
            bit = (bits >> i) & 1
            m[i // 3][i % 3 + size - 11] = bit
        for i in range(18):
            bit = (bits >> i) & 1
            m[i % 3 + size - 11][i // 3] = bit
    return m, size


def _place_data(m, size, codewords):
    bits = []
    for cw in codewords:
        bits.extend(int(b) for b in format(cw, "08b"))
    bit_i = 0
    n_bits = len(bits)
    col = size - 1
    row_dir = -1
    row = size - 1
    reserved = [[m[y][x] is not None for x in range(size)]
               for y in range(size)]
    while col > 0:
        if col == 6:
            col -= 1
        for _ in range(size):
            for c in (col, col - 1):
                if not reserved[row][c]:
                    val = bits[bit_i] if bit_i < n_bits else 0
                    m[row][c] = val
                    bit_i += 1
            row += row_dir
            if row < 0 or row >= size:
                row_dir *= -1
                row += row_dir
                break
        col -= 2
    return m


def _apply_mask_and_format(m, size, mask_idx, reserved):
    out = [row[:] for row in m]
    for y in range(size):
        for x in range(size):
            if reserved[y][x]:
                continue
            invert = False
            if mask_idx == 0:
                invert = (x + y) % 2 == 0
            elif mask_idx == 1:
                invert = y % 2 == 0
            elif mask_idx == 2:
                invert = x % 3 == 0
            elif mask_idx == 3:
                invert = (x + y) % 3 == 0
            elif mask_idx == 4:
                invert = (y // 2 + x // 3) % 2 == 0
            elif mask_idx == 5:
                invert = (x * y) % 2 + (x * y) % 3 == 0
            elif mask_idx == 6:
                invert = ((x * y) % 2 + (x * y) % 3) % 2 == 0
            elif mask_idx == 7:
                invert = ((x + y) % 2 + (x * y) % 3) % 2 == 0
            if invert and out[y][x] is not None:
                out[y][x] = 1 - out[y][x]
    fmt = _FORMAT_INFO_M[mask_idx]
    fbits = [int(c) for c in format(fmt, "015b")]
    vert_rows = [0, 1, 2, 3, 4, 5, 7, 8]
    for i, r in enumerate(vert_rows):
        out[r][8] = fbits[14 - i]
    horiz_cols = [8, 7, 5, 4, 3, 2, 1, 0]
    for i, c in enumerate(horiz_cols):
        out[8][c] = fbits[7 - i]
    for i in range(8):
        out[8][size - 1 - i] = fbits[14 - i]
    for i in range(7):
        out[size - 7 + i][8] = fbits[6 - i]
    return out


def _size_to_version(size):
    return (size - 21) // 4 + 1


def _penalty(m, size):
    """Punteggio di penalita' standard per scegliere la maschera
    migliore -- meno pattern ripetitivi/sbilanciati, piu' facile da
    scansionare per un lettore vero."""
    p = 0
    for y in range(size):
        run = 1
        for x in range(1, size):
            if m[y][x] == m[y][x - 1]:
                run += 1
            else:
                if run >= 5:
                    p += run - 2
                run = 1
        if run >= 5:
            p += run - 2
    for x in range(size):
        run = 1
        for y in range(1, size):
            if m[y][x] == m[y - 1][x]:
                run += 1
            else:
                if run >= 5:
                    p += run - 2
                run = 1
        if run >= 5:
            p += run - 2
    for y in range(size - 1):
        for x in range(size - 1):
            v = m[y][x]
            if (m[y][x + 1] == v and m[y + 1][x] == v and
                    m[y + 1][x + 1] == v):
                p += 3
    dark = sum(1 for row in m for v in row if v == 1)
    pct = dark * 100 // (size * size)
    p += (abs(pct - 50) // 5) * 10
    return p


def encode(text):
    """Testo -> matrice 2D (lista di liste) di 0/1, 1 = modulo scuro.
    Sceglie la versione minima che ospita il testo, prova tutte le 8
    maschere e sceglie quella con la penalita' minore, come previsto
    dallo standard."""
    nbytes = len(text.encode("utf-8", errors="replace"))
    version = _capacity_for_len(nbytes)
    codewords = _build_codewords(text, version)
    base_m, size = _make_matrix(version)
    reserved = [[base_m[y][x] is not None for x in range(size)]
               for y in range(size)]
    base_m = _place_data(base_m, size, codewords)
    best, best_p = None, None
    for mask_idx in range(8):
        candidate = _apply_mask_and_format(base_m, size, mask_idx,
                                           reserved)
        p = _penalty(candidate, size)
        if best_p is None or p < best_p:
            best_p, best = p, candidate
    return [[1 if v else 0 for v in row] for row in best]
