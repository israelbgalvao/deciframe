def normalizar_sequencia(sequencia):
    if isinstance(sequencia, str):
        tokens = sequencia.split(',')
    else:
        tokens = sequencia

    normalizada = []
    for token in tokens:
        token = ''.join(str(token).split()).lower()
        if token:
            normalizada.append(token)
    return normalizada


def casa_sequencia(sequencia_normalizada, cifra_minuscula, acordes_minusculos):
    if not sequencia_normalizada:
        return False

    tamanho = len(sequencia_normalizada)
    contigua = any(
        cifra_minuscula[i:i + tamanho] == sequencia_normalizada
        for i in range(len(cifra_minuscula) - tamanho + 1)
    )
    if not contigua:
        return False

    return acordes_minusculos.issubset(set(sequencia_normalizada))
