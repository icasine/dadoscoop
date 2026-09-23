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
        "1",
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
    return ramo in (
        "credito",
        "cooperativas de credito",
    )


def parse_num(v):
    if v is None:
        return 0

    valor = str(v).strip()

    if not valor:
        return 0

    try:
        # Formato brasileiro: 1.234,56
        if "," in valor:
            clean = valor.replace(".", "").replace(",", ".")
        else:
            # Para quantidades inteiras, mantém 1.234 como 1234
            clean = valor.replace(".", "")

        numero = float(clean)

        if numero.is_integer():
            return int(numero)

        return numero

    except (ValueError, TypeError):
        return 0


with urllib.request.urlopen(os.environ["CSV_URL"]) as r:
    texto_csv = r.read().decode("utf-8-sig")


saida = []

leitor = csv.DictReader(io.StringIO(texto_csv))

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
    # Somente registros marcados para publicação entram
    # no dados.json.
    # ---------------------------------------------------------
    publicar_val = l.get("publicar", "")

    if not sim(publicar_val):
        continue

    ramo = l.get("ramo", "") or None
    credito = eh_credito(ramo)

    # ---------------------------------------------------------
    # REGISTRO BASE
    # ---------------------------------------------------------
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
        "tags": lista(l.get("tags")),
        "fonte": l.get("fonte", ""),
        "link": l.get("link", "")
    }

    # ---------------------------------------------------------
    # PAC
    # ---------------------------------------------------------
    # Só o ramo Crédito recebe o campo pac.
    # Para outros ramos, o campo nem sequer é gravado.
    # ---------------------------------------------------------
    if credito:
        pac_val = l.get("pac", "").strip()

        if pac_val:
            item["pac"] = parse_num(pac_val)
        else:
            item["pac"] = None

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
