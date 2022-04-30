``piccolo migrations new brc --auto && piccolo migrations forwards session_auth && piccolo migrations forwards user`` must be run initially to create session tables

Run ``python3.10 -m uvicorn brc.app:app`` to run backend