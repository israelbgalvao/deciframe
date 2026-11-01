# Plano — Sequências de Acordes Customizadas

## Contexto, escopo e restrições

- Hoje as 6 sequências vivem em `main.py:40-45`; `/similares` usa a tag
  `Musica.seqs_famosas`, o frontend tem 4 sequências hardcoded, não há banco, suíte
  de testes nem volume Docker.
- A feature adiciona catálogo persistente de sequências customizadas, cadastro
  anônimo, busca por qualquer sequência do catálogo e formulário em
  `#/porsequencia`, conforme `02-proposal.md` e ADR 0002.
- Restrições: Python 3.9 no container; somente stdlib para testes e SQLite; manter
  `json.dumps` e o `Content-Type` legado; CSV continua sendo a fonte de músicas e
  gêneros; sem cache; sem normalização enarmônica/transposição; sem autenticação ou
  moderação; corrigir bugs do CSV está fora do escopo.
- Execução em 8 passos estritamente sequenciais, sem estimativa de calendário: um
  passo só começa quando a verificação do anterior passar. Rollout é local, via
  Docker; não há observabilidade adicional prevista além dos testes e do E2E.

## Decisões de design

- Um único matcher para as 6 originais e as novas; `seqs_famosas` fica apenas como
  oráculo de regressão.
- SQLite da stdlib para o catálogo; músicas e gêneros continuam no CSV em memória;
  caminho por `SEQUENCIAS_DB_PATH`.
- Cifra em minúsculas e vocabulário calculados uma vez no carregamento; sem cache
  por busca.
- `/similares` resolve a sequência pela `chave_unica` normalizada e mantém o
  contrato/`json.dumps` atual.
- `GET/POST /sequencias` com validação de 2–8 acordes, vocabulário de
  `main.acordes` e duplicata idempotente.
- Frontend carrega o catálogo e cadastra em `#/porsequencia`; sem paginação,
  edição, remoção ou autenticação nesta feature.

## Passos

1. [x] **Rede de segurança primeiro: teste de regressão com `unittest`.**
   - Criar `tests/test_sequence_regression.py`, sem dependência nova, usando
     `main.app.test_client()`.
   - Para cada uma das 6 sequências, chamar
     `/similares?sequencia=<acordes>`, agregar `id_unico_musica` de todas as
     páginas até a lista vazia e comparar o conjunto com as músicas marcadas em
     `seqs_famosas`.
   - Repetir sem `generos` e com um gênero que tenha marcação conhecida:
     Sertanejo para `BmGDA`/`CGAmF`, Rock para `EmG`, Samba para `CA7DmG7`,
     Pagode para `GmF`/`CC7FFm`.
   - Comparar sempre `set` de ids, nunca a página 1 nem a ordem. Contagens
     esperadas sem gênero: `199, 296, 4, 5, 7, 3`; com os gêneros acima:
     `77, 83, 2, 5, 2, 2`.
   - Rodar contra o código atual: `python -m unittest discover -s tests -v`;
     repetir com `PYTHONHASHSEED=2`.
   - **Verificação:** a suíte passa no código atual, com os 6 conjuntos iguais
     às tags e sem diferença entre as duas seeds.

2. [x] **Matcher puro e pré-processamento único da cifra.**
   - Criar uma função pura, testável fora do Flask e do banco (ex.:
     `matching.py`): normaliza a sequência e recebe tokens já prontos; exige
     bloco contíguo na ordem e nenhum acorde da música fora do vocabulário.
   - Em `musica.py`/`main.py`, calcular uma única vez, no carregamento do CSV,
     `cifra_minuscula` e `acordes_minusculos`; a busca não deve chamar `lower()`
     por música a cada request.
   - Manter a tag `seqs_famosas` intacta como oráculo; não usá-la no matcher.
   - Criar `tests/test_matching.py` com casos pequenos: bloco contíguo, acorde
     extra, ordem diferente, maiúsculas/minúsculas e repetição de acorde.
   - **Problema encontrado:** `acordes_minusculos` (set) e `cifra_minuscula`
     passaram a integrar `Musica.__dict__`; `GET /musica/<id>/` e `GET /musicas`
     fazem `json.dumps(musica.__dict__)` e agora respondem 500
     (`TypeError: Object of type set is not JSON serializable`). Mesmo como lista,
     os campos novos mudariam o contrato.
   - **Correção escolhida:** manter o pré-processamento em `Musica` e criar um
     serializador explícito com os 12 campos do contrato para esses dois endpoints;
     é mais simples que tirar o pré-processamento do `__dict__` e evita recalcular
     `lower()` a cada busca.
   - Criar `tests/test_endpoints_legados.py` cobrindo status 200 e as chaves exatas
     de `GET /musica/<id>/` e `GET /musicas`.
   - **Verificação:** testes unitários passam, o matcher não consulta
     `seqs_famosas`, não normaliza a cifra no laço e os dois endpoints legados
     mantêm as 12 chaves originais.

3. [x] **Banco SQLite, schema e seed idempotente.**
   - Criar `sequencias_db.py` com conexão via `SEQUENCIAS_DB_PATH` (padrão
     `db/sequencias.db`), criação do diretório pai, `CREATE TABLE IF NOT EXISTS`
     e as operações de listar, buscar por chave e cadastrar.
   - Schema conforme proposta: `id`, `nome`, `acordes`, `chave_unica` única,
     `origem` (`original`/`usuario`) e `criado_em` em ISO 8601 UTC.
   - Semear as 6 originais de forma idempotente com `INSERT OR IGNORE`, lendo os
     nomes de `data/mapeamento_sequencias_famosas.txt`.
   - Criar `tests/test_sequencias_db.py` usando banco temporário
     (`tempfile.TemporaryDirectory`), sem tocar em `db/` real: schema, seed,
     segunda inicialização sem duplicar, cadastro, busca e duplicata.
   - **Verificação:** testes passam; após duas inicializações o banco tem
     exatamente 6 originais; o arquivo temporário é removido no fim.

4. [x] **Trocar `/similares?sequencia=` para catálogo + matcher.**
   - Resolver o parâmetro `sequencia` pela `chave_unica` normalizada do catálogo
     (espaços e caixa), mantendo `generos`, `pagina` e `TAM_PAGINA`.
   - Substituir a consulta à tag pelo matcher sobre as músicas já pré-processadas;
     preservar os mesmos campos da resposta e devolver `[]` para sequência
     desconhecida.
   - Registrar a mudança intencional de API: a busca agora aceita minúsculas e
     espaços; não alterar o `Content-Type` legado.
   - Rodar novamente a regressão do passo 1; adicionar `tests/test_similares_catalogo.py`
     verificando que `bm,g,d,a`/`Bm, G, D, A` retornam o mesmo conjunto de
     `Bm,G,D,A` em todas as páginas.
   - Centralizar o isolamento em `tests/isolamento_db.py`, importado antes de
     `main` em todo teste que carrega o módulo, para apontar
     `SEQUENCIAS_DB_PATH` para um diretório temporário.
   - **Verificação:** regressão continua passando sem alterar os testes e a busca
     normalizada devolve o mesmo conjunto; a tag não é mais lida pela busca.

5. [x] **`GET /sequencias` e `POST /sequencias`.**
   - `GET /sequencias`: array com as 6 originais e as novas, cada item com `id`,
     `nome`, `acordes` (lista), `origem` e `criado_em`; resposta com `json.dumps`.
   - `POST /sequencias`: corpo `{"acordes": [...], "nome": "opcional"}`; aceitar
     também `acordes` como string separada por vírgulas. Validar 2–8 acordes,
     remover espaços, aceitar caixa, exigir cada acorde em `main.acordes` e nome
     com no máximo 80 caracteres; responder `400` caso contrário.
   - Construir `acordes_minusculos` uma única vez após o CSV e usar esse conjunto
     na validação do cadastro, sem recalcular por request.
   - Duplicata: não criar outra linha; devolver a existente com
     `status: "existente"`. Criação nova: `status: "criada"`.
   - Criar `tests/test_sequencias_api.py`: criação válida, aparecimento no `GET`,
     busca em `/similares`, duplicata com outra grafia, 1 e 9 acordes, acorde
     desconhecido, corpo inválido, nome longo e as 6 originais no `GET`.
   - **Verificação:** testes de API passam; após duplicata o banco continua com
     uma única linha para a `chave_unica`; todas as respostas continuam
     `json.dumps`.

6. [x] **Frontend dinâmico e formulário.**
   - Em `static/assets/js/controllers/sequencia.js`, remover as 4 sequências
     hardcoded, carregar `GET /sequencias` na inicialização e adaptar
     `acordes` de lista de strings para o template (`df-hex`, cor `#2E1C74`).
   - Em `static/templates/sequencia.html`, exibir `sequencia.nome` acima dos
     acordes e adicionar formulário em `#/porsequencia` com nome opcional e acordes
     separados por vírgula; enviar `POST /sequencias`, recarregar o catálogo e
     selecionar a criada/existente; mostrar erro do backend.
   - Exibir "Sequência cadastrada!" em `201` e "Essa sequência já existia." em
     `200`; em erro, exibir a mensagem `erro` retornada pelo backend.
   - Manter `pesquisarPorSequencia` e `createChordsString` usando
     `similares?sequencia=...`; não adicionar paginação, edição ou remoção.
   - **Verificação:** com o backend rodando, a tela exibe as 6 originais, cadastra
     uma nova, busca por ela, trata duplicata/inválida e continua buscando as 6.

7. [x] **Docker e documentação.**
   - Adicionar `db/` a `.gitignore` e `.dockerignore`.
   - Atualizar `README.md` e `AGENTS.md`, que hoje dizem que não há banco: catálogo
     SQLite, `SEQUENCIAS_DB_PATH`, volume e comando
     `docker run -p 8080:8080 -v ciframe-db:/app/db ciframe`.
   - Documentar a mudança intencional de `/similares` (aceita minúsculas/espaços).
   - **Verificação:** `git diff --check` limpo; os comandos documentados usam o
     volume e o caminho do banco; nenhuma dependência nova em `requirements.txt`.

8. [ ] **Verificação de ponta a ponta no container Python 3.9.**
   - `docker build -t ciframe .`; confirmar Python 3.9 dentro da imagem.
   - Subir com `docker run -d --name ciframe-e2e -p 8080:8080 -v ciframe-db:/app/db ciframe`;
     cadastrar uma sequência via `POST /sequencias`, confirmar em
     `GET /sequencias` e buscar por ela em `/similares`.
   - `docker rm -f ciframe-e2e`; subir de novo com o mesmo volume e confirmar que
     a sequência continua no catálogo.
   - Rodar a suíte dentro do container:
     `docker run --rm -e SEQUENCIAS_DB_PATH=/tmp/test.db ciframe python -m unittest discover -s tests -v`.
   - **Verificação:** build e suíte passam no Python 3.9; a sequência sobrevive ao
     `docker rm` com o mesmo volume.

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `main.py` | Resolver `/similares` pelo catálogo; adicionar `GET/POST /sequencias`; usar matcher e cifra pré-processada; remover leitura da tag na busca; serializar explicitamente `/musica/<id>/` e `/musicas`. |
| `musica.py` | Expor `cifra_minuscula`/`acordes_minusculos` calculados uma vez no carregamento. |
| `(novo) matching.py` | Função pura de normalização e matching; sem Flask/banco. |
| `(novo) sequencias_db.py` | Conexão SQLite, schema, seed idempotente e operações do catálogo. |
| `(novo) tests/test_sequence_regression.py` | Regressão das 6 sequências contra as tags, agregando todas as páginas. |
| `(novo) tests/test_matching.py` | Casos unitários do matcher. |
| `(novo) tests/test_sequencias_db.py` | Schema, seed, persistência e duplicata com banco temporário. |
| `(novo) tests/test_similares_catalogo.py` | Equivalência canônica/normalizada de `/similares?sequencia=...`. |
| `(novo) tests/isolamento_db.py` | Aponta `SEQUENCIAS_DB_PATH` para diretório temporário antes de importar `main`. |
| `(novo) tests/test_sequencias_api.py` | Contratos e validação de `GET/POST /sequencias` e `/similares`. |
| `(novo) tests/test_endpoints_legados.py` | Contrato de `GET /musica/<id>/` e `GET /musicas`; impede vazamento do pré-processamento. |
| `static/assets/js/controllers/sequencia.js` | Catálogo dinâmico e envio do cadastro; remoção dos 4 hardcoded. |
| `static/templates/sequencia.html` | Formulário de cadastro e renderização de `acordes` como strings. |
| `.gitignore` / `.dockerignore` | Ignorar `db/`. |
| `README.md` / `AGENTS.md` | Remover “sem banco”; documentar SQLite, env var e volume. |
| `Dockerfile` | Sem alteração de conteúdo; o volume é fornecido via `-v` no `docker run`. |
| `data/mapeamento_sequencias_famosas.txt` | Somente leitura no seed; sem alteração. |

## Riscos e mitigação

- **Ordem de `generos` varia por processo.** `main.py:92` faz
  `generos = list(generos)` a partir de um `set`; com `PYTHONHASHSEED=1` a primeira
  página de `/similares?sequencia=Bm,G,D,A` começou com
  `capital-inicial_a-sua-maneira`, `u2_with-or-without-you-live-elevation-tour`,
  `one-republic_if-i-lose-myself`; com `PYTHONHASHSEED=2` começou com
  `darvin_fica-pronto-pra-mim`, `projota_a-rezadeira`, `projota_deixa-rolar`.
  O conjunto completo é o mesmo: 199 ids sem gênero e 5 com Rock, com o mesmo
  digest nas duas seeds. **Mitigação:** a regressão agrega todas as páginas e
  compara `set`; nunca compara a página 1 nem a ordem.
- **Pré-processamento não pode vazar para endpoints que serializam `__dict__`.**
  `GET /musica/<id>/` e `GET /musicas` serializavam `Musica.__dict__`; campos como
  `acordes_minusculos` (set) quebram o `json.dumps` e campos novos mudariam o
  contrato. Mitigação: serializador explícito com os 12 campos originais e teste
  `tests/test_endpoints_legados.py`.
- **Quebra de compatibilidade do `/similares`.** A busca passa a aceitar
  minúsculas/espaços e deixa de usar a tag; é uma mudança intencional. Mitigação:
  teste de equivalência canônica/normalizada e documentação no passo 7.
- **Matcher estrito pode excluir músicas com acordes extras.** É o comportamento
  decidido. Mitigação: a regressão prova que as 6 originais continuam com os
  mesmos conjuntos; o custo fica documentado na proposta.
- **Seed duplicado ou banco parcial.** Mitigação: `INSERT OR IGNORE` pela
  `chave_unica`, teste de duas inicializações e teste com banco temporário.
- **Volume ausente perde o catálogo após `docker rm`.** Mitigação: documentar e
  validar no passo 8 com `-v ciframe-db:/app/db`; `db/` no `.dockerignore` mantém
  o banco de runtime fora da imagem, e o volume é o que o preserva.
- **Latência sem cache.** Medição local: ~0,49–0,55 s de média e máximo de
  ~0,64 s sem filtro; aceitável para uso local single-user, mas não para alta
  concorrência. Mitigação: manter sem cache nesta feature e confirmar no Python
  3.9 do container.
- **Diferença entre Python 3.14 local e 3.9 do container.** Mitigação: a suíte e o
  E2E do passo 8 rodam dentro da imagem Python 3.9.
- **Frontend legado sem build.** Mitigação: mudanças pequenas em `sequencia.js` e
  `sequencia.html`, validação manual no navegador e testes de API cobrindo o
  contrato.

## Definição de pronto

- [ ] Cadastro de sequência funciona pela API e pelo formulário em
      `#/porsequencia`.
- [ ] Busca por sequência cadastrada funciona, inclusive com minúsculas/espaços, e
      retorna o mesmo contrato de `/similares`.
- [ ] As 6 sequências originais continuam funcionando como antes: a regressão
      compara o conjunto completo de `id_unico_musica` de todas as páginas, sem
      gênero e com pelo menos um gênero, contra as tags.
- [ ] As 6 originais são semeadas de forma idempotente e não duplicam ao reiniciar.
- [ ] `GET /sequencias` e `POST /sequencias` têm testes de validação e duplicata.
- [ ] O frontend lista as 6 originais + novas e permite cadastrar sem build novo.
- [ ] `db/` está ignorado por Git e Docker; README e AGENTS documentam SQLite,
      `SEQUENCIAS_DB_PATH` e o volume nomeado.
- [ ] A suíte completa passa dentro do container Python 3.9.
- [ ] A persistência é confirmada após `docker rm`: subir de novo com o mesmo
      volume `ciframe-db` mantém a sequência cadastrada.
