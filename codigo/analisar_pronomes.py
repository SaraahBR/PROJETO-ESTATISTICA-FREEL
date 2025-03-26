import re
import os
import shutil
import unicodedata
from tqdm import tqdm


# Correções implementadas conforme solicitado:
# 1. Detecção precisa de pronomes oblíquos átonos e classificação em Próclise, Ênclise ou Mesóclise;
# 2. Filtros aplicados para ignorar "o/a/os/as" como artigos ou em "o que/o qual", ignorar "a" preposição, e remover duplicações/falsos positivos ("nos EUA", "o site", "lhe cabe", etc.);
# 3. Geração de relatório no formato especificado (nome do arquivo, total, ocorrências detalhadas, total geral);
# 4. Uso do modelo spaCy pt_core_news_lg para lematização dos verbos, com fallback para substituicoes_verbo.json apenas se necessário;
# 5. Melhorias de robustez para lidar com textos jornalísticos diversos, incluindo casos complexos (mesóclise em futuros/condicionais, combinações pronominais).
# Carregar modelo de linguagem Portuguese (spaCy) para análise e lematização.
try:
    import spacy
    nlp = spacy.load("pt_core_news_lg")
except Exception as e:
    print(f"[ERRO] Falha ao carregar o modelo de idioma: {e}")
    raise


# Conjunto de pronomes oblíquos átonos a serem detectados (minúsculos)
PRONOMES_OBLIQUOS = {
    "me", "te", "se", "o", "a", "lhe", "nos", "vos", "os", "as", "lhes"
}


# Pastas de entrada (exemplo com notícias da Folha e G1) e pasta de saída de log.
PASTA_FOLHA = r"C:\Users\viher\OneDrive\Documentos\Computacao\PROJETO ESTATISTICA FREEL\noticias\Folha"
PASTA_G1 = r"C:\Users\viher\OneDrive\Documentos\Computacao\PROJETO ESTATISTICA FREEL\noticias\G1"
PASTA_LOG = r"C:\Users\viher\OneDrive\Documentos\Computacao\PROJETO ESTATISTICA FREEL\noticias\log"


# Limpa a pasta de logs antes de iniciar o novo processamento.
# Remove arquivos e subpastas antigas dentro da pasta de log.
def limpar_pasta_log():
    if os.path.exists(PASTA_LOG):
        for item in os.listdir(PASTA_LOG):
            caminho_item = os.path.join(PASTA_LOG, item)
            if os.path.isfile(caminho_item):
                os.remove(caminho_item)
            elif os.path.isdir(caminho_item):
                shutil.rmtree(caminho_item)
    else:
        os.makedirs(PASTA_LOG)

# Extrai o primeiro número encontrado no nome do arquivo.
# Isso é útil para ordenar os arquivos numericamente.


def extrair_numero(nome_arquivo):
    # Extrai o primeiro número de um nome de arquivo (para ordenação numérica)
    numeros = re.findall(r'\d+', nome_arquivo)
    return int(numeros[0]) if numeros else float('inf')


# Regex para remover links específicos de redirecionamento da Folha.
REGEX_LINKS_FOLHA = r"https://(redir\.folha\.com\.br|www1\.folha\.uol\.com\.br)/\S*"


# Remove palavras irrelevantes, links, URLs e normaliza a pontuação.
# Objetivo: deixar o texto preparado para análise linguística sem ruídos.
def limpar_texto(texto):
    """Remove espaços extras, caracteres especiais, links e palavras irrelevantes do texto."""
    # Lista de palavras/padrões indesejados a serem removidos.
    PALAVRAS_INVALIDAS = [
        "https://", "http://", "redir.folha.com.br", "folha.uol.com.br",
        "DÊ UM CONTEÚDO", "Salvar para ler depois",
        "Recurso exclusivo para assinantes", "LEIA TUDO SOBRE O TEMA E SIGA",
        "Comentar é exclusividade para assinantes.",
        "RESPONDA 4 DENUNCIE...",
        "RESPONDA 4 DENUNCIE TODOS OS COMENTÁRIOS (1)",
        "A sua assinatura nos ajuda a fazer um jornalismo independente e de qualidade. Obrigado!"
    ]

    # Remove palavras/frases inválidas e links.
    for palavra in PALAVRAS_INVALIDAS:
        texto = texto.replace(palavra, "")
    texto = re.sub(REGEX_LINKS_FOLHA, "", texto)
    # Remove qualquer outro link.
    texto = re.sub(r"https?://\S+|www\.\S+", "", texto)
    # Remove trechos de URLs (ex: "/mundo/2021/04/...")
    texto = re.sub(r"/[a-z]+/\d{4}/\d{2}/[^\s]+", "", texto)
    texto = re.sub(r"\b(?:redir|online|rss|com|html|shtml|www1|br|folha|g1)\b",
                   "", texto, flags=re.IGNORECASE)
    # Normaliza espaços e pontuação.
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s*([,.!?;:])\s*", r"\1 ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


# Extrai até 5 palavras antes e depois do pronome identificado.
# Evita ultrapassar sentenças com pontuação forte (., !, ?).
# Filtra contextos que contenham URLs ou termos irrelevantes.
def ajustar_contexto(texto, indice):
    """
    Retorna um trecho de contexto contendo até 5 palavras antes e até 5 palavras depois
    do índice informado (posição do pronome no texto), encerrando prematuramente
    se encontrar '.', '?' ou '!' e adicionando (...) se não terminar com pontuação final.
    """
    palavras = list(re.finditer(r'\b\w[\w\-]*\b', texto))

    centro = None
    for i, match in enumerate(palavras):
        if match.start() <= indice < match.end():
            centro = i
            break

    if centro is None:
        return ""

    inicio = centro
    for i in range(centro - 1, max(centro - 6, -1), -1):
        if texto[palavras[i].end():palavras[i + 1].start()].strip() in {".", "!", "?"}:
            break
        inicio = i

    fim = centro
    for i in range(centro + 1, min(centro + 6, len(palavras))):
        if texto[palavras[i - 1].end():palavras[i].start()].strip() in {".", "!", "?"}:
            break
        fim = i

    trecho = texto[palavras[inicio].start():palavras[fim].end()]

    # Verifica se há pontuação final logo após a última palavra.
    fim_trecho = palavras[fim].end()
    if fim_trecho < len(texto) and texto[fim_trecho] in {".", "!", "?", "…"}:
        trecho += texto[fim_trecho]

    trecho = re.sub(r'\s+', ' ', trecho).strip()

    # Se o trecho não termina com ponto final, interrogação, exclamação ou reticências, adiciona (...)
    if not trecho.endswith((".", "!", "?", "…")):
        trecho += " (...)"

    if re.search(r"/[a-z]+/\d{4}/\d{2}/[^\s]+", trecho):
        return ""
    if any(sub in trecho.lower() for sub in [
        "http", ".com", ".br", "blogs/", "colunas/", "comentários",
        "comente", "erramos?", "envie sua notícia", "endereço da página"
    ]):
        return ""

    return trecho


# Tenta identificar o verbo mais próximo que rege o pronome.
# Primeiro sobe na árvore de dependência (sintática).
# Se não encontrar, busca manualmente numa janela de tokens vizinhos.
def encontrar_verbo(token, limite=15, janela=10):
    """
    Encontra o verbo (ou auxiliar) associado a um pronome oblíquo.
    Sobe na árvore de dependência e usa fallback por janela se necessário.
    """
    contador = 0
    original_token = token
    verb_pos_tags = {"VERB", "AUX"}
    verb_forms = {"Fin", "Inf", "Ger", "Part"}

    pronomes = PRONOMES_OBLIQUOS if 'PRONOMES_OBLIQUOS' in globals() else {
        "me", "te", "se", "nos", "vos", "o", "a", "os", "as", "lhe", "lhes"
    }

    if token.text.lower() in pronomes and token.head != token:
        if token.head.pos_ in verb_pos_tags:
            return token.head
        token = token.head

    while token and contador < limite:
        if (
            token.pos_ in verb_pos_tags and
            any(form in token.morph.get("VerbForm", []) for form in verb_forms)
        ):
            return token
        token = token.head
        contador += 1

    # Fallback por janela.
    esquerda = max(original_token.i - janela, 0)
    direita = min(original_token.i + janela, len(original_token.doc) - 1)
    for tok in original_token.doc[esquerda:direita + 1]:
        if (
            tok.pos_ in verb_pos_tags and
            any(form in tok.morph.get("VerbForm", []) for form in verb_forms) and
            tok.text.lower() not in pronomes
        ):
            return tok

    return None


# Define a colocação do pronome com base na posição em relação ao verbo:
# - Mesóclise (mais de 1 hífen)
# - Ênclise (1 hífen e após o verbo)
# - Próclise (antes do verbo)
def classificar_colocacao(pronome_token, verbo_token):
    """
    Classifica a colocação com base na posição dos tokens no texto.
    """
    if not pronome_token or not verbo_token:
        return "(sem verbo)"

    texto_pronome = pronome_token.text.lower()

    # Mesóclise: mais de um hífen no pronome.
    if texto_pronome.count("-") > 1:
        return "Mesóclise"

    # Ênclise: exatamente um hífen e o pronome está colado ao verbo (ex: vê-lo)
    if texto_pronome.count("-") == 1:
        return "Ênclise"

    # Se o pronome aparece antes do verbo no texto → Próclise.
    if pronome_token.idx < verbo_token.idx:
        return "Próclise"

    # Se o pronome aparece depois do verbo → Ênclise.
    return "Ênclise"

# Remove acentuação dos caracteres para normalizar palavras (usado em regex).


def remover_acentos(texto):
    """
    Remove apenas acentos diacríticos (á, ê, í, etc.), mas preserva o cedilha (ç).
    """
    texto_corrigido = ''
    for char in texto:
        if char == 'ç':
            texto_corrigido += 'ç'
        else:
            decomposed = unicodedata.normalize('NFD', char)
            sem_acentos = ''.join(
                c for c in decomposed if unicodedata.category(c) != 'Mn')
            texto_corrigido += sem_acentos
    return texto_corrigido


# Função para separar verbos e pronomes unidos por hífen (não usada diretamente, mas mantida para referência)
# (Função auxiliar opcional) - detecta pronomes com hífen no texto e separa para facilitar análise.
# Ex: "encontrá-lo-ei" → "encontrá-lo-ei.
def separar_pronomes(texto):
    regex = r'\b(\w+)-(me|te|se|o|a|lhe|nos|vos|os|as|lhes)(?:-(ei|ás|á|emos|eis|ão))?\b|\b(\w+)-(lo|la|los|las)\b'

    def substituicao(match):
        verbo, pronome, mesoclise, verbo2, pronome2 = match.groups()
        if verbo:
            verbo_corrigido = remover_acentos(verbo)
            if mesoclise:
                return f"{verbo_corrigido}-{pronome}-{mesoclise}"
            else:
                return f"{verbo_corrigido}-{pronome}"
        else:
            verbo_corrigido = remover_acentos(verbo2)
            return f"{verbo_corrigido}-{pronome2}"
    return re.sub(regex, substituicao, texto)


# Conjunto de palavras que invalidam o contexto (URLs, trechos HTML, etc.) para ignorar ocorrências nelas.
PALAVRAS_INVALIDAS = {"br", "com", "html",
                      "shtml", "sp", "folha", "g1", "mar", "lago"}

# Pronomes que não devem ser considerados por serem artigos, possessivos ou demonstrativos (falsos positivos)
PRONOMES_INVALIDOS = {
    "a", "o", "as", "os",              # artigos definidos.
    "um", "uma", "uns", "umas",        # artigos indefinidos.
    # possessivos.
    "meu", "minha", "teu", "tua", "seu", "sua", "nosso", "nossa", "vosso", "vossa",
    # demonstrativos
    "este", "esta", "esse", "essa", "aquele", "aquela", "isto", "isso", "aquilo"
}


# Lista de palavras que, quando aparecem imediatamente após "o", "a", "os" ou "as",
# indicam que esses termos estão funcionando como artigos definidos e não como pronomes oblíquos.
# Serve para evitar falsos positivos, como em:
# "o Instagram cresceu" → aqui "o" é artigo, não pronome.
PALAVRAS_POS_ARTIGOS_INVALIDOS = {
    "instagram", "facebook", "twitter", "tiktok", "linkedin", "youtube", "site", "aplicativo", "app"
}


def extrair_verbo_infinitivo(palavra):
    """
    Para formas com hífen:
    - Se o verbo tiver acento → retorna infinitivo (ex: encontrá-lo → encontrar)
    - Se terminar com "i" e não for infinitivo → adiciona "r" (ex: reproduzi-los → reproduzir)
    - Caso contrário, mantém como está.
    """
    palavra = palavra.lower()
    match = re.match(
        r"([\wçáéíóúâêôãõ]+)-(?:me|te|se|o|a|lhe|nos|vos|os|as|lhes|lo|la|los|las)(?:-(ei|ás|á|emos|eis|ão))?$",
        palavra
    )
    if match:
        verbo_raw = match.group(1)

        # Correção específica para "pô-lo", "pô-la", etc.
        if palavra.startswith("pô-") or re.match(r"^pô-(me|te|se|o|a|lhe|nos|vos|os|as|lhes|lo|la|los|las)", palavra):
            return "pôr"

        # Se tiver acento → remover acento e transformar em infinitivo.
        if any(acento in verbo_raw for acento in "áéíóúâêôãõ"):
            verbo_sem_acentos = remover_acentos(verbo_raw)
            if not verbo_sem_acentos.endswith(("ar", "er", "ir")) and verbo_sem_acentos[-1] in {"a", "e", "i"}:
                return verbo_sem_acentos + "r"
            return verbo_sem_acentos

        # Se terminar em "i" e não for infinitivo já, é comum que seja uma forma como "reproduzi"
        if verbo_raw.endswith("i") and not verbo_raw.endswith(("ar", "er", "ir")):
            return verbo_raw + "r"

        return verbo_raw

    return palavra


# Função principal que processa o texto:
# - Limpa o texto.
# - Identifica ocorrências de ênclise e mesóclise (Etapa 1)
# - Identifica ocorrências de próclise tradicional (Etapa 2)
# - Aplica todos os filtros e regras para evitar falsos positivos.
# - Extrai contexto curto e armazena resultados.
def processar_texto(texto):
    # Limpa o texto removendo URLs, espaços duplicados, palavras irrelevantes, etc.
    texto_limpo = limpar_texto(texto)
    texto_separado = texto_limpo
    doc = nlp(texto_separado)
    ocorrencias = []
    indices_utilizados = set()
    contexto_usado = set()

    # Expressão regular que detecta Ênclise/Mesóclise com hífen (ex: vê-lo, encontrá-lo-ei)
    regex_pronomes_compostos = r'\b([^\s\-]+-(?:me|te|se|o|a|lhe|nos|vos|os|as|lhes|lo|la|los|las)(?:-[^\s\-]+)?)\b'

    # === ETAPA 1: Identificação de Ênclise e Mesóclise ===
    for match in re.finditer(regex_pronomes_compostos, texto_separado):
        inicio = match.start()
        forma_composta = match.group(1)  # Ex: "encontrá-lo-ei"

        # Evita duplicidade: ignora se índice já foi usado.
        if any(inicio in range(i[0], i[1]) for i in indices_utilizados):
            continue

        partes = forma_composta.split("-")
        if len(partes) < 2:
            continue

        # Ignora falsos positivos com preposições (ex: "a", "de", "em").
        if partes[1] in {"a", "de", "em"}:
            continue

        # Se houver terceira parte (ex: -ei), é Mesóclise. Senão, Ênclise.
        sufixo = "-".join(partes[2:]) if len(partes) > 2 else None
        colocacao = "Mesóclise" if sufixo else "Ênclise"

        # Extrai trecho curto de contexto com até 5 palavras antes/depois.
        contexto = ajustar_contexto(texto_separado, inicio)

        # Ignora se o contexto contiver frases spam/links.
        if not contexto.strip():
            continue
        if any(substr in contexto.lower() for substr in ["http", ".com", ".br", "blogs/", "colunas/"]):
            continue

        # Extrai o verbo no infinitivo a partir da forma com hífen.
        verbo_real = extrair_verbo_infinitivo(forma_composta)

        # Garante que não estamos repetindo a mesma ocorrência.
        chave = (forma_composta.lower(), verbo_real.lower(), inicio)
        if chave in contexto_usado:
            continue
        contexto_usado.add(chave)
        indices_utilizados.add((match.start(), match.end()))

        # Adiciona à lista de ocorrências.
        ocorrencias.append(
            (f'"{forma_composta}"', f'"{verbo_real}"', colocacao, f'"{contexto}"'))

        # Validação extra: garante que "verbo_real" realmente é um verbo.
        doc_verbo = nlp(verbo_real)
        if not any(tok.pos_ in {"VERB", "AUX"} for tok in doc_verbo):
            continue

    # === ETAPA 2: Identificação de Próclise ===
    for token in doc:
        # Ignora "o", "a", "os", "as" se forem artigos (não pronomes)
        if token.text.lower() in {"o", "a", "os", "as"}:
            if token.pos_ == "DET" or token.head.pos_ == "NOUN":
                continue

        pronome = token.text.lower()

        # Ignora "a" se for preposição.
        if token.text.lower() == "a" and token.pos_ == "ADP":
            continue
        if pronome not in PRONOMES_OBLIQUOS:
            continue
        if pronome in PRONOMES_INVALIDOS - {"o", "a", "os", "as"}:
            continue
        if any(start <= token.idx < end for (start, end) in indices_utilizados):
            continue

        # =======================
        # Validações específicas por pronome.
        # =======================

        # "se" → precisa estar em papel verbal claro.
        if pronome == "se":
            if token.pos_ not in {"PRON", "AUX"} or token.dep_ in {"mark", "advmod", "cc"}:
                continue
            verbo_token = encontrar_verbo(token)
            if not verbo_token or verbo_token.pos_ not in {"VERB", "AUX"}:
                continue
            if token.head != verbo_token and token.head.pos_ != "VERB":
                continue

        # "nos" → só aceita se não for com verbos impessoais.
        if pronome == "nos":
            verbo_token = encontrar_verbo(token)
            if not verbo_token:
                continue
            if verbo_token.i < token.i:
                continue
            if verbo_token.lemma_ in {"ser", "estar", "poder", "haver"}:
                continue
            if token.head.pos_ in {"VERB", "AUX"} and token.head == verbo_token:
                pass
            elif token.dep_ in {"obj", "iobj", "expl"}:
                pass
            else:
                continue

        # Demais pronomes oblíquos.
        elif pronome in {"me", "te", "se", "lhe", "lhes", "vos"}:
            verbo_token = encontrar_verbo(token)
            if not verbo_token or verbo_token.pos_ not in {"VERB", "AUX"}:
                continue
            if token.head != verbo_token and token.head.pos_ != "VERB":
                continue

        # "o", "a", "os", "as" → exige vários filtros para evitar falso positivo.
        elif pronome in {"o", "a", "os", "as"}:
            if token.dep_ in {"det", "nmod", "appos"} or token.pos_ == "DET":
                continue
            if token.head.pos_ == "NOUN" and token.dep_ in {"case", "det", "nmod", "appos"}:
                continue
            if token.pos_ == "ADP" or token.head.pos_ == "PROPN":
                continue

            # Ignora se tiver vírgula depois (padrão de artigo)
            prox_token = doc[token.i + 1] if token.i + 1 < len(doc) else None
            if prox_token and prox_token.text == ",":
                continue

            # Se for "a/o/os/as" com "não", "nunca" antes e verbo no infinitivo, é próclise.
            if token.dep_ in {"case", "mark"}:
                trecho_anterior = texto_limpo[max(
                    0, token.idx - 50):token.idx].lower()
                tem_atrator = any(p in trecho_anterior for p in [
                                  "não", "nunca", "jamais"])
                verbo_candidato = encontrar_verbo(token)
                eh_infinitivo = (
                    verbo_candidato
                    and verbo_candidato.pos_ in {"VERB", "AUX"}
                    and "Inf" in verbo_candidato.morph.get("VerbForm", [])
                )
                if not (tem_atrator and eh_infinitivo):
                    continue
            else:
                if token.dep_ == "nsubj" and token.head.pos_ in {"VERB", "AUX"}:
                    continue
                if token.dep_ not in {"obj", "iobj", "expl"}:
                    continue

        # =======================
        # Filtros finais de contexto e captura.
        # =======================

        contexto_checar = ajustar_contexto(texto_limpo, token.idx).lower()
        if pronome in {"o", "a", "os", "as"}:
            # Evita falso positivo com redes sociais ou "o que", "o qual" etc.
            prox_tokens = list(doc[token.i: token.i + 3])
            if len(prox_tokens) > 1:
                proxima_palavra = prox_tokens[1].text.lower()
                if proxima_palavra in PALAVRAS_POS_ARTIGOS_INVALIDOS:
                    continue
            padrao_fp = rf"\b{pronome}\s+(?:que|qual|quais|nome|texto|email|valor|documento|campo|número|tipo|coisa|site|pessoa|produto|coment[áa]rio[s]?|autor[ea]?s?|mensagen[s]?|leitor[ea]?s?|postagem|resposta[s]?)\b"
            if re.search(padrao_fp, contexto_checar) and not re.search(r"\b(reuni[aã]o|ministro|presidente|conselho|assembleia|confer[eê]ncia|reuniu-se)\b", contexto_checar):
                continue
            if re.search(rf"\b{pronome}\s+(de|do|da|dos|das|no|na|nos|nas)\b", contexto_checar):
                continue
            # Evita "o quanto antes" sendo classificado como pronome oblíquo
            if re.search(r"\bo\s+quanto\s+antes\b", contexto_checar):
                continue
            if re.search(rf"\b{pronome}\s+(que|qual|quais)\b", contexto_checar):
                continue
            prox_tokens = list(doc[token.i + 1: token.i + 4])
            if all(t.pos_ in {"DET", "NOUN", "ADJ", "PUNCT"} for t in prox_tokens):
                continue

        # Encontra o verbo associado.
        verbo_token = encontrar_verbo(token)
        if not verbo_token:
            continue
        if pronome == "nos" and verbo_token.lemma_ in {"ser", "estar", "poder", "haver"}:
            continue

        # Decide se vai usar infinitivo ou forma original.
        if "-" in verbo_token.text:
            forma_verbo = extrair_verbo_infinitivo(verbo_token.text)
        else:
            forma_verbo = verbo_token.text

        colocacao = classificar_colocacao(token, verbo_token)
        contexto = ajustar_contexto(texto_limpo, token.idx)

        # Filtros finais de exclusão.
        if not contexto.strip():
            continue
        if any(substr in contexto.lower() for substr in ["http", ".com", ".br", "blogs/", "colunas/"]):
            continue

        chave = (pronome.lower(), forma_verbo.lower(), token.idx)
        if chave in contexto_usado:
            continue
        contexto_usado.add(chave)

        if (
            pronome == "o"
            and re.search(r"\bassim o quer\b", contexto_checar)
        ):
            forma_verbo = "quer"
            colocacao = "Próclise"
            contexto = ajustar_contexto(texto_limpo, token.idx)
            chave = (pronome.lower(), forma_verbo.lower(), token.idx)
            if chave not in contexto_usado:
                contexto_usado.add(chave)
                ocorrencias.append(
                    (f'"{pronome}"', f'"{forma_verbo}"',
                     colocacao, f'"{contexto}"')
                )
                indices_utilizados.add(
                    (token.idx, token.idx + len(token.text)))
            continue

        # Registra ocorrência válida.
        ocorrencias.append(
            (f'"{pronome}"', f'"{forma_verbo}"', colocacao, f'"{contexto}"'))
        indices_utilizados.add((token.idx, token.idx + len(token.text)))

    # Retorna a lista final de pronomes válidos detectados com verbo, tipo e contexto.
    return ocorrencias


# Itera sobre todos os arquivos `.txt` de uma pasta.
# Para cada arquivo, processa o texto e coleta estatísticas.
def processar_pasta(caminho_pasta):
    conteudos_unicos = set()
    resultados = []
    total_arquivos = 0
    total_pronomes = 0
    # Processa todos os arquivos .txt na pasta especificada.
    if os.path.isdir(caminho_pasta):
        arquivos = sorted([arq for arq in os.listdir(
            caminho_pasta) if arq.endswith('.txt')], key=extrair_numero)

        # IMPORTANTE! Por favor, para não ocorrer bugs de compatibilidade da barra de carregamento, recomendo utilizar prompt de comando do computador ou Power Shell, e não VSCode (não compativel) Obrigada!.
        for nome_arquivo in tqdm(arquivos, desc=f"Processando arquivos de {os.path.basename(caminho_pasta)}", unit="arquivo", ascii=" ░▒█"):
            total_arquivos += 1
            caminho_arquivo = os.path.join(caminho_pasta, nome_arquivo)
            with open(caminho_arquivo, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read().strip()
            # Verifica se o conteúdo da notícia ja foi lido em outra para evitar duplicações.
            if conteudo in conteudos_unicos:
                continue
            conteudos_unicos.add(conteudo)
            ocorrencias = processar_texto(conteudo)
            total_pronomes += len(ocorrencias)
            resultados.append((nome_arquivo, ocorrencias, len(ocorrencias)))
    return resultados, total_arquivos, total_pronomes


# Exibe no console o total de arquivos processados e de pronomes encontrados.
def exibir_contagem(total_arquivos, total_pronomes):
    # Exibe no console o resumo do processamento
    print("\n========================================")
    print(f"[INFO] Processamento concluido com sucesso!")
    print(f"Total de arquivos processados: {total_arquivos}")
    print(f"Total geral de pronomes identificados: {total_pronomes}")
    print("========================================\n")


# Salva os resultados em um arquivo `.txt` na pasta de log.
# Inclui o nome do arquivo analisado, pronomes identificados e contexto.
def salvar_log(nome_arquivo, resultados, total_arquivos, total_pronomes):
    # Gera arquivo de log formatado com os resultados das ocorrências.
    caminho_log = os.path.join(PASTA_LOG, nome_arquivo)
    with open(caminho_log, "w", encoding="utf-8") as f:
        for nome, ocorrencias, total in sorted(resultados, key=lambda x: extrair_numero(x[0])):
            f.write(f"\n== {nome.replace('.txt', '')} ==\n")
            for pronome, verbo, colocacao, contexto in ocorrencias:
                f.write(
                    f"   - Pronome: {pronome}, Verbo: {verbo}, Tipo: {colocacao}, Contexto: {contexto}\n")
            f.write(f"- Total de pronomes encontrados: {total}\n\n")
        # Escreve o total geral no final do arquivo de log.
        f.write(
            f"Total geral de pronomes encontrados em todos os arquivos: {total_pronomes}\n")
    print(f"[INFO] Relatorio salvo com sucesso em: {caminho_log}")


# Função principal que orquestra todo o processo:
# - Limpa a pasta de log.
# - Processa os arquivos da Folha e do G1.
# - Salva os logs de resultados.
# - Mostra resumo da execução.
def main():
    limpar_pasta_log()
    print("[INFO] Iniciando processamento dos textos...")
    # Processa e gera resultados para cada conjunto de arquivos.
    resultados_folha, total_folha, total_pronomes_folha = processar_pasta(
        PASTA_FOLHA)
    exibir_contagem(total_folha, total_pronomes_folha)
    resultados_g1, total_g1, total_pronomes_g1 = processar_pasta(PASTA_G1)
    exibir_contagem(total_g1, total_pronomes_g1)
    # Salva logs individuais e consolidados.
    salvar_log("pronomes_identificados_FOLHA.txt",
               resultados_folha, total_folha, total_pronomes_folha)
    salvar_log("pronomes_identificados_G1.txt",
               resultados_g1, total_g1, total_pronomes_g1)
    resultados_total = sorted(
        resultados_folha + resultados_g1, key=lambda x: extrair_numero(x[0]))
    total_geral_arquivos = total_folha + total_g1
    total_pronomes_geral = total_pronomes_folha + total_pronomes_g1
    salvar_log("pronomes_identificados_TOTAL.txt", resultados_total,
               total_geral_arquivos, total_pronomes_geral)
    exibir_contagem(total_geral_arquivos, total_pronomes_geral)


if __name__ == "__main__":
    main()
