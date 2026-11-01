# Pesquisa — Sequências de Acordes Customizadas

> Preencha esta fase antes de propor qualquer solução. O objetivo é investigar as
> perguntas abaixo com evidência real (código, dados, testes rápidos que você mesmo
> rodou), não chutar. Apague este bloco de instruções antes de entregar.

## Resumo

As 6 sequências são apenas chaves do dicionário `main.sequencias`; a busca atual não
calcula nada em tempo real. Ela consulta a pertinência de um id numérico na tag
pré-computada `Musica.seqs_famosas`, gravada na coluna `SEQ_FAMOSA` do CSV pelo script
`scripts/generate_data_set.py`. A reprodução dessa tag sobre as 67.585 músicas carregadas
por `main.py` mostrou que a regra efetiva é: **um bloco contíguo da sequência aparece em
`musica.cifra` E o vocabulário de acordes da música está contido no vocabulário da
sequência**. Essa conjunção reproduz 100% das 199/296/4/5/7/3 músicas marcadas; subconjunto,
contiguidade, subsequência ou igualdade de vocabulário isoladas deixam entre 433 e 31.102
falsos positivos no total agregado. Não há banco de dados, endpoint de cadastro nem matching em tempo real
hoje; o frontend tem 4 sequências hardcoded (faltam `EmG` e `CA7DmG7`) e envia
`GET /similares?sequencia=...`. O `Dockerfile` atual não declara volume, e o catálogo de
músicas continua sendo lido do CSV em memória a cada início do processo.

## Escopo e método

- Li integralmente os arquivos pedidos: `docs/features/sequencias-customizadas/00-enunciado.md`,
  `README.md`, `AGENTS.md`, `main.py`, `musica.py`,
  `docs/adr/0001-local-only-docker-deploy.md`, `docs/adr/0003-lift-frontend-freeze.md`,
  `static/templates/sequencia.html` e `static/assets/js/controllers/sequencia.js`.
- Também inspecionei `scripts/generate_data_set.py`, `scripts/normalize_chords.R`,
  `scripts/simplify_chords.R`, `scripts/build-chords-transitions.R`, `Dockerfile`,
  `requirements.txt`, `static/index.html`, `static/assets/js/app.js`,
  `static/assets/js/routes.js`, `static/assets/js/controllers/acordes.js`,
  `static/assets/js/controllers/musica.js`, `data/mapeamento_sequencias_famosas.txt`
  e amostras de `data/top/dataset_final.csv` e `data/dataset_seq_notas.csv`.
- Executei um script Python em `/tmp/validate_seq_matching.py` importando `main.py` e
  comparando, para cada uma das 6 sequências, o conjunto marcado em `seqs_famosas` com
  o conjunto produzido por 9 regras candidatas (script completo na seção 2).
- Também executei `/tmp/benchmark_seq_matching.py`, sem cache e com 5 repetições por
  medição, para medir o custo do matcher sobre as 67.585 músicas e sobre o subconjunto
  Rock (7.914 músicas); resultados na seção 2.7.
- Ambiente de execução: Python 3.14.4 do sistema, com Flask 3.1.3 e gunicorn 23.0.0
  instalados a partir de `requirements.txt` numa virtualenv em `/tmp/ciframe-venv`; o
  projeto declara Python 3.9 (`AGENTS.md:9`, `Dockerfile:1`). Nenhum arquivo de código do
  repositório foi alterado.
- Não há suíte de testes automatizada no repositório: a busca por `pytest`, `unittest`,
  `def test_` e arquivos `*test*` só encontrou o template
  `docs/features/sequencias-customizadas/04-test-report.md`.

## Perguntas que você precisa responder

1. **Algoritmo de matching**: hoje, as 6 sequências hardcoded em `main.py` (linhas
   40-45) são comparadas contra músicas via uma tag pré-computada
   (`SEQ_FAMOSA`/`seqs_famosas`, vinda do CSV). Sequências cadastradas pelo usuário
   não têm essa tag — o matching precisa ser calculado em tempo real a partir da
   lista de acordes de cada música (`musica.acordes`/`musica.cifra`). O que vai
   definir "a sequência X aparece na música Y"? A ordem dos acordes importa?
   Repetições de acorde dentro da música importam? É preciso normalizar (ex.:
   maiúsculas/minúsculas, variações de escrita do mesmo acorde)?
2. **Validação da hipótese**: rode o algoritmo que você está considerando contra os
   dados reais em `data/top/dataset_final.csv`, para as 6 sequências hoje
   hardcoded, e confirme (ou refute) que ele reproduz os mesmos matches que o
   código atual produz via `seqs_famosas`. Esse é o bar mínimo de correção que
   você vai usar na fase de testes.
3. **Banco de dados**: quais bancos embarcados (sem serviço externo adicional) são
   viáveis dentro do container Docker único e local-only já documentado em
   `docs/adr/0001-local-only-docker-deploy.md`? O que cada opção implica para o
   `Dockerfile` atual e para a persistência dos dados entre reinícios do
   container?
4. **Frontend existente**: o que a página `#/porsequencia`
   (`static/templates/sequencia.html` +
   `static/assets/js/controllers/sequencia.js`) já faz? Repare que ela tem hoje uma
   lista *hardcoded no JavaScript* de 4 sequências (`sequencia1`..`sequencia4`),
   diferente das 6 que existem no backend — um detalhe real e pré-existente do
   código, não um erro seu, que vale entender antes de decidir o que precisa
   mudar.

## Registro das descobertas

### 1. Algoritmo de matching

#### 1.1 Onde as sequências existem hoje

O backend mantém um único dicionário `sequencias` que mapeia a concatenação dos acordes
para um id numérico (`main.py:40-45`):

| id | chave em `main.sequencias` | acordes na ordem | músicas com a tag | aparece no frontend? |
|---:|---|---|---:|---|
| 0 | `BmGDA` | `Bm`, `G`, `D`, `A` | 199 | sim (`sequencia1`) |
| 1 | `CGAmF` | `C`, `G`, `Am`, `F` | 296 | sim (`sequencia2`) |
| 2 | `EmG` | `Em`, `G` | 4 | não |
| 3 | `CA7DmG7` | `C`, `A7`, `Dm`, `G7` | 5 | não |
| 4 | `GmF` | `Gm`, `F` | 7 | sim (`sequencia3`) |
| 5 | `CC7FFm` | `C`, `C7`, `F`, `Fm` | 3 | sim (`sequencia4`) |

Os mesmos ids e nomes aparecem em `data/mapeamento_sequencias_famosas.txt:1-6`, mas esse
arquivo não é lido por nenhum código da aplicação. O frontend repete 4 dessas sequências
em `static/assets/js/controllers/sequencia.js:2-31` e as publica em
`vm.sequenciasFamosas` (`sequencia.js:33-37`). A rota `#/porsequencia` está em
`static/assets/js/routes.js:17-21`.

#### 1.2 Como a tag `SEQ_FAMOSA` é produzida

A tag não é calculada pela aplicação em execução. Ela já está no CSV e foi gerada pelo
script `scripts/generate_data_set.py`, que faz scraping dos HTMLs de cifra e grava a
coluna `SEQ_FAMOSA` (`scripts/generate_data_set.py:69-89`). A função relevante é
`get_famosas` (`scripts/generate_data_set.py:7-24`):

```python
def get_famosas(acorde):
    seqs = ['bm;g;d;a','c;g;am;f', 'em;g' , 'c;a7;dm;g7', 'gm;f', 'c;c7;f;fm' ]
    out = []
    for i in range(len(seqs)):
        s = seqs[i]
        acorde = acorde.lower()
        if s in acorde:
            achou = True
            tem_seqs = []
            for l in acorde.split(';'):
                tokens = s.split(';')
                if l not in tokens:
                    achou = False
                    break
            if achou:
                tem_seqs.append(str(i))
                out.append("-".join(tem_seqs))
    return out
```

Em termos de dados, para cada uma das 6 sequências, o script exige duas condições
simultâneas:

1. a string `s` (ex.: `bm;g;d;a`) aparece como substring da cifra inteira em minúsculas
   (`scripts/generate_data_set.py:12-13`). Como `s` contém `;`, isso corresponde a um
   bloco ordenado de acordes na cifra;
2. **todos** os acordes da música (`acorde.split(';')`) pertencem ao conjunto de acordes
   da sequência (`scripts/generate_data_set.py:16-20`).

O resultado é uma lista de ids; o chamador faz `''.join(get_famosas(str_notas))`
(`scripts/generate_data_set.py:84-88`), ou seja, sem separador. No conjunto carregado por
`main.py`, o campo só contém um id por linha ou fica sem tag (`['']`): a distribuição
observada é sem tag em 67.071 músicas, `0` em 199, `1` em 296, `2` em 4, `3` em 5, `4`
em 7 e `5` em 3. No CSV cru há 67.072 `NA`, porque a primeira linha é descartada no
carregamento (seção 2.6). Não há valores com dois ids concatenados nos dados atuais.
O próprio `scripts/generate_data_set.py` é Python 2 (`print` como statement em
`scripts/generate_data_set.py:27`, `reload(sys)` em `scripts/generate_data_set.py:29`),
então não roda no runtime Python 3.9 da aplicação.

No carregamento, `main.py` lê a coluna 7 como `SEQ_FAMOSA` (`main.py:33`), divide o campo
por `;` (`main.py:63`) e guarda o resultado em `Musica.seqs_famosas`
(`main.py:69-72`, `musica.py:18`). Uma música sem tag vira `['']` porque `main.py` troca
todas as ocorrências de `NA` por vazio antes de dividir a linha (`main.py:53`).

#### 1.3 O que cada música oferece para um matching em tempo real

`Musica` (`musica.py:1-22`) guarda duas representações distintas da cifra:

- `self.cifra = cifra` (`musica.py:16`): lista ordenada de tokens, com repetições
  preservadas. É o que `limpa_cifra` devolve (`main.py:11-23`) a partir do campo CIFRA
  separado por `;` (`main.py:58-61`).
- `self.acordes = list(set(cifra))` (`musica.py:17`): conjunto sem ordem e sem repetição.

`Musica.tom` é armazenado (`musica.py:15`, `main.py:72`), mas não é consultado em nenhum
ponto do matching: a busca por acordes usa nomes absolutos, e a busca por sequência usa
apenas a tag. Os scripts R `normalize_chords.R` e `simplify_chords.R` geram uma cifra em
graus (`NCIFRA`) em `data/dataset_seq_notas.csv`, mas esse arquivo não é lido por
`main.py`; o app carrega somente `data/top/dataset_final.csv` (`main.py:49`).

#### 1.4 Ordem, repetição e normalização: evidência nos dados

- **Ordem.** A tag é gerada por uma busca de substring ordenada
  (`scripts/generate_data_set.py:13`), enquanto `musica.acordes` é um `set`
  (`musica.py:17`). Portanto, qualquer regra baseada apenas em `musica.acordes` não
  consegue expressar ordem. Exemplo: `one-direction_something-great` tem exatamente o
  vocabulário `{A, Bm, D, G}` e cifra `D;G;Bm;A;D;G;Bm;A;...`, mas **não** tem a tag 0;
  `shakira_waka-waka` tem o mesmo vocabulário e cifra `D;A;Bm;G;D;A;...`, e **tem** a tag
  0 porque a repetição faz aparecer o bloco `Bm;G;D;A` a partir da segunda posição.
- **Repetição.** A tag não exige que a música repita a sequência um número específico de
  vezes; basta uma ocorrência contígua. Repetições adicionais de acordes da própria
  sequência são aceitas (por exemplo, `gusttavo-lima_balada-boa-tche-tche-rere` alterna
  `Bm;G;D;A` com trechos `Bm;A;G;A;D;A` e continua com a tag 0). Colapsar execuções
  consecutivas do mesmo acorde antes de comparar muda os números (por exemplo, `BmGDA`
  passa de 866 para 882 matches), o que mostra que a tag não colapsa repetições.
- **Maiúsculas/minúsculas.** A geração da tag baixa a cifra inteira para minúsculas
  (`scripts/generate_data_set.py:12`), mas a consulta HTTP compara a chave de sequência
  de forma exata e sensível a caso (`main.py:191-195`). Nos dados, `Bm,G,D,A` retorna
  resultados e `bm,g,d,a` retorna `[]`. Para as 6 sequências atuais, rodar a regra de
  contiguidade com tokens em minúsculas produziu exatamente os mesmos conjuntos que a
  versão sensível a caso (diferença 0 nas 6).
- **Variações de escrita.** Após o parsing de `main.py`, `main.acordes` tem 6.653 grafias
  distintas de acorde (o campo `CIFRA` cru do CSV tem 6.703); há acordes com
  `#`, com `b`, com baixo invertido (`Dm9/F`, `Gm/Bb`), extensões (`Bm7(11)`,
  `F#m7(11)`) e 11 tokens cujo primeiro caractere é minúsculo (ex.: `add9`, `b9`,
  `c7m(5+)/e`, `b/Bb`). Não há normalização enarmônica, de sufixo, de baixo invertido
  nem transposição por tom em `main.py`; a comparação é por token exato (a tag apenas
  ignora maiúsculas/minúsculas).
- **Espaços e vírgulas.** O endpoint remove apenas as vírgulas do parâmetro
  (`main.py:191`) e usa o resultado como chave exata. `Bm, G, D, A` (com espaços) e
  `D,A,Bm,G` (outra ordem) retornam `[]`.

#### 1.5 Como o endpoint consome a tag

`GET /similares` (`main.py:170-201`) tem três caminhos: `acordes`, `id_unico_musica` e
`sequencia`. No caminho de sequência, ele remove as vírgulas e procura a string em
`main.sequencias` (`main.py:190-197`). Se não encontrar, a resposta é uma lista vazia; se
encontrar, chama `get_similares_por_sequencia(id_seq, generos_key)`
(`main.py:203-223`), que:

1. filtra as músicas pelos gêneros pedidos com `apply_filtro` (`main.py:205`,
   `main.py:266-272`);
2. mantém as músicas em que `str(id_seq)` está em `musica.seqs_famosas`
   (`main.py:209`);
3. devolve os campos `id_unico_musica`, `id_artista`, `id_musica`, `nome_artista`,
   `nome_musica`, `popularidade`, `acordes`, `genero` e `url` (`main.py:210-220`).

O resultado é paginado por `get_pagina` (`main.py:226-228`), com `TAM_PAGINA = 100`
(`main.py:35`). O endpoint serializa com `json.dumps` e não com `jsonify`
(`main.py:197`, `main.py:201`), mantendo o comportamento legado descrito em
`AGENTS.md:46`. O frontend não envia `pagina` nem tem controle de paginação
(`sequencia.js:72-77`), então só a primeira página é exibida.

### 2. Validação da hipótese

#### 2.1 Script executado

O script abaixo foi salvo em `/tmp/validate_seq_matching.py`, importa `main.py`, percorre
`main.musicas` e compara a tag com 9 regras candidatas. Ele usa `Musica.acordes` no teste
literal de subconjunto/igualdade e `Musica.cifra` nas regras que dependem de ordem. Não
altera nenhum arquivo do repositório.

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida, contra data/top/dataset_final.csv, qual regra reproduz
main.musicas[*].seqs_famosas para as 6 sequências de main.sequencias.

Uso:
    /tmp/ciframe-venv/bin/python /tmp/validate_seq_matching.py

Não altera nenhum arquivo do repositório.
"""
import csv
import os
import sys

REPO = os.getcwd()
sys.path.insert(0, REPO)

import main  # noqa: E402  (carrega o CSV em memória no import)

# Tokens das 6 sequências, na ordem em que aparecem em scripts/generate_data_set.py:8
# e em data/mapeamento_sequencias_famosas.txt.
SEQS = {
    "BmGDA": ["Bm", "G", "D", "A"],
    "CGAmF": ["C", "G", "Am", "F"],
    "EmG": ["Em", "G"],
    "CA7DmG7": ["C", "A7", "Dm", "G7"],
    "GmF": ["Gm", "F"],
    "CC7FFm": ["C", "C7", "F", "Fm"],
}

for _nome, _tokens in SEQS.items():
    assert "".join(_tokens) == _nome


def contiguo(seq, cifra):
    n = len(seq)
    return any(cifra[i:i + n] == seq for i in range(len(cifra) - n + 1))


def subsequencia(seq, cifra):
    it = iter(cifra)
    return all(acorde in it for acorde in seq)


def colapsar(seq):
    saida = []
    for acorde in seq:
        if not saida or saida[-1] != acorde:
            saida.append(acorde)
    return saida


def contiguo_colapsado(seq, cifra):
    return contiguo(colapsar(seq), colapsar(cifra))


def contiguo_e_vocab_igual(seq, cifra):
    return contiguo(seq, cifra) and set(seq) == set(cifra)


def conjuncao_original(seq, cifra):
    """Reproduz get_famosas() de scripts/generate_data_set.py:7-24
    sobre a cifra já parseada por main.py (tokens ligados por ';')."""
    s = ";".join(seq).lower()
    musica = ";".join(cifra).lower()
    if s not in musica:
        return False
    tokens = s.split(";")
    return all(token in tokens for token in musica.split(";"))


def conjuncao_original_raw(seq, cifra_raw):
    """Mesma regra, mas aplicada ao campo CIFRA cru do CSV."""
    s = ";".join(seq).lower()
    musica = cifra_raw.lower()
    if s not in musica:
        return False
    tokens = s.split(";")
    return all(token in tokens for token in musica.split(";"))


ALGORITMOS = {
    # Teste literal contra musica.acordes (musica.py:17).
    "subset": lambda seq, m: set(seq) <= set(m.acordes),
    "set_equal": lambda seq, m: set(seq) == set(m.acordes),
    "contiguo": lambda seq, m: contiguo(seq, m.cifra),
    "contiguo_colapsado": lambda seq, m: contiguo_colapsado(seq, m.cifra),
    "subsequencia": lambda seq, m: subsequencia(seq, m.cifra),
    "subsequencia_e_subset": lambda seq, m: subsequencia(seq, m.cifra) and set(m.cifra) <= set(seq),
    "contiguo_e_set_equal": lambda seq, m: contiguo_e_vocab_igual(seq, m.cifra),
    "conjuncao_original": lambda seq, m: conjuncao_original(seq, m.cifra),
}

# Campo CIFRA cru do CSV, indexado pelo mesmo id_unico_musica de main.musicas.
raw_cifra = {}
with open("data/top/dataset_final.csv", encoding="utf-8") as f:
    for row in csv.reader(f):
        if len(row) >= 9:
            raw_cifra["%s_%s" % (row[0], row[1])] = row[8]

musicas = list(main.musicas.values())
todos = {}

print("Músicas carregadas por main.py: %d" % len(musicas))
print("Linhas de dados no CSV: %d" % len(raw_cifra))
print()

print("| Sequência | Algoritmo | Músicas com tag | Encontradas | Falsos negativos | Falsos positivos | Igual ao tag |")
print("|---|---|---:|---:|---:|---:|:---:|")

for nome, seq in SEQS.items():
    id_seq = main.sequencias[nome]
    tag = {m.id_unico_musica for m in musicas if str(id_seq) in m.seqs_famosas}
    resultados = {}
    for alg_nome, alg in ALGORITMOS.items():
        encontradas = {m.id_unico_musica for m in musicas if alg(seq, m)}
        resultados[alg_nome] = encontradas
        fn = tag - encontradas
        fp = encontradas - tag
        print("| %s | %s | %d | %d | %d | %d | %s |" % (
            nome, alg_nome, len(tag), len(encontradas), len(fn), len(fp),
            "sim" if encontradas == tag else "não"))

    brutas = {m.id_unico_musica for m in musicas
              if conjuncao_original_raw(seq, raw_cifra[m.id_unico_musica])}
    resultados["conjuncao_original_raw"] = brutas
    todos[nome] = resultados
    fn = tag - brutas
    fp = brutas - tag
    print("| %s | %s | %d | %d | %d | %d | %s |" % (
        nome, "conjuncao_original_raw", len(tag), len(brutas), len(fn), len(fp),
        "sim" if brutas == tag else "não"))

print()
print("Verificação do padrão (contíguo E vocabulário igual):")
for nome, seq in SEQS.items():
    id_seq = main.sequencias[nome]
    tag = {m.id_unico_musica for m in musicas if str(id_seq) in m.seqs_famosas}
    conjunto = todos[nome]["contiguo_e_set_equal"]
    print("  %-8s tag=%3d regra=%3d  tag==regra: %s" % (
        nome, len(tag), len(conjunto), tag == conjunto))

print()
print("Exemplos de falsos positivos de 'contiguo' (bloco presente, mas há acorde fora da sequência):")
for nome in ("BmGDA", "CGAmF"):
    seq = SEQS[nome]
    id_seq = main.sequencias[nome]
    tag = {m.id_unico_musica for m in musicas if str(id_seq) in m.seqs_famosas}
    fp = todos[nome]["contiguo"] - tag
    print("  %s:" % nome)
    for mid in list(fp)[:3]:
        m = main.musicas[mid]
        print("    %s | acordes=%s" % (mid, sorted(set(m.cifra))))

print()
print("Exemplos de falsos positivos de 'set_equal' (mesmo vocabulário, bloco em outra ordem/ausente):")
for nome in ("BmGDA", "CGAmF", "CA7DmG7"):
    seq = SEQS[nome]
    id_seq = main.sequencias[nome]
    tag = {m.id_unico_musica for m in musicas if str(id_seq) in m.seqs_famosas}
    fp = todos[nome]["set_equal"] - tag
    print("  %s:" % nome)
    for mid in list(fp)[:2]:
        m = main.musicas[mid]
        print("    %s | cifra=%s" % (mid, ";".join(m.cifra)[:90]))

print()
print("Exemplos de músicas marcadas pela tag (início da cifra):")
for nome, seq in SEQS.items():
    id_seq = main.sequencias[nome]
    marcadas = [m for m in musicas if str(id_seq) in m.seqs_famosas]
    print("  %s (primeiras 2 de %d):" % (nome, len(marcadas)))
    for m in marcadas[:2]:
        print("    %s | cifra=%s" % (m.id_unico_musica, ";".join(m.cifra)[:90]))
```

Execução:

```bash
python3 -m venv /tmp/ciframe-venv
/tmp/ciframe-venv/bin/pip install -r requirements.txt
/tmp/ciframe-venv/bin/python /tmp/validate_seq_matching.py
```

Saída inicial:

```text
Músicas carregadas por main.py: 67585
Linhas de dados no CSV: 67586
```

A diferença de uma música é explicada na seção 2.6.

#### 2.2 Resultados por algoritmo e sequência

`Falsos negativos = tag − algoritmo`; `falsos positivos = algoritmo − tag`. A coluna
"Músicas com tag" é a mesma para todas as linhas de uma sequência.

| Sequência | Algoritmo | Músicas com tag | Encontradas | Falsos negativos | Falsos positivos | Igual ao tag |
|---|---|---:|---:|---:|---:|:---:|
| BmGDA | subset | 199 | 5768 | 0 | 5569 | não |
| BmGDA | set_equal | 199 | 395 | 0 | 196 | não |
| BmGDA | contiguo | 199 | 866 | 0 | 667 | não |
| BmGDA | contiguo_colapsado | 199 | 882 | 0 | 683 | não |
| BmGDA | subsequencia | 199 | 4763 | 0 | 4564 | não |
| BmGDA | subsequencia_e_subset | 199 | 382 | 0 | 183 | não |
| BmGDA | contiguo_e_set_equal | 199 | 199 | 0 | 0 | sim |
| BmGDA | conjuncao_original | 199 | 199 | 0 | 0 | sim |
| BmGDA | conjuncao_original_raw | 199 | 199 | 0 | 0 | sim |
| CGAmF | subset | 296 | 6894 | 0 | 6598 | não |
| CGAmF | set_equal | 296 | 532 | 0 | 236 | não |
| CGAmF | contiguo | 296 | 1216 | 0 | 920 | não |
| CGAmF | contiguo_colapsado | 296 | 1235 | 0 | 939 | não |
| CGAmF | subsequencia | 296 | 5887 | 0 | 5591 | não |
| CGAmF | subsequencia_e_subset | 296 | 518 | 0 | 222 | não |
| CGAmF | contiguo_e_set_equal | 296 | 296 | 0 | 0 | sim |
| CGAmF | conjuncao_original | 296 | 296 | 0 | 0 | sim |
| CGAmF | conjuncao_original_raw | 296 | 296 | 0 | 0 | sim |
| EmG | subset | 4 | 14160 | 0 | 14156 | não |
| EmG | set_equal | 4 | 4 | 0 | 0 | sim |
| EmG | contiguo | 4 | 3110 | 0 | 3106 | não |
| EmG | contiguo_colapsado | 4 | 3110 | 0 | 3106 | não |
| EmG | subsequencia | 4 | 13643 | 0 | 13639 | não |
| EmG | subsequencia_e_subset | 4 | 4 | 0 | 0 | sim |
| EmG | contiguo_e_set_equal | 4 | 4 | 0 | 0 | sim |
| EmG | conjuncao_original | 4 | 4 | 0 | 0 | sim |
| EmG | conjuncao_original_raw | 4 | 4 | 0 | 0 | sim |
| CA7DmG7 | subset | 5 | 582 | 0 | 577 | não |
| CA7DmG7 | set_equal | 5 | 6 | 0 | 1 | não |
| CA7DmG7 | contiguo | 5 | 96 | 0 | 91 | não |
| CA7DmG7 | contiguo_colapsado | 5 | 96 | 0 | 91 | não |
| CA7DmG7 | subsequencia | 5 | 427 | 0 | 422 | não |
| CA7DmG7 | subsequencia_e_subset | 5 | 6 | 0 | 1 | não |
| CA7DmG7 | contiguo_e_set_equal | 5 | 5 | 0 | 0 | sim |
| CA7DmG7 | conjuncao_original | 5 | 5 | 0 | 0 | sim |
| CA7DmG7 | conjuncao_original_raw | 5 | 5 | 0 | 0 | sim |
| GmF | subset | 7 | 3847 | 0 | 3840 | não |
| GmF | set_equal | 7 | 7 | 0 | 0 | sim |
| GmF | contiguo | 7 | 1039 | 0 | 1032 | não |
| GmF | contiguo_colapsado | 7 | 1039 | 0 | 1032 | não |
| GmF | subsequencia | 7 | 3641 | 0 | 3634 | não |
| GmF | subsequencia_e_subset | 7 | 7 | 0 | 0 | sim |
| GmF | contiguo_e_set_equal | 7 | 7 | 0 | 0 | sim |
| GmF | conjuncao_original | 7 | 7 | 0 | 0 | sim |
| GmF | conjuncao_original_raw | 7 | 7 | 0 | 0 | sim |
| CC7FFm | subset | 3 | 365 | 0 | 362 | não |
| CC7FFm | set_equal | 3 | 3 | 0 | 0 | sim |
| CC7FFm | contiguo | 3 | 132 | 0 | 129 | não |
| CC7FFm | contiguo_colapsado | 3 | 132 | 0 | 129 | não |
| CC7FFm | subsequencia | 3 | 280 | 0 | 277 | não |
| CC7FFm | subsequencia_e_subset | 3 | 3 | 0 | 0 | sim |
| CC7FFm | contiguo_e_set_equal | 3 | 3 | 0 | 0 | sim |
| CC7FFm | conjuncao_original | 3 | 3 | 0 | 0 | sim |
| CC7FFm | conjuncao_original_raw | 3 | 3 | 0 | 0 | sim |

#### 2.3 Resumo agregado

Total de músicas com alguma das 6 tags: **514**. Todos os algoritmos tiveram **zero
falsos negativos**; a diferença está nos falsos positivos.

| Algoritmo | Total encontrado | FN | FP | Igual à tag nas 6? |
|---|---:|---:|---:|---|
| subset (contra `musica.acordes`) | 31.616 | 0 | 31.102 | não |
| set_equal | 947 | 0 | 433 | não |
| contiguo | 6.459 | 0 | 5.945 | não |
| contiguo_colapsado | 6.494 | 0 | 5.980 | não |
| subsequencia | 28.641 | 0 | 28.127 | não |
| subsequencia_e_subset | 920 | 0 | 406 | não |
| contiguo_e_set_equal | 514 | 0 | 0 | **sim** |
| conjuncao_original | 514 | 0 | 0 | **sim** |
| conjuncao_original_raw | 514 | 0 | 0 | **sim** |

#### 2.4 Padrão encontrado nas músicas marcadas

A verificação `tag == (contiguo E set_equal)` deu `True` para as 6 sequências:

```text
BmGDA    tag=199 regra=199  tag==regra: True
CGAmF    tag=296 regra=296  tag==regra: True
EmG      tag=  4 regra=  4  tag==regra: True
CA7DmG7  tag=  5 regra=  5  tag==regra: True
GmF      tag=  7 regra=  7  tag==regra: True
CC7FFm   tag=  3 regra=  3  tag==regra: True
```

Ou seja, nos dados atuais, "estar marcado" equivale a:

- existir uma ocorrência **contígua e na ordem** dos acordes da sequência dentro de
  `musica.cifra`; e
- o conjunto de acordes da música ser **exatamente** o conjunto de acordes da sequência
  (nenhum acorde a mais e nenhum a menos). Como a contiguidade já garante que todos os
  acordes da sequência aparecem, a condição de vocabulário equivale à condição
  `set(musica) ⊆ set(sequência)` usada em `get_famosas`
  (`scripts/generate_data_set.py:16-20`).

As regras simples falham exatamente por ignorar uma das duas partes:

- `contiguo` sozinho aceita músicas que contêm o bloco mas têm acordes fora da sequência.
  Exemplo: `gusttavo-lima_meu-destino` contém `Bm;G;D;A`, mas tem também `A#°`, `C#º`,
  `Em` e `D/F#`; a tag 0 não está presente.
- `set_equal` sozinho aceita músicas com o vocabulário certo, mas com o bloco em outra
  ordem ou sem o bloco. Exemplo: `one-direction_something-great` tem
  `{A, Bm, D, G}` e cifra `D;G;Bm;A;...`; `aerosmith_fallen-angels` tem
  `{Am, C, F, G}` e cifra `C;Am;G;F;...`; `os-originais-do-samba_samba-da-vizinha`
  tem `{A7, C, Dm, G7}` e cifra `C;Dm;A7;Dm;G7;...`. Nenhuma das três tem a tag
  correspondente.
- `subset` e `subsequencia` são ainda mais amplos: o primeiro aceita qualquer música
  que use apenas acordes da sequência, mesmo sem o bloco; o segundo aceita o bloco
  espalhado, com lacunas.

Para sequências curtas, a igualdade de vocabulário coincide com a tag nos dados:
`EmG` (4 músicas), `GmF` (7) e `CC7FFm` (3). Para `CA7DmG7`, `set_equal` encontra 6 e a
tag tem 5; a música extra é `os-originais-do-samba_samba-da-vizinha`, que tem os quatro
acordes mas não o bloco contíguo.

#### 2.5 O que o endpoint devolve hoje

Testes com o cliente de testes do Flask, sem subir servidor, sobre as mesmas 6 chaves:

| Consulta | Resultado | Observação |
|---|---:|---|
| `/similares?sequencia=Bm,G,D,A` | 100 | tag tem 199; página 1 de 2 |
| `/similares?sequencia=Bm,G,D,A&pagina=2` | 99 | segunda página |
| `/similares?sequencia=C,G,Am,F` | 100 | tag tem 296 |
| `/similares?sequencia=C,G,Am,F&pagina=3` | 96 | terceira página |
| `/similares?sequencia=Em,G` | 4 | tag tem 4 |
| `/similares?sequencia=C,A7,Dm,G7` | 5 | tag tem 5 |
| `/similares?sequencia=Gm,F` | 7 | tag tem 7 |
| `/similares?sequencia=C,C7,F,Fm` | 3 | tag tem 3 |
| `/similares?sequencia=D,A,Bm,G` | 0 | ordem diferente não é chave |
| `/similares?sequencia=Bm, G, D, A` | 0 | espaço não é removido |
| `/similares?sequencia=bm,g,d,a` | 0 | comparação sensível a caso |
| `/similares?sequencia=xyz` | 0 | chave inexistente retorna lista vazia |

A paginação é aplicada depois do filtro de gênero (`main.py:196`); o endpoint não
devolve o total nem um campo de página. O frontend não pede páginas seguintes.

#### 2.6 Observações do carregamento do CSV que afetam a validação

- `main.py:49-50` abre o CSV e chama `f.readline()` assumindo que a primeira linha é
  cabeçalho. O arquivo `data/top/dataset_final.csv` não tem cabeçalho: a primeira linha
  é a música `14-bis` / `a-qualquer-tempo`. Por isso `main.musicas` tem 67.585 entradas
  enquanto o CSV tem 67.586 linhas de dados. A primeira música tem `SEQ_FAMOSA = NA`,
  então a contagem de tags não muda.
- `main.py:53` faz `line.replace('"', '').replace('NA', '')` antes de dividir por
  vírgulas. Isso remove qualquer substring `NA` de qualquer campo, não só o valor
  sentinela. Sete nomes de música são afetados por conterem `NA` em caixa alta nos dados
  atuais, por exemplo `gusttavo-lima_dna` ("DNA" vira "D"),
  `lourenco-e-lourival_cabana` ("CABANA" vira "CABA") e `sergio-reis_juliana`
  ("JULIANA" vira "JULIA").
- O campo CIFRA vazio é gravado como `NA` no CSV (`scripts/generate_data_set.py:75-76`);
  após a substituição, `main.py:60-61` o transforma em `[]`. Há 8.141 linhas com
  `CIFRA` igual a `NA` no CSV.
- A tag sem sequência é `NA`; após a substituição e o `split(';')`, ela vira `['']`
  (`main.py:53`, `main.py:63`). Por isso a checagem de pertinência usa
  `str(id_seq) in musica.seqs_famosas` (`main.py:209`), e não uma comparação direta
  com o campo inteiro.

#### 2.7 Custo do matching em tempo real

Para fechar a lacuna de performance, medi o matcher sem cache sobre as 67.585 músicas
carregadas por `main.py`, para as 6 sequências, com 5 repetições por medição. A regra
medida é a mesma validada na seção 2.4: bloco contíguo em `Musica.cifra` **e** nenhum
acorde da música fora do vocabulário da sequência, comparando sem diferenciar
maiúsculas de minúsculas. O matcher converte a cifra para minúsculas dentro de cada
execução; a implementação pode normalizar a cifra uma vez no carregamento, o que tende a
reduzir o custo. O filtro "Rock" usa `main.genero_musicas['Rock']` (7.914 músicas), e a
obtenção dessa coleção ficou fora do trecho cronometrado — a tabela mede o matcher sobre
o subconjunto, não o tempo de filtrar.

Script salvo em `/tmp/benchmark_seq_matching.py` e executado a partir da raiz do projeto:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mede o custo do matcher de sequências sobre main.musicas.

Regra medida: bloco contíguo da sequência em Musica.cifra E nenhum acorde
da música fora do vocabulário da sequência, comparando sem diferenciar
maiúsculas de minúsculas. Sem cache.

Uso, a partir da raiz do projeto:
    /tmp/ciframe-venv/bin/python /tmp/benchmark_seq_matching.py
"""
import os
import statistics
import sys
import time

REPO = os.getcwd()
sys.path.insert(0, REPO)

import main  # noqa: E402  (carrega o CSV em memória no import)

SEQS = {
    "BmGDA": ["Bm", "G", "D", "A"],
    "CGAmF": ["C", "G", "Am", "F"],
    "EmG": ["Em", "G"],
    "CA7DmG7": ["C", "A7", "Dm", "G7"],
    "GmF": ["Gm", "F"],
    "CC7FFm": ["C", "C7", "F", "Fm"],
}

REPETICOES = 5


def matcher(seq_lower, musica):
    cifra = [acorde.lower() for acorde in musica.cifra]
    n = len(seq_lower)
    contiguo = any(
        cifra[i:i + n] == seq_lower
        for i in range(len(cifra) - n + 1)
    )
    if not contiguo:
        return False
    vocabulario = set(seq_lower)
    return all(acorde in vocabulario for acorde in cifra)


def medir(seq_lower, colecao):
    tempos = []
    encontradas = None
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        encontradas = sum(1 for musica in colecao if matcher(seq_lower, musica))
        tempos.append((time.perf_counter() - inicio) * 1000.0)
    return encontradas, statistics.mean(tempos), max(tempos)


musicas = list(main.musicas.values())
rock = main.genero_musicas["Rock"]

print("Músicas em main.musicas: %d" % len(musicas))
print("Músicas do gênero Rock: %d" % len(rock))
print("Repetições por medição: %d" % REPETICOES)
print("Python: %s" % sys.version.split()[0])
print()
print("| Sequência | Filtro | Músicas avaliadas | Matches | Média (ms) | Máximo (ms) |")
print("|---|---|---:|---:|---:|---:|")

for nome, tokens in SEQS.items():
    seq_lower = [token.lower() for token in tokens]
    encontradas, media, maximo = medir(seq_lower, musicas)
    print("| %s | sem filtro | %d | %d | %.3f | %.3f |" % (
        nome, len(musicas), encontradas, media, maximo))
    encontradas, media, maximo = medir(seq_lower, rock)
    print("| %s | Rock | %d | %d | %.3f | %.3f |" % (
        nome, len(rock), encontradas, media, maximo))
```

Saída:

```text
Músicas em main.musicas: 67585
Músicas do gênero Rock: 7914
Repetições por medição: 5
Python: 3.14.4

| Sequência | Filtro | Músicas avaliadas | Matches | Média (ms) | Máximo (ms) |
|---|---|---:|---:|---:|---:|
| BmGDA | sem filtro | 67585 | 199 | 521.537 | 575.299 |
| BmGDA | Rock | 7914 | 5 | 55.452 | 66.332 |
| CGAmF | sem filtro | 67585 | 296 | 520.104 | 576.629 |
| CGAmF | Rock | 7914 | 8 | 50.134 | 51.034 |
| EmG | sem filtro | 67585 | 4 | 494.778 | 502.516 |
| EmG | Rock | 7914 | 2 | 48.800 | 50.656 |
| CA7DmG7 | sem filtro | 67585 | 5 | 552.529 | 642.559 |
| CA7DmG7 | Rock | 7914 | 0 | 51.915 | 56.053 |
| GmF | sem filtro | 67585 | 7 | 497.874 | 506.936 |
| GmF | Rock | 7914 | 0 | 55.165 | 65.406 |
| CC7FFm | sem filtro | 67585 | 3 | 516.499 | 548.796 |
| CC7FFm | Rock | 7914 | 0 | 52.297 | 53.291 |
```

A máquina de teste estava compartilhada; em execuções repetidas, a média sem filtro variou
de cerca de **457 ms a 553 ms** e o máximo observado foi **642,6 ms**. A tabela acima
registra a execução mais recente. Com o filtro Rock, a média ficou entre **48,8 ms e
55,5 ms**, com máximo de **66,3 ms**. Para o uso local e single-user do projeto, isso é
aceitável: o pior caso observado fica abaixo de 0,7 s, e o filtro de gênero reduz o custo
para dezenas de milissegundos. Em troca, uma busca sem gênero adiciona cerca de meio
segundo de latência; isso não serve para alta concorrência e deve ser observado no
ambiente real.

**Ressalva de ambiente:** os experimentos rodaram em Python **3.14.4 local**, não no
**Python 3.9** do `Dockerfile:1`. Os tempos são uma referência de ordem de grandeza; o
comportamento no container pode variar e deve ser confirmado no build final antes de
fechar metas de latência.

### 3. Banco de dados

#### 3.1 Estado atual

Não existe banco de dados. `main.py` carrega `data/top/dataset_final.csv` uma única vez,
no import (`main.py:49-98`), e mantém `musicas`, `genero_musicas`, `generos` e `acordes`
em memória (`main.py:37-47`, `main.py:87-96`). `AGENTS.md:9-11` e `README.md:8-9`
registram a ausência de banco. As dependências são apenas Flask e gunicorn
(`requirements.txt:5-6`).

O deploy é um único `Dockerfile` (`Dockerfile:1-12`): base `python:3.9-slim`, instala
`requirements.txt`, copia o projeto para `/app` com `COPY . .` (`Dockerfile:8`), expõe a
porta 8080 e roda `gunicorn --bind 0.0.0.0:8080 main:app` (`Dockerfile:12`). Não há
instrução `VOLUME` nem `USER`. O CMD não passa `--workers`, então o gunicorn usa o
número padrão de 1 worker.

O ADR `docs/adr/0001-local-only-docker-deploy.md:9-16` registra a escolha por um
container único local, sem alvo de nuvem definido. O enunciado fixa que músicas e gêneros
continuam vindo do CSV em memória e que só o catálogo de sequências precisa de
persistência (`00-enunciado.md:60-65`).

#### 3.2 Opções embarcadas

Todas as opções abaixo não exigem um serviço externo adicional; a diferença está na
dependência, no formato do arquivo e nas operações disponíveis.

| Opção | Dependência | Armazenamento | Prós | Contras |
|---|---|---|---|---|
| SQLite (`sqlite3`) | stdlib do CPython; não exige pip novo (confirmar o módulo no build da imagem `python:3.9-slim`) | um arquivo `.db`; com WAL, também `.db-wal`/`.db-shm` | SQL, transações, índices, amplamente usado | precisa de caminho gravável e volume para recriar o container; escritas concorrentes serializam; schema/migrações são responsabilidade da aplicação |
| TinyDB | pacote pip novo | um arquivo JSON | API Python simples, documento JSON, sem SQL | exige mudar `requirements.txt` e rebuildar; reescreve o arquivo inteiro; concorrência e atomicidade ficam por conta do uso |
| `shelve`/`dbm` | stdlib; o backend `dbm` disponível depende da imagem | um ou mais arquivos | sem pip novo, API chave-valor simples | backend pode variar; não há consultas relacionais; concorrência e integridade dependem do backend |
| JSON puro (`json`) | stdlib | um arquivo JSON | sem pip novo, formato legível | leitura/escrita do arquivo inteiro; precisa de bloqueio e escrita atômica implementados à mão; sem índices ou consultas |

#### 3.3 Persistência entre reinícios

O ponto de decisão não é só o formato, mas onde o arquivo fica:

- `docker restart` no mesmo container preserva a camada gravável, incluindo um arquivo
  criado em `/app` em tempo de execução.
- `docker rm` seguido de novo `docker run` (ou recriação por compose) descarta a camada
  gravável; sem volume nomeado ou bind mount, o catálogo some.
- Se o arquivo for gravado no contexto de build (por exemplo, via bind mount em um caminho
  do projeto), um rebuild futuro com `COPY . .` (`Dockerfile:8`) pode copiá-lo para a
  imagem, porque o `.dockerignore` atual só exclui `.git`, `.venv`, `__pycache__` e
  `*.pyc`.
- Um volume de diretório cobre o arquivo principal e os arquivos auxiliares (WAL,
  journals ou múltiplos arquivos de `dbm`/`shelve`); um bind mount de arquivo único não
  cobre os auxiliares.
- Com mais de um worker do gunicorn, cada processo abre o mesmo arquivo; SQLite coordena
  escritas por bloqueio, enquanto arquivos JSON/TinyDB/shelve exigem coordenação
  explícita. O CMD atual não altera o número de workers.

#### 3.4 O que cada opção implica no Dockerfile

- SQLite, `shelve`/`dbm` e JSON puro não mudam `requirements.txt`; a mudança fica no
  caminho do arquivo e, se necessário, na declaração de `VOLUME` ou no uso de `-v`.
- TinyDB exige uma linha nova em `requirements.txt` e um rebuild da imagem.
- Qualquer opção que grave dentro de `/app` convive com `COPY . .` (`Dockerfile:8`) e
  com a ausência de `.dockerignore` para arquivos de banco; gravar fora de `/app` exige
  criar o diretório e montá-lo.
- `main.py` é importado pelo gunicorn (`Dockerfile:12`); o carregamento do CSV continua
  acontecendo no import (`main.py:49-98`), independentemente da tecnologia escolhida
  para as sequências.

### 4. Frontend existente

#### 4.1 Rota e carregamento

O frontend é AngularJS 1.4.9 carregado por CDN, sem build (`static/index.html:129-147`;
`AGENTS.md:12-15`). A rota `#/porsequencia` mapeia para `templates/sequencia.html` e
`SequenciaController` com `controllerAs: "Sequencia"` (`routes.js:17-21`). O módulo
`deciframeApp` é criado em `app.js:1-2`.

#### 4.2 Controller

`SequenciaController` (`sequencia.js:1-105`) define quatro objetos literais
(`sequencia1` a `sequencia4`) em `sequencia.js:2-31` e os empilha em
`vm.sequenciasFamosas` em `sequencia.js:33-37`:

| Objeto | Acordes | Chave correspondente no backend |
|---|---|---|
| `sequencia1` | `Bm`, `G`, `D`, `A` | `BmGDA` (id 0) |
| `sequencia2` | `C`, `G`, `Am`, `F` | `CGAmF` (id 1) |
| `sequencia3` | `Gm`, `F` | `GmF` (id 4) |
| `sequencia4` | `C`, `C7`, `F`, `Fm` | `CC7FFm` (id 5) |

Não há `EmG` nem `CA7DmG7` no frontend. Todos os objetos usam `index: 1`, mas esse campo
não é lido em nenhum lugar do controller ou do template. As cores são todas
`#2E1C74` (`sequencia.js:5-30`).

O controller também:

- atribui `vm.generos = GENEROS` (`sequencia.js:43`), usando a constante fixa definida
  em `app.js:6-58`, e não `GET /generos`;
- define `temAcorde` por identidade de objeto (`sequencia.js:47-53`);
- monta a string de busca concatenando `acorde` com vírgulas em `createChordsString`
  (`sequencia.js:55-61`);
- em `pesquisarPorSequencia` (`sequencia.js:63-90`), usa `apiUrl = ""`
  (`sequencia.js:72`), ou seja, faz a requisição relativa à origem atual, e não usa a
  constante `RESTAPI` (`app.js:3-5`). A URL é
  `similares?sequencia=<acordes separados por vírgula>` e, se houver gênero,
  `&generos=<gênero>` (`sequencia.js:73-76`);
- no sucesso, substitui `vm.musics` pela resposta (`sequencia.js:78-84`); no erro,
  mostra "Ops! Algo errado." (`sequencia.js:85-89`);
- `limparPesquisa` zera `vm.minhaSequencia` e `vm.musics` (`sequencia.js:92-95`);
- `goToLirics` abre `music.url` em nova janela (`sequencia.js:97-99`).

#### 4.3 Template

`static/templates/sequencia.html` tem dois painéis:

- o painel esquerdo (`sequencia.html:3-16`) mostra o título "Aponte uma sequencia de
  acordes", itera `Sequencia.sequenciasFamosas` (`sequencia.html:6`) e, ao clicar em uma
  sequência, chama `Sequencia.pesquisarPorSequencia(sequencia)`. Cada acorde é renderizado
  pela diretiva `df-hex` (`sequencia.html:7`; `static/assets/js/directives/df-hex.js:1-12`);
- o painel direito (`sequencia.html:17-62`) mostra o gênero selecionável
  (`sequencia.html:24-30`), a sequência escolhida como chips (`sequencia.html:34`) e os
  resultados em cards ordenados por `-popularidade` (`sequencia.html:40-58`). O card usa
  `ng-hide="music.diferenca.length"` (`sequencia.html:43`), mas o endpoint de sequência
  não devolve o campo `diferenca` (`main.py:210-220`); esse campo só existe na resposta
  de `get_similares` (caminhos de acordes e de `id_unico_musica`,
  `main.py:256-257`).

Não há formulário, campo de texto, botão de salvar, método POST nem chamada de cadastro
na página. Não há catálogo persistido: a página só conhece a lista fixa de quatro objetos
(mais a sequência selecionada em `vm.minhaSequencia`).

#### 4.4 Catálogo real vs catálogo do frontend

O backend tem 6 sequências (`main.py:40-45`); o frontend tem 4 (`sequencia.js:2-37`).
A página, portanto, não reflete o catálogo do backend. O arquivo
`data/mapeamento_sequencias_famosas.txt:1-6` tem os nomes legíveis das 6 (por exemplo,
"Sequência Em", "Sequência de C (Samba)"), mas não é carregado pelo backend nem pelo
frontend. A busca por qualquer sequência que não esteja nas quatro do frontend só é
possível chamando o endpoint diretamente.

### Conexões entre componentes e fluxo de dados

```text
data/top/dataset_final.csv
  └─ import de main.py (main.py:49-98)
       ├─ musicas: OrderedDict[ id_unico -> Musica ]     (main.py:87-89)
       ├─ genero_musicas: dict[genero -> [Musica]]       (main.py:80-85, 94-96)
       ├─ generos: list                                   (main.py:66, 92)
       ├─ acordes: set                                    (main.py:39, 77-78)
       └─ cada Musica:
            ├─ cifra: lista ordenada, com repetições      (musica.py:16)
            ├─ acordes: list(set(cifra))                  (musica.py:17)
            └─ seqs_famosas: lista vinda de SEQ_FAMOSA    (main.py:63, musica.py:18)

GET /similares?sequencia=Bm,G,D,A[&generos=...]
  └─ main.get_similares (main.py:170-201)
       ├─ remove vírgulas -> "BmGDA"                      (main.py:191)
       ├─ lookup exato em main.sequencias                  (main.py:194)
       ├─ get_similares_por_sequencia(id_seq, generos_key)
       │    ├─ apply_filtro por gênero                     (main.py:205, 266-272)
       │    ├─ mantém músicas com str(id_seq) em seqs_famosas (main.py:209)
       │    └─ monta dicts de resposta                    (main.py:210-221)
       ├─ get_pagina (TAM_PAGINA=100)                      (main.py:226-228)
       └─ json.dumps(...)                                 (main.py:197)

Frontend #/porsequencia
  └─ routes.js:17-21 -> sequencia.html + SequenciaController
       ├─ 4 sequências hardcoded em sequencia.js:2-37
       ├─ clique -> pesquisarPorSequencia                  (sequencia.js:63-90)
       ├─ GET relativo "similares?sequencia=..."           (sequencia.js:72-77)
       └─ vm.musics -> cards                              (sequencia.html:40-58)
```

Não existem hoje: banco de dados, endpoint de cadastro, cálculo de matching em tempo real,
normalização de acordes no backend, transposição por `TOM` ou leitura do catálogo de
sequências pelo frontend.

## Trade-offs identificados

Nenhuma opção abaixo está escolhida nesta fase; os prós e contras alimentam a proposta.

### Algoritmo de matching

| Opção | Prós | Contras |
|---|---|---|
| Subconjunto de `musica.acordes` | simples e rápido; ignora ordem e repetição; usa apenas o conjunto já existente (`musica.py:17`) | não reproduz a tag: 31.616 matches contra 514 nas 6 sequências; não distingue uma música que só usa os acordes daquela que toca a progressão |
| Igualdade de vocabulário (`set`) | elimina músicas com acordes a mais; é exato para `EmG`, `GmF` e `CC7FFm` nos dados | não verifica ordem; falha em `BmGDA` (196 FP), `CGAmF` (236 FP) e `CA7DmG7` (1 FP) |
| Bloco contíguo em `musica.cifra` | expressa ordem e repetição; usa a cifra completa (`musica.py:16`) | aceita músicas com acordes fora da sequência: 6.459 matches contra 514; não reproduz a tag sozinho |
| Subsequência não contígua em `musica.cifra` | tolera lacunas entre os acordes | é ainda mais amplo: 28.641 matches contra 514; perde a noção de bloco |
| Contíguo **e** vocabulário igual | reproduz exatamente as 514 tags atuais; usa as duas representações já disponíveis | é restritivo: uma música que toca a progressão mas acrescenta qualquer outro acorde fica de fora; depende da grafia exata dos acordes |
| Reprodução literal de `get_famosas` (substring em minúsculas + vocabulário da música contido na sequência) | reproduz exatamente as 514 tags, tanto na cifra parseada quanto no campo cru do CSV | replica também detalhes do script antigo (primeira checagem por substring e `''.join` sem separador na geração); depende de a cifra conter a mesma grafia |
| Normalização de grafia (caixa, enarmonia, sufixos, baixo invertido) | aumentaria a tolerância a variações como `A#`/`Bb`, `Dm9/F`, `Bm7(11)` | mudaria os resultados das 6 sequências; exigiria definir equivalências; os dados têm 6.653 grafias distintas após o parsing e 11 tokens iniciados por minúscula |
| Transposição por `TOM`/graus (`NCIFRA`) | permitiria reconhecer a mesma progressão em outros tons | `main.py` não usa `TOM` nem `data/dataset_seq_notas.csv`; exigiria carregar/derivar essa representação e definir a comparação em graus |

### Banco de dados

| Opção | Prós | Contras |
|---|---|---|
| SQLite | sem dependência nova; SQL, transações e índices; um arquivo | schema/migrações; bloqueio de escrita; WAL/journal; volume para recriar o container |
| TinyDB | API simples; documento JSON; sem schema SQL | dependência pip nova; reescreve o arquivo inteiro; concorrência e atomicidade por conta do uso |
| `shelve`/`dbm` | stdlib; chave-valor simples | backend varia com a imagem; múltiplos arquivos possíveis; sem consultas; concorrência limitada |
| JSON puro | stdlib; formato legível | leitura/escrita do arquivo inteiro; bloqueio e escrita atômica manuais; sem índices |
| Arquivo dentro de `/app` | caminho simples; sobrevive a `docker restart` | não sobrevive a `docker rm`/recriação sem volume; `COPY . .` pode copiá-lo no próximo build |
| Volume nomeado ou bind mount | separa dados da imagem; sobrevive à recriação do container | exige mudar a forma de execução (`-v`) ou declarar `VOLUME`; o caminho precisa ser criado e ter permissão de escrita |

### Frontend

| Opção | Prós | Contras |
|---|---|---|
| Manter a lista de 4 sequências e apenas adicionar um formulário | mudança pequena no template/controller | a página continua sem refletir o catálogo real de 6 e sem as sequências novas; exige sincronizar a lista manualmente |
| Carregar o catálogo do backend e renderizar dinamicamente | a página passa a refletir o catálogo persistido; serve para as 6 e para as novas | exige endpoint de listagem e mudança no `ng-repeat`/estado do controller |
| Cadastro na própria `#/porsequencia` | mantém uma única página e o fluxo atual de busca | a página passa a ter dois estados (lista e formulário) e precisa validar a sequência no cliente |
| Cadastro em rota/modal separado | separa listagem de criação | adiciona rota/estado e navegação novos ao frontend legado |
| Entrada por acordes estruturados (adicionar/remover/reordenar) | expressa a lista ordenada e permite reutilizar `df-hex` | exige mais estado e controles no AngularJS 1.4.9; precisa definir como o usuário escolhe acordes válidos |
| Entrada por texto livre separado por vírgulas | reutiliza o formato que `createChordsString` já produz (`sequencia.js:55-61`) | exige parsing/validação de grafias; o backend hoje só aceita a chave exata concatenada |
| Continuar usando `GENEROS` hardcoded (`app.js:6-58`) | nenhuma chamada nova | a lista pode divergir de `GET /generos` (`main.py:158-160`) |
| Buscar gêneros de `GET /generos` | usa a lista real do backend | exige requisição adicional e mudança no controller/template |
