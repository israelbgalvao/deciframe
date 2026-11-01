import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from matching import normalizar_sequencia


CAMINHO_PADRAO = 'db/sequencias.db'
CAMINHO_MAPEAMENTO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'data',
    'mapeamento_sequencias_famosas.txt',
)

SCHEMA = '''
CREATE TABLE IF NOT EXISTS sequencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    acordes TEXT NOT NULL,
    chave_unica TEXT NOT NULL UNIQUE,
    origem TEXT NOT NULL CHECK (origem IN ('original', 'usuario')),
    criado_em TEXT NOT NULL
)
'''


def _caminho_banco():
    return os.environ.get('SEQUENCIAS_DB_PATH') or CAMINHO_PADRAO


def _agora():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conexao():
    caminho = _caminho_banco()
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    try:
        with conexao:
            yield conexao
    finally:
        conexao.close()


def _preparar_acordes(acordes):
    if isinstance(acordes, str):
        acordes = acordes.split(',')

    preparados = []
    for acorde in acordes:
        acorde = ''.join(str(acorde).split())
        if acorde:
            preparados.append(acorde)
    return preparados


def _gerar_chave(acordes):
    return ','.join(normalizar_sequencia(acordes))


def _para_sequencia(linha):
    return {
        'id': linha['id'],
        'nome': linha['nome'],
        'acordes': linha['acordes'].split(','),
        'origem': linha['origem'],
        'criado_em': linha['criado_em'],
    }


def _ler_sequencias_originais():
    with open(CAMINHO_MAPEAMENTO, encoding='utf-8') as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha:
                continue
            _, nome, acordes = linha.split(',', 2)
            acordes = [
                acorde.strip()
                for acorde in acordes.replace(' - ', ',').split(',')
                if acorde.strip()
            ]
            yield nome, acordes


def inicializar():
    criado_em = _agora()
    with _conexao() as conexao:
        conexao.execute(SCHEMA)
        for nome, acordes in _ler_sequencias_originais():
            conexao.execute(
                '''
                INSERT OR IGNORE INTO sequencias
                    (nome, acordes, chave_unica, origem, criado_em)
                VALUES (?, ?, ?, 'original', ?)
                ''',
                (nome, ','.join(acordes), _gerar_chave(acordes), criado_em),
            )


def listar_sequencias():
    with _conexao() as conexao:
        linhas = conexao.execute(
            'SELECT * FROM sequencias ORDER BY id'
        ).fetchall()
    return [_para_sequencia(linha) for linha in linhas]


def buscar_por_chave(sequencia):
    chave = _gerar_chave(sequencia)
    with _conexao() as conexao:
        linha = conexao.execute(
            'SELECT * FROM sequencias WHERE chave_unica = ?', (chave,)
        ).fetchone()
    return _para_sequencia(linha) if linha else None


def cadastrar_sequencia(acordes, nome=None, origem='usuario'):
    acordes = _preparar_acordes(acordes)
    if not acordes:
        raise ValueError('sequencia sem acordes')

    chave = _gerar_chave(acordes)
    if not nome:
        nome = 'Sequência ' + ' - '.join(acordes)

    with _conexao() as conexao:
        resultado = conexao.execute(
            '''
            INSERT OR IGNORE INTO sequencias
                (nome, acordes, chave_unica, origem, criado_em)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (nome, ','.join(acordes), chave, origem, _agora()),
        )
        criada = resultado.rowcount == 1
        linha = conexao.execute(
            'SELECT * FROM sequencias WHERE chave_unica = ?', (chave,)
        ).fetchone()

    return _para_sequencia(linha), criada
