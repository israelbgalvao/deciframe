import atexit
import os
import tempfile


diretorio = tempfile.TemporaryDirectory()
os.environ['SEQUENCIAS_DB_PATH'] = os.path.join(
    diretorio.name, 'sequencias.db'
)
atexit.register(diretorio.cleanup)
