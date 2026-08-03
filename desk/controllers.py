# -*- coding: utf-8 -*-
# ============================================================================
#  VOIDDESK // controllers -- rilevamento e lettura di periferiche esterne
#  per il mappatore comandi (tastiere USB, controller MIDI come una Korg
#  nanoKEY). Stesso principio di evinput.py: lettura diretta dei device node
#  Linux, zero dipendenze esterne.
#
#  Due famiglie di dispositivi, protocolli diversi:
#  - HID/tastiera: /dev/input/event* (evdev), stesso struct input_event
#    gia' usato da evinput.py -- qui pero' leggiamo un file DIVERSO da
#    quello del gamepad interno, per non rubargli eventi
#  - MIDI: /dev/snd/midiC*D* (interfaccia raw ALSA), niente struct fisso,
#    sequenza di byte MIDI standard letta a mano (status byte + data byte).
#
#  NOTA IMPORTANTE: la parte MIDI e' scritta seguendo lo standard
#  documentato (status byte 0x80-0xEF = Note Off/On/Control Change/ecc,
#  bit 7 a 0 = byte dati), ma non e' stata verificata contro un
#  dispositivo MIDI vero -- questa sandbox non ne ha uno collegato.
#  Da confermare sul dispositivo reale.
# ============================================================================
import ctypes
import fcntl
import os
import struct

_EV_KEY = 1
_EVSZ = struct.calcsize("llHHi")

# ioctl EVIOCGNAME: legge il nome leggibile del device. Calcolato
# con la formula vera del kernel Linux (_IOC macro) invece di un
# numero scritto a mano -- un valore sbagliato qui fa fallire in
# silenzio ogni lettura, con l'effetto di scartare TUTTI i
# dispositivi indistintamente (bug vero trovato e corretto: la
# costante originale, 0x82000406, non corrispondeva al calcolo
# reale, che da' 0x81004506).
_IOC_READ = 2


def _IOC(direction, type_, nr, size):
    return (direction << 30) | (type_ << 8) | nr | (size << 16)


_NAME_BUFLEN = 256
_EVIOCGNAME_BASE = _IOC(_IOC_READ, ord("E"), 0x06, _NAME_BUFLEN)


def device_name(fd):
    buf = ctypes.create_string_buffer(256)
    try:
        fcntl.ioctl(fd, _EVIOCGNAME_BASE, buf)
        return buf.value.decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def list_hid_devices(exclude_names=None, input_dir=None):
    """Elenca i device evdev veri presenti, con nome leggibile.
    exclude_names: nomi da NON mostrare (il gamepad interno del
    dispositivo, gia' gestito da evinput.py -- non va doppiato qui).
    input_dir: se non specificato, usa la STESSA risoluzione di
    evinput.py (variabili d'ambiente specifiche di muOS prima del
    percorso fisso) -- e' quello il percorso vero su cui funziona
    davvero il gamepad, quindi e' quello giusto anche qui."""
    if input_dir is None:
        input_dir = os.environ.get(
            "VOIDCAST_INPUT_DIR", os.environ.get(
                "VOIDPAD_INPUT_DIR", "/dev/input"))
    exclude_names = exclude_names or []
    out = []
    try:
        names = sorted(n for n in os.listdir(input_dir)
                       if n.startswith("event"))
    except OSError:
        return out
    for n in names:
        path = os.path.join(input_dir, n)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            continue
        nm = device_name(fd)
        os.close(fd)
        if not nm or any(ex.lower() in nm.lower() for ex in
                         exclude_names):
            continue
        out.append({"path": path, "name": nm, "kind": "hid"})
    return out


def list_midi_devices(snd_dir="/dev/snd"):
    """Elenca i device MIDI raw ALSA veri (/dev/snd/midiC#D#). Il nome
    leggibile vero si trova in /proc/asound/cards, non nel device node
    stesso -- lo leggiamo da li' se disponibile."""
    out = []
    try:
        names = sorted(n for n in os.listdir(snd_dir)
                       if n.startswith("midiC"))
    except OSError:
        return out
    card_names = {}
    try:
        with open("/proc/asound/cards") as f:
            for line in f:
                line = line.strip()
                if line and line[0].isdigit():
                    idx = line.split()[0]
                    card_names[idx] = line
    except OSError:
        pass
    for n in names:
        # formato vero: "midiC1D0" -> scheda 1, device midi 0
        try:
            card_id = n.split("midiC")[1].split("D")[0]
        except (IndexError, ValueError):
            card_id = "?"
        label = card_names.get(card_id, "MIDI " + n)
        out.append({"path": os.path.join(snd_dir, n), "name": label,
                   "kind": "midi"})
    return out


def list_all_controllers(exclude_names=None):
    return (list_hid_devices(exclude_names) +
           list_midi_devices())


def diagnose_hid(exclude_names=None, input_dir=None):
    """Diagnostica precisa, device per device: apertura riuscita o
    negata (con l'errore vero, utile per capire se e' un problema
    di permessi), nome letto o fallito, incluso o escluso dal
    filtro -- per capire DOVE si ferma davvero invece di vedere solo
    un elenco vuoto senza sapere perche'."""
    if input_dir is None:
        input_dir = os.environ.get(
            "VOIDCAST_INPUT_DIR", os.environ.get(
                "VOIDPAD_INPUT_DIR", "/dev/input"))
    exclude_names = exclude_names or []
    out = ["cartella usata: %s" % input_dir]
    try:
        names = sorted(n for n in os.listdir(input_dir)
                       if n.startswith("event"))
    except OSError as e:
        out.append("impossibile leggere la cartella: %s" % e)
        return out
    out.append("file event* trovati: %d" % len(names))
    for n in names:
        path = os.path.join(input_dir, n)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as e:
            out.append("%s: apertura fallita (%s)" % (n, e))
            continue
        try:
            nm = device_name(fd)
        except Exception as e:
            nm = None
            out.append("%s: ioctl nome fallito (%s)" % (n, e))
        os.close(fd)
        if nm is None:
            continue
        if not nm:
            out.append("%s: aperto ok, nome VUOTO" % n)
            continue
        excluded = any(ex.lower() in nm.lower() for ex in
                      exclude_names)
        out.append("%s: nome='%s'%s" % (n, nm,
                   "  [ESCLUSO dal filtro]" if excluded else
                   "  [visibile]"))
    return out


class HidReader:
    """Legge tasti veri da un device evdev esterno (tastiera USB,
    controller HID). Stesso struct input_event di evinput.py."""

    def __init__(self, path):
        self.path = path
        self.fd = None

    def open(self):
        try:
            self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
            return True
        except OSError:
            return False

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def poll(self):
        """Ritorna una lista di (codice_tasto, premuto_bool) per
        ogni evento tasto vero letto in questo giro."""
        if self.fd is None:
            return []
        out = []
        try:
            while True:
                data = os.read(self.fd, _EVSZ)
                if len(data) < _EVSZ:
                    break
                _, _, etype, code, value = struct.unpack("llHHi",
                                                          data)
                if etype == _EV_KEY and value in (0, 1):
                    out.append((code, bool(value)))
        except BlockingIOError:
            pass
        except OSError:
            pass
        return out


class MidiReader:
    """Legge byte MIDI grezzi veri da un device /dev/snd/midiC*D*,
    li ricompone in messaggi (status + 0-2 byte dati) secondo lo
    standard MIDI documentato. Non verificato contro hardware vero
    in questa sandbox -- solo la logica di ricomposizione byte e'
    stata testata con sequenze finte."""

    def __init__(self, path):
        self.path = path
        self.fd = None
        self._buf = bytearray()

    def open(self):
        try:
            self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
            return True
        except OSError:
            return False

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    @staticmethod
    def _msg_len(status):
        """Quanti byte dati servono per questo tipo di messaggio,
        secondo lo standard MIDI (Program Change e Channel Pressure
        ne vogliono 1, la maggior parte 2, i messaggi di sistema
        variano e qui li ignoriamo)."""
        hi = status & 0xF0
        if hi in (0xC0, 0xD0):
            return 1
        if hi in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
            return 2
        return 0

    def poll(self):
        """Ritorna una lista di messaggi MIDI veri ricomposti:
        (status, data1, data2_o_None). Gestisce 'running status'
        (quando un dispositivo manda piu' messaggi dello stesso tipo
        di fila senza ripetere il byte di stato, comune sulle
        tastiere MIDI vere)."""
        if self.fd is None:
            return []
        try:
            chunk = os.read(self.fd, 256)
            if chunk:
                self._buf.extend(chunk)
        except BlockingIOError:
            pass
        except OSError:
            return []
        out = []
        running_status = None
        i = 0
        buf = self._buf
        while i < len(buf):
            b = buf[i]
            if b & 0x80:
                status = b
                i += 1
            else:
                status = running_status
                if status is None:
                    i += 1
                    continue
            if status is None:
                break
            running_status = status if status < 0xF0 else None
            need = self._msg_len(status)
            if need == 0:
                continue
            if i + need > len(buf):
                self._buf = buf[i - 1:] if (buf[i - 1] & 0x80) \
                    else buf[i:]
                return out
            data = buf[i:i + need]
            i += need
            d1 = data[0] if need >= 1 else None
            d2 = data[1] if need >= 2 else None
            out.append((status, d1, d2))
        self._buf = bytearray()
        return out


def midi_signature(status, d1, d2):
    """Firma stabile e leggibile per un tasto MIDI vero, usata come
    chiave di mappatura -- nota+canale per Note On/Off, controller+
    canale per Control Change."""
    hi = status & 0xF0
    ch = status & 0x0F
    if hi in (0x80, 0x90):
        return "midi:note:%d:ch%d" % (d1, ch)
    if hi == 0xB0:
        return "midi:cc:%d:ch%d" % (d1, ch)
    return "midi:raw:%02x:%s:%s" % (status, d1, d2)
