# Proposta — Sequências de Acordes Customizadas

## Abordagem escolhida

### Algoritmo de matching

A busca passa a usar **um único caminho de código** para as 6 sequências originais e para
as sequências cadastradas. A regra é a de `get_famosas`
(`scripts/generate_data_set.py:7-24`), aplicada sobre a cifra já parseada de cada música
(`Musica.cifra`, `musica.py:16`):

1. normalizar a sequência e a cifra para minúsculas;
2. exigir que a sequência apareça como bloco **contíguo e na ordem** dentro da lista de
   acordes da música;
3. exigir que **todos** os acordes da música pertençam ao vocabulário da sequência, ou
   seja, nenhum acorde da música pode ficar fora da sequência.

A comparação é por token exato, sem diferenciar maiúsculas de minúsculas, como em
`get_famosas` (`scripts/generate_data_set.py:12`). Não há normalização enarmônica,
normalização de sufixos/baixo invertido nem transposição por `TOM`. A regra é restritiva:
uma música que toca a progressão mas acrescenta qualquer outro acorde não casa; esse custo
é aceito para manter o mesmo comportamento das 6 originais.

A tag `Musica.seqs_famosas` **deixa de ser consultada na busca**. Ela permanece no CSV e
passa a ser o **oráculo do teste de regressão**: o matcher precisa reproduzir exatamente
as 514 músicas marcadas pelas 6 tags, como validado em `01-research.md §2.3–2.4`.

**Decisão sobre cache: sem cache.** A medição da seção
`01-research.md §2.7` mostrou, sem cache e com 5 repetições:

- sem filtro de gênero: média de **494,8 a 552,5 ms** e máximo de **642,6 ms** por
  sequência sobre as 67.585 músicas (em execuções repetidas, a média variou de ~457 ms a
  ~553 ms);
- com filtro Rock (7.914 músicas): média de **48,8 a 55,5 ms** e máximo de **66,3 ms**.

Para o uso local e single-user do projeto, o pior caso observado abaixo de 0,7 s é
aceitável; por isso não será adicionado cache nesta feature. A ressalva é que os
experimentos rodaram em **Python 3.14.4 local**, não no **Python 3.9 do `Dockerfile:1`**;
a latência no container deve ser confirmada no build final.

### Banco de dados

SQLite, usando o módulo `sqlite3` da stdlib, sem dependência nova. Só o catálogo de
sequências vai para o banco; `musicas`, `generos` e `genero_musicas` continuam vindo de
`data/top/dataset_final.csv` e sendo carregados em memória por `main.py:49-98`, como hoje.

O caminho do arquivo é configurável pela variável de ambiente `SEQUENCIAS_DB_PATH`, com
padrão `db/sequencias.db` relativo ao diretório de trabalho. O diretório `db/` será
incluído em `.gitignore` e `.dockerignore`. No Docker, o diretório é montado como volume
nomeado, por exemplo:

```bash
docker run -p 8080:8080 -v ciframe-db:/app/db ciframe
```

O volume é o que garante a persistência após `docker rm`; a camada gravável do container
sozinha não sobrevive à recriação. O SQLite serializa as escritas, o que é suficiente para
o cenário local de poucos cadastros concorrentes.

### Esquema de dados (alto nível)

Uma tabela, criada na inicialização se não existir:

```sql
sequencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    acordes TEXT NOT NULL,              -- "Bm,G,D,A"
    chave_unica TEXT NOT NULL UNIQUE,   -- "bm,g,d,a" (ordem preservada)
    origem TEXT NOT NULL CHECK (origem IN ('original', 'usuario')),
    criado_em TEXT NOT NULL             -- ISO 8601 em UTC
)
```

`acordes` preserva a grafia enviada pelo usuário (ou a grafia do mapeamento, no seed) para
exibição; `chave_unica` é a forma normalizada usada para busca e duplicidade: tokens sem
espaços, em minúsculas, unidos por vírgula, na ordem original. A ordem faz parte da
identidade da sequência.

Na inicialização, as 6 originais são inseridas de forma idempotente com `INSERT OR IGNORE`
sobre `chave_unica`, usando os nomes de `data/mapeamento_sequencias_famosas.txt:1-6`
(ex.: "Sequência de Bm", "Sequência Em"). Os IDs internos do SQLite não precisam coincidir
com os IDs 0–5 da tag; a tag não é usada na busca.

### API

Todas as respostas continuam sendo `json.dumps(...)`, não `jsonify`, inclusive as novas.

- `GET /sequencias`: lista o catálogo em um array de objetos, incluindo as 6 originais e
  as novas. Cada objeto tem o formato
  `{"id": 1, "nome": "Sequência de Bm", "acordes": ["Bm", "G", "D", "A"],
  "origem": "original", "criado_em": "..."}`.
- `POST /sequencias`: cadastro anônimo com corpo JSON
  `{"acordes": ["Bm", "G", "D", "A"], "nome": "opcional"}`. Se `nome` não vier, gerar
  `"Sequência " + " - ".join(acordes)`. Resposta `201` com
  `{"status": "criada", "sequencia": {...}}` quando cria; `200` com
  `{"status": "existente", "sequencia": {...}}` quando a `chave_unica` já existe; `400`
  com `{"status": "erro", "erro": "..."}` quando a entrada é inválida. Em nenhum caso cria
  uma segunda linha para a mesma `chave_unica`.
- `GET /similares?sequencia=Bm,G,D,A`: mantém o parâmetro e o formato de resposta atuais,
  mas passa a resolver a sequência no catálogo pela `chave_unica` normalizada (espaços
  removidos, minúsculas, vírgulas). Funciona para qualquer sequência do catálogo, não só
  para as 6 antigas; mantém `generos`, `pagina`, `TAM_PAGINA = 100` e a lista de campos de
  `main.py:203-223`. Sequência desconhecida continua devolvendo `[]`.

Validação do cadastro:

- aceitar de **2 a 8 acordes**;
- remover espaços de cada acorde e ignorar tokens vazios;
- cada acorde precisa existir em `main.acordes`, comparando sem diferenciar maiúsculas de
  minúsculas; caso contrário, responder `400`;
- sequência duplicada não é erro: devolve a existente com `status: "existente"`.

### Frontend

Em `#/porsequencia`:

- remover as 4 sequências hardcoded de
  `static/assets/js/controllers/sequencia.js:2-37`;
- carregar o catálogo de `GET /sequencias` na inicialização do controller e renderizar as
  6 originais + as novas em `Sequencia.sequenciasFamosas`;
- adaptar o controller/template para `acordes` como lista de strings, mantendo o `df-hex`
  (`static/templates/sequencia.html:6-7`) e aplicando a cor padrão `#2E1C74`;
- adicionar um formulário simples de cadastro: nome opcional e acordes separados por
  vírgula. O envio é `POST /sequencias`; em sucesso, recarregar o catálogo e selecionar a
  sequência criada ou existente; em `400`, exibir a mensagem do backend;
- manter `pesquisarPorSequencia` e `createChordsString`
  (`sequencia.js:55-90`) apontando para `similares?sequencia=...`, agora com qualquer
  sequência do catálogo;
- não adicionar paginação, edição, remoção ou autenticação nesta etapa.

## Alternativas consideradas e descartadas

**(a) Proposta 2 — catálogo JSON + índice de matches pré-computado.** Foi descartada
porque troca transações e integridade do SQLite por escrita atômica e lock manuais em
JSON, exige reconstruir o índice no startup e faz o tempo de inicialização crescer com o
catálogo. O ganho de consulta não compensa a complexidade: a medição sem cache mostrou
latência aceitável para o uso local.

**(b) Manter a tag `seqs_famosas` para as 6 originais e usar o matcher só para as novas.**
Foi descartada porque cria dois caminhos de código e duas semânticas que podem divergir.
O matcher reproduz 100% das 514 tags (`01-research.md §2.3–2.4`), então a tag pode ficar
apenas como oráculo de regressão.

**(c) Regra mais frouxa para sequências novas (só bloco contíguo, sem exigir vocabulário).**
Foi descartada porque as novas passariam a se comportar de forma diferente das originais,
contrariando o requisito de buscar "do mesmo jeito". A pesquisa mostrou que só contiguidade
produz 5.945 falsos positivos agregados (`01-research.md §2.3`). O custo aceito é que a
regra escolhida é restritiva: músicas com acordes extras não casam.

## Escopo explícito

**Dentro do escopo:**

- banco SQLite para o catálogo de sequências, com caminho por `SEQUENCIAS_DB_PATH`;
- seed idempotente das 6 originais a partir de `data/mapeamento_sequencias_famosas.txt`;
- `GET /sequencias`, `POST /sequencias` e `/similares?sequencia=...` para todo o catálogo;
- validação de 2 a 8 acordes, comparação sem caixa, rejeição de acorde desconhecido e
  tratamento de duplicata;
- frontend dinâmico em `#/porsequencia`, com formulário de cadastro;
- volume nomeado no Docker, `db/` no `.gitignore` e no `.dockerignore`;
- teste de regressão do matcher contra as 514 tags e testes de API/persistência.

**Fora do escopo (e por quê):**

- corrigir a primeira linha do CSV descartada e o `replace('NA', '')` que corrompe nomes:
  são bugs pré-existentes, documentados em `01-research.md §2.6`, e mexer neles alteraria
  a base de músicas sem relação com o catálogo de sequências;
- normalização enarmônica, de sufixos/baixo invertido ou transposição por `TOM`: a decisão
  é comparação exata por token (exceto caixa), como em `get_famosas`, para preservar o
  comportamento das 6 originais;
- paginação no frontend: o endpoint continua paginando em 100 e a tela atual não tem
  controle de página; é uma melhoria separada;
- edição e remoção de sequências: o pedido cobre cadastro e busca; editar/remover exigiria
  definir propriedade, autenticação e moderação;
- autenticação e moderação: o requisito é catálogo aberto e anônimo;
- migrar `musicas`/`generos` para o banco: o enunciado fixa que esses catálogos continuam
  vindo do CSV em memória.
