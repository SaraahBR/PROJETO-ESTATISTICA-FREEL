# 🧠 Analisador de Pronomes Oblíquos Átonos em Textos Jornalísticos (Português)

Este projeto foi desenvolvido como parte de um trabalho freelance acadêmico para apoiar uma pesquisa de doutorado em linguística na Universidade Estadual de Londrina (UEL). O objetivo principal é identificar, classificar e registrar automaticamente o uso de pronomes oblíquos átonos em textos jornalísticos reais, como os da *Folha de S.Paulo* e do *G1*.

## 📌 Objetivo

Detectar com alta precisão a presença de pronomes oblíquos átonos nas construções verbais e classificá-los corretamente como:

- **Próclise** (antes do verbo)  
- **Ênclise** (após o verbo com hífen)  
- **Mesóclise** (no meio do verbo com dois hífens)

## 🛠️ Tecnologias e Ferramentas Utilizadas

- Python 3.11  
- [spaCy](https://spacy.io) com o modelo `pt_core_news_lg` para análise sintática e morfológica  
- Expressões regulares (regex)  
- Geração de relatórios automatizados `.txt`  
- Dicionários personalizados `.json` para:  
  - Substituições de lematização  
  - Palavras compostas com hífen  
  - Contextos inválidos  

## 🧠 Principais Funcionalidades

- ✔️ Detecção de pronomes oblíquos átonos em textos de forma automatizada  
- ✔️ Classificação da colocação pronominal (**próclise**, **ênclise**, **mesóclise**)  
- ✔️ Geração de logs detalhados com:
  - Arquivo analisado  
  - Pronome identificado  
  - Verbo associado  
  - Tipo de colocação  
  - Contexto enxuto da ocorrência  
- ✔️ Filtros avançados para evitar falsos positivos, incluindo:
  - Artigos definidos (ex: “o carro”, “a casa”)  
  - Preposições com “a” (ex: “entregou a ela”)  
  - Pronomes isolados sem contexto verbal claro  
  - Expressões ambíguas ou indesejadas  
- ✔️ Leitura de exceções via `.json` para fácil manutenção e expansão

## 🗂️ Estrutura de Pastas

```
/codigo/             # Scripts principais em Python  
/noticias/           # Textos jornalísticos utilizados  
├── Folha/           # Textos da Folha de S.Paulo  
├── G1/              # Textos do G1  
/log/                # Relatórios gerados automaticamente  
```

## 🔍 Exemplo de Saída no Relatório

```
== noticia_exemplo123 ==
 - Pronome: "se", Verbo: "aproximar", Tipo: Próclise, Contexto: "busca se aproximar de uma literatura produzida"
 - Pronome: "vê-las", Verbo: "ver", Tipo: Ênclise, Contexto: "Quero vê-las antes do evento."
 - Pronome: "Encontrá-lo-ei", Verbo: "encontrar", Tipo: Mesóclise, Contexto: "Encontrá-lo-ei algum dia entre as estrelas."
Total de pronomes encontrados: 3
```

## 🚀 Como Executar

Instale os requisitos (incluindo o spaCy):

```bash
pip install -r requirements.txt
```

Baixe o modelo do spaCy:

```bash
python -m spacy download pt_core_news_lg
```

Execute o script principal:

```bash
python analisar_pronomes.py
```

Confira os resultados na pasta `/log`.

## 👨‍🔬 Aplicações Possíveis

- Pesquisas acadêmicas em linguística e estilística  
- Estudos de colocação pronominal na norma culta  
- Análises de sintaxe em corpora jornalísticos
