import csv
import io
import json
import os
import re
import unicodedata
import urllib.request

avisos = []


def lista(v):
    return [
        x.strip()
        for x in re.split(r"[,;\n]+", v or "")
        if x.strip()
    ]


def sim(v):
    return (v or "").strip().lower() in (
        "sim",
        "s",
        "x",
        "true",
        "1"
    )


def normalizar(v):
    texto = str(v or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    return texto


def eh_credito(v):
    ramo = normalizar(v)
    return "credito" in ramo


def parse_num(v):
    if not v:
        return 0

    try:
        clean = str(v).replace(".", "").replace(",", ".")
        return float(clean) if "." in clean else int(clean)
    except:
        return 0


with urllib.request.urlopen(os.environ["CSV_URL"]) as r:
    texto_csv = r.read().decode("utf-8")


saida = []

leitor = csv.DictReader(io.StringIO(texto_csv))

# Verifica se colunas condicionais existem na planilha
campos = [str(c or "").strip().lower() for c in (leitor.fieldnames or [])]
tem_coluna_publicar = "publicar" in campos
tem_coluna_pac = "pac" in campos


for n, linha in enumerate(leitor, start=2):

    l = {
        (k or "").strip(): (v or "").strip()
        for k, v in linha.items()
    }

    ano_val = l.get("ano", "").strip()

    if not ano_val:
        avisos.append(
            f"Linha {n}: sem 'ano', ignorada"
        )
        continue

    # ---------------------------------------------------------
    # PUBLICAR
    # ---------------------------------------------------------
    if tem_coluna_publicar:
        if not sim(l.get("publicar")):
            continue

    ramo = l.get("ramo", "") or None

    item = {
        "ano": int(parse_num(ano_val)),
        "geral": sim(l.get("geral")),
        "ramo": ramo,
        "nivel": l.get("nivel", ""),
        "pais": l.get("pais", "Brasil"),
        "estado": l.get("estado", ""),
        "cidade": l.get("cidade", ""),
        "cooperativas": parse_num(
            l.get("cooperativas")
        ),
        "cooperados": parse_num(
            l.get("cooperados")
        ),
        "empregos": parse_num(
            l.get("empregos")
        ),
        "tags": lista(
            l.get("tags")
        ),
        "fonte": l.get("fonte", ""),
        "link": l.get("link", ""),
        "note": l.get("note", "")
    }

    # ---------------------------------------------------------
    # PAC
    # ---------------------------------------------------------
    if eh_credito(ramo) and tem_coluna_pac:

        pac_val = l.get("pac", "").strip()

        if pac_val:
            item["pac"] = parse_num(pac_val)

    saida.append(item)


with open(
    "dados.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        saida,
        f,
        ensure_ascii=False,
        indent=2
    )


for a in avisos:
    print(f"::warning::{a}")

print(
    f"{len(saida)} registro(s) gravado(s) em dados.json"
)
