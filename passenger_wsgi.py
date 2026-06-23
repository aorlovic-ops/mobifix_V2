import sys
import os

# Strogo naređujemo Pythonu da gleda samo NOVU mapu
NOVA_PUTANJA = "/home/mobiserv/test.webrjesenja.com.hr"

# Brišemo stare putanje ako su ostale u memoriji
sys.path = [p for p in sys.path if "mobifix.webrjesenja.com.hr" not in p]

# Ubacujemo novu putanju na prvo mjesto
if NOVA_PUTANJA not in sys.path:
    sys.path.insert(0, NOVA_PUTANJA)

try:
    from main import app
    application = app
except Exception as e:
    with open(os.path.join(NOVA_PUTANJA, "GRESKA_LOG.txt"), "w") as f:
        import traceback
        traceback.print_exc(file=f)
    
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/html; charset=utf-8')])
        return [b"Greska je zapisana u novi GRESKA_LOG.txt!"]