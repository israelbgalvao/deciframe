import json
import unittest

from tests import isolamento_db
import main


CONTRACT_KEYS = {
    "id_artista",
    "nome_artista",
    "id_musica",
    "nome_musica",
    "genero",
    "popularidade",
    "tom",
    "cifra",
    "acordes",
    "seqs_famosas",
    "id_unico_musica",
    "url",
}


class EndpointsLegadosTest(unittest.TestCase):

    def setUp(self):
        self.client = main.app.test_client()
        self.musica_id = next(iter(main.musicas))

    def test_get_musica_mantem_contrato(self):
        response = self.client.get("/musica/%s/" % self.musica_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(set(data), CONTRACT_KEYS)

    def test_get_musicas_mantem_contrato(self):
        response = self.client.get("/musicas")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data)
        for musica in data:
            self.assertEqual(set(musica), CONTRACT_KEYS)


if __name__ == "__main__":
    unittest.main()
