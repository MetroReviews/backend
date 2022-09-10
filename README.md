``piccolo migrations new brc --auto && piccolo migrations forwards all`` must be run whenever ``tables.py`` changes.

Run ``python3.10 -m uvicorn brc.app:app`` to run backend
