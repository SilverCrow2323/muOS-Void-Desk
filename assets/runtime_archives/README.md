RUNTIME ARCHIVES
================

Questa cartella contiene archivi compressi dei runtime precompilati per VoidDesk.
Se la cartella `runtime/` è assente o danneggiata, il bootstrap estrarrà
automaticamente il primo archivio qui presente per ripristinare
le dipendenze senza connessione internet.

Formati supportati
------------------

- `.zip`
- `.tar.gz`
- `.tgz`

Struttura attesa
----------------

Ogni archivio può contenere direttamente i package Python (es.
`pygame-2.6.1.data/`, `pygame/`, `evinput/`, `fbdisplay/`, ecc.) oppure
una cartella `runtime/` radice. Il bootstrap posiziona automaticamente
tutto il contenuto in `runtime/`.

Come usare
----------

1. Inserisci gli archivi in questa cartella (es. `pygame-2.6.1.tar.gz`).
2. Al prossimo avvio, se `runtime/` manca o è incompleta, il bootstrap
   estrarrà automaticamente il primo archivio trovato.

Creare un archivio
------------------

Se hai già un runtime funzionante in `runtime/`, puoi creare un archivio
manualmente:

    # ZIP
    cd /path/to/voiddesk
    zip -r assets/runtime_archives/mio_runtime.zip runtime/

    # TAR.GZ
    cd /path/to/voiddesk
    tar -czf assets/runtime_archives/mio_runtime.tar.gz runtime/

Priorità bootstrap
------------------

1. Dipendenze già presenti in `runtime/`
2. Estrazione da `assets/runtime_archives/` (offline)
3. Installazione via pip/apt (online)
4. Download runtime precompilato da GitHub (online)
