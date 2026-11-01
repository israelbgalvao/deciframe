# deciframe

Descubra as músicas que você já sabe tocar (e ainda não faz ideia). Busque por
título/artista, gênero, pelos acordes que você já manja, ou por sequências de
acordes famosas — o deciframe cruza isso com uma base de cifras e sugere
músicas parecidas.

Stack: backend Flask (Python) servindo uma API JSON + um frontend AngularJS
estático. As músicas e os gêneros continuam sendo carregados de um CSV em
memória; o catálogo de sequências de acordes fica em um banco SQLite local
(`db/sequencias.db` por padrão), configurável pela variável
`SEQUENCIAS_DB_PATH`.

## Rodando localmente

### Com Docker

```
docker build -t ciframe .
docker run -p 8080:8080 -v ciframe-db:/app/db ciframe
```

Acesse [http://localhost:8080](http://localhost:8080).

O volume nomeado `ciframe-db` preserva o catálogo de sequências quando o
container é recriado.

### Com virtualenv

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Acesse [http://localhost:5000](http://localhost:5000).

O caminho do banco pode ser alterado com `SEQUENCIAS_DB_PATH`, por exemplo:

```
SEQUENCIAS_DB_PATH=/tmp/ciframe.db python main.py
```

### Testes

```
python -m unittest discover -s tests -v
```

A busca por sequência (`/similares?sequencia=`) aceita acordes em minúsculas e
com espaços, por exemplo `Bm, G, D, A`.

---

Para convenções de contribuição, veja [CONTRIB.md](CONTRIB.md). Licença: [LICENSE](LICENSE).
