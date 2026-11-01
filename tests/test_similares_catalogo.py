import json
import unittest

from tests import isolamento_db
import main


class SimilaresCatalogoTest(unittest.TestCase):

    def setUp(self):
        self.client = main.app.test_client()

    def _all_pages(self, sequencia):
        ids = []
        page = 1
        while True:
            response = self.client.get(
                '/similares',
                query_string={'sequencia': sequencia, 'pagina': page},
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.get_data(as_text=True))
            if not data:
                break
            ids.extend(musica['id_unico_musica'] for musica in data)
            page += 1
            self.assertLess(page, 100)
        return ids

    def test_formas_normalizadas_retornam_o_mesmo_conjunto(self):
        esperado = self._all_pages('Bm,G,D,A')
        self.assertTrue(esperado)

        sem_espacos = self._all_pages('bm,g,d,a')
        com_espacos = self._all_pages('Bm, G, D, A')

        self.assertEqual(len(sem_espacos), len(set(sem_espacos)))
        self.assertEqual(len(com_espacos), len(set(com_espacos)))
        self.assertEqual(set(sem_espacos), set(esperado))
        self.assertEqual(set(com_espacos), set(esperado))


if __name__ == '__main__':
    unittest.main()
