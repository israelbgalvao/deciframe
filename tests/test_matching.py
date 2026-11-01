import unittest

from tests import isolamento_db
import main
from matching import casa_sequencia, normalizar_sequencia
from musica import Musica


ORIGINALS = (
    ("0", "Bm,G,D,A", 199),
    ("1", "C,G,Am,F", 296),
    ("2", "Em,G", 4),
    ("3", "C,A7,Dm,G7", 5),
    ("4", "Gm,F", 7),
    ("5", "C,C7,F,Fm", 3),
)


def criar_musica(cifra):
    return Musica("artista", "Artista", "musica", "Música", "Rock", 1, [], "C", cifra)


class NormalizacaoTest(unittest.TestCase):

    def test_remove_espacos_vazios_e_normaliza_caixa(self):
        self.assertEqual(
            normalizar_sequencia(" Bm, , G ,D , A "),
            ["bm", "g", "d", "a"],
        )
        self.assertEqual(normalizar_sequencia(["Bm", "", " G "]), ["bm", "g"])
        self.assertEqual(normalizar_sequencia(" , "), [])


class MatcherTest(unittest.TestCase):

    def test_bloco_contiguo_presente(self):
        self.assertTrue(
            casa_sequencia(
                ["bm", "g", "d", "a"],
                ["bm", "g", "d", "a"],
                {"bm", "g", "d", "a"},
            )
        )

    def test_acorde_extra_na_musica(self):
        self.assertFalse(
            casa_sequencia(
                ["bm", "g", "d", "a"],
                ["bm", "g", "d", "a", "e"],
                {"bm", "g", "d", "a", "e"},
            )
        )

    def test_ordem_diferente(self):
        self.assertFalse(
            casa_sequencia(
                ["bm", "g", "d", "a"],
                ["bm", "g", "a", "d"],
                {"bm", "g", "d", "a"},
            )
        )

    def test_maiusculas_e_minusculas(self):
        musica = criar_musica(["Bm", "G", "D", "A"])
        sequencia = normalizar_sequencia("Bm, g, D, a")
        self.assertTrue(
            casa_sequencia(
                sequencia,
                musica.cifra_minuscula,
                musica.acordes_minusculos,
            )
        )

    def test_acorde_repetido(self):
        self.assertTrue(
            casa_sequencia(
                ["bm", "g", "bm"],
                ["bm", "g", "bm"],
                {"bm", "g"},
            )
        )

    def test_musica_sem_cifra(self):
        musica = criar_musica([])
        self.assertFalse(
            casa_sequencia(
                ["bm", "g"],
                musica.cifra_minuscula,
                musica.acordes_minusculos,
            )
        )

    def test_sequencia_vazia(self):
        self.assertFalse(casa_sequencia([], ["bm"], {"bm"}))


class MatcherRegressaoTest(unittest.TestCase):

    def test_reproduz_as_tags_das_6_originais(self):
        for tag, sequencia, esperado in ORIGINALS:
            with self.subTest(sequencia=sequencia):
                normalizada = normalizar_sequencia(sequencia)
                expected = {
                    musica.id_unico_musica
                    for musica in main.musicas.values()
                    if tag in musica.seqs_famosas
                }
                actual = {
                    musica.id_unico_musica
                    for musica in main.musicas.values()
                    if casa_sequencia(
                        normalizada,
                        musica.cifra_minuscula,
                        musica.acordes_minusculos,
                    )
                }
                self.assertEqual(len(expected), esperado)
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
