import json
import unittest

from tests import isolamento_db
import main


ORIGINAIS = {
    'Sequência de Bm',
    'Sequência de C',
    'Sequência Em',
    'Sequência de C (Samba)',
    'Sequência de Gm',
    'Sequência de C (Samba cont.)',
}


class SequenciasAPITest(unittest.TestCase):

    def setUp(self):
        self.client = main.app.test_client()

    def _post(self, payload):
        response = self.client.post('/sequencias', json=payload)
        return response, json.loads(response.get_data(as_text=True))

    def _get_sequencias(self):
        response = self.client.get('/sequencias')
        self.assertEqual(response.status_code, 200)
        return json.loads(response.get_data(as_text=True))

    def test_get_lista_as_6_originais(self):
        sequencias = self._get_sequencias()
        self.assertTrue(ORIGINAIS.issubset(
            {sequencia['nome'] for sequencia in sequencias}
        ))

    def test_criacao_valida_aparece_no_get_e_busca(self):
        response, data = self._post({
            'acordes': ['D', 'A', 'Bm', 'G'],
            'nome': 'Criação API',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['status'], 'criada')
        sequencia = data['sequencia']
        self.assertEqual(sequencia['nome'], 'Criação API')
        self.assertEqual(sequencia['acordes'], ['D', 'A', 'Bm', 'G'])

        sequencias = self._get_sequencias()
        self.assertIn(sequencia['id'], {item['id'] for item in sequencias})

        busca = self.client.get(
            '/similares',
            query_string={'sequencia': 'D, A, Bm, G'},
        )
        self.assertEqual(busca.status_code, 200)
        self.assertIsInstance(
            json.loads(busca.get_data(as_text=True)), list
        )

    def test_duplicata_com_outra_grafia_nao_cria_linha(self):
        response, criada = self._post({
            'acordes': ['A', 'Bm', 'D', 'G'],
            'nome': 'Duplicata API',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(criada['status'], 'criada')
        antes = len(self._get_sequencias())

        response, existente = self._post({
            'acordes': ' a , bm , d, g ',
            'nome': 'Outro nome',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(existente['status'], 'existente')
        self.assertEqual(existente['sequencia'], criada['sequencia'])
        self.assertEqual(len(self._get_sequencias()), antes)

    def test_um_acorde_e_invalido(self):
        response, data = self._post({'acordes': ['D']})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['status'], 'erro')

    def test_nove_acordes_e_invalido(self):
        response, data = self._post({'acordes': ['D'] * 9})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['status'], 'erro')

    def test_acorde_desconhecido_informa_o_acorde(self):
        response, data = self._post({'acordes': ['Bm', 'ZZZ']})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['status'], 'erro')
        self.assertIn('ZZZ', data['erro'])

    def test_corpo_invalido(self):
        response = self.client.post(
            '/sequencias',
            data='não é json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data['status'], 'erro')

        vazio = self.client.post('/sequencias')
        self.assertEqual(vazio.status_code, 400)

    def test_nome_longo_e_invalido(self):
        response, data = self._post({
            'acordes': ['Bm', 'G'],
            'nome': 'x' * 81,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['status'], 'erro')
        self.assertIn('80', data['erro'])


if __name__ == '__main__':
    unittest.main()
