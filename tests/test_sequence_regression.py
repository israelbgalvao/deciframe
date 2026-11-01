import json
import unittest

from tests import isolamento_db
import main


SEQUENCES = (
    ("BmGDA", "0", "Bm,G,D,A", "Sertanejo", 199, 77),
    ("CGAmF", "1", "C,G,Am,F", "Sertanejo", 296, 83),
    ("EmG", "2", "Em,G", "Rock", 4, 2),
    ("CA7DmG7", "3", "C,A7,Dm,G7", "Samba", 5, 5),
    ("GmF", "4", "Gm,F", "Pagode", 7, 2),
    ("CC7FFm", "5", "C,C7,F,Fm", "Pagode", 3, 2),
)


class SequenceRegressionTest(unittest.TestCase):

    def setUp(self):
        self.client = main.app.test_client()

    def _expected_ids(self, tag, genre=None):
        return {
            musica.id_unico_musica
            for musica in main.musicas.values()
            if tag in musica.seqs_famosas
            and (genre is None or musica.genero == genre)
        }

    def _all_pages(self, acordes, genre=None):
        ids = []
        page = 1
        while True:
            params = {"sequencia": acordes, "pagina": page}
            if genre is not None:
                params["generos"] = genre
            response = self.client.get("/similares", query_string=params)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.get_data(as_text=True))
            if not data:
                break
            ids.extend(musica["id_unico_musica"] for musica in data)
            page += 1
            self.assertLess(page, 100)
        return ids

    def test_all_pages_match_tags_without_genre(self):
        for name, tag, acordes, _, expected_count, _ in SEQUENCES:
            with self.subTest(sequencia=name):
                expected = self._expected_ids(tag)
                self.assertEqual(len(expected), expected_count)
                actual = self._all_pages(acordes)
                self.assertEqual(len(actual), len(set(actual)))
                self.assertEqual(set(actual), expected)

    def test_all_pages_match_tags_with_genre(self):
        for name, tag, acordes, genre, _, expected_count in SEQUENCES:
            with self.subTest(sequencia=name, genero=genre):
                expected = self._expected_ids(tag, genre)
                self.assertEqual(len(expected), expected_count)
                actual = self._all_pages(acordes, genre)
                self.assertEqual(len(actual), len(set(actual)))
                self.assertEqual(set(actual), expected)


if __name__ == "__main__":
    unittest.main()
