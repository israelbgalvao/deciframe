import os
import sqlite3
import tempfile
import unittest
from datetime import datetime

import sequencias_db


class SequenciasDBTest(unittest.TestCase):

    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(
            self.diretorio.name, 'nested', 'sequencias.db'
        )
        self.env_anterior = os.environ.get('SEQUENCIAS_DB_PATH')
        os.environ['SEQUENCIAS_DB_PATH'] = self.db_path
        sequencias_db.inicializar()

    def tearDown(self):
        if self.env_anterior is None:
            os.environ.pop('SEQUENCIAS_DB_PATH', None)
        else:
            os.environ['SEQUENCIAS_DB_PATH'] = self.env_anterior
        self.diretorio.cleanup()

    def test_schema_criado(self):
        self.assertTrue(os.path.exists(self.db_path))
        with sqlite3.connect(self.db_path) as conexao:
            colunas = {
                linha[1]: linha
                for linha in conexao.execute('PRAGMA table_info(sequencias)')
            }
            indices = conexao.execute('PRAGMA index_list(sequencias)').fetchall()

        self.assertEqual(
            set(colunas),
            {'id', 'nome', 'acordes', 'chave_unica', 'origem', 'criado_em'},
        )
        self.assertEqual(colunas['id'][5], 1)
        self.assertEqual(colunas['chave_unica'][3], 1)
        self.assertTrue(any(indice[2] for indice in indices))

    def test_seed_cria_as_6_originais(self):
        sequencias = sequencias_db.listar_sequencias()
        self.assertEqual(len(sequencias), 6)
        self.assertEqual(
            {sequencia['nome'] for sequencia in sequencias},
            {
                'Sequência de Bm',
                'Sequência de C',
                'Sequência Em',
                'Sequência de C (Samba)',
                'Sequência de Gm',
                'Sequência de C (Samba cont.)',
            },
        )
        self.assertTrue(
            all(sequencia['origem'] == 'original' for sequencia in sequencias)
        )
        bm = sequencias_db.buscar_por_chave('Bm,G,D,A')
        self.assertEqual(bm['acordes'], ['Bm', 'G', 'D', 'A'])

    def test_segunda_inicializacao_nao_duplica(self):
        antes = sequencias_db.listar_sequencias()
        sequencias_db.inicializar()
        depois = sequencias_db.listar_sequencias()

        self.assertEqual(len(depois), 6)
        self.assertEqual(antes, depois)

    def test_cadastro(self):
        sequencia, criada = sequencias_db.cadastrar_sequencia(
            ['D', ' A ', 'Bm', 'G'], nome='Nova'
        )

        self.assertTrue(criada)
        self.assertEqual(sequencia['nome'], 'Nova')
        self.assertEqual(sequencia['acordes'], ['D', 'A', 'Bm', 'G'])
        self.assertEqual(sequencia['origem'], 'usuario')
        self.assertIsNotNone(datetime.fromisoformat(sequencia['criado_em']))
        self.assertEqual(len(sequencias_db.listar_sequencias()), 7)
        self.assertEqual(
            sequencias_db.buscar_por_chave('d, a, bm, g'), sequencia
        )

    def test_busca_por_chave_normaliza_caixa_e_espacos(self):
        sequencia = sequencias_db.buscar_por_chave(' bm , G, d, a ')
        self.assertEqual(sequencia['nome'], 'Sequência de Bm')

    def test_duplicata_nao_cria_segunda_linha(self):
        original = sequencias_db.buscar_por_chave('Bm,G,D,A')
        existente, criada = sequencias_db.cadastrar_sequencia(
            [' bm ', 'G', 'D', 'a']
        )

        self.assertFalse(criada)
        self.assertEqual(existente, original)
        self.assertEqual(len(sequencias_db.listar_sequencias()), 6)

    def test_ordem_faz_parte_da_identidade(self):
        original = sequencias_db.buscar_por_chave('Bm,G,D,A')
        self.assertIsNone(sequencias_db.buscar_por_chave('G,Bm,D,A'))

        sequencia, criada = sequencias_db.cadastrar_sequencia(
            ['G', 'Bm', 'D', 'A']
        )

        self.assertTrue(criada)
        self.assertNotEqual(sequencia['id'], original['id'])
        self.assertEqual(len(sequencias_db.listar_sequencias()), 7)


if __name__ == '__main__':
    unittest.main()
