import csv
import io
import json
import os
import re
import unicodedata
import urllib.request

avisos = []

def slugify(text):
    text = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", text)

def lista(v):
    return [x.strip() for x in re.split(r"[,;\n]+", v or "") if x.strip()]

def converter_inteiro(v, onde, campo):
    if not v:
        return None
    s = re.sub(r"[^\d-]", "", str(v).strip())
    try:
        return int(s)
    except ValueError:
        avisos.append(f"{onde}: valor inválido para número inteiro no campo '{campo}': {v}")
        return None

def converter_valor_economico(v):
    if not v:
        return None
    s = str(v).strip()
    # Tenta limpar formato monetário (ex: R$ 1.500.000,50 ou 1500000.50)
    limpo = s.replace("R$", "").replace("$", "").strip()
    if "," in limpo and "." in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        # Se for textual (ex: "15 bilhões"), preserva o texto original
        return s

def ler_links(v, onde):
    out = []
    for linha in (v or "").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if "|" in linha:
            rotulo, _, url = linha.rpartition("|")
            rotulo, url = rotulo.strip(), url.strip()
        else:
            url, rotulo = linha, ""
        if not url.lower().startswith(("http://", "https://")):
            avisos.append(f"{onde}: link sem http(s) ignorado: {linha}")
            continue
        out.append({"texto": rotulo or url, "url": url})
    return out

with urllib.request.urlopen(os.environ["CSV_URL"]) as r:
    texto_csv = r.read().decode("utf-8")

dados = []
ids_vistos = set()

for n, linha in enumerate(csv.DictReader(io.StringIO(texto_csv)), start=2):
    l = {(k or "").strip(): (v or "").strip() for k, v in linha.items()}
    did = l.get("id", "")
    ano_raw = l.get("ano", "")
    ramo = l.get("ramo", "")
    nivel = l.get("nivel", "")
    estado = l.get("estado", "")
    pais = l.get("pais", "")

    # Ignora linhas totalmente vazias
    if not any(l.values()):
        continue

    # Respeita coluna de publicação, se existir
    if l.get("publicar", "").lower() in ("não", "nao", "false", "0"):
        continue

    onde = f"Linha {n} (ano: {ano_raw}, ramo: {ramo})"

    # Geração automática de ID se estiver em branco
    if not did:
        base_id = "-".join(filter(None, [pais or "br", estado, nivel, ramo, ano_raw]))
        did = slugify(base_id) or f"dado-{n}"
        avisos.append(f"{onde}: sem 'id', gerado automaticamente como '{did}'")
    else:
        did = slugify(did)

    if did in ids_vistos:
        avisos.append(f"{onde}: id duplicado '{did}'")
    ids_vistos.add(did)

    ano = converter_inteiro(ano_raw, onde, "ano")
    coops = converter_inteiro(l.get("cooperativas"), onde, "cooperativas")
    cooperados = converter_inteiro(l.get("cooperados"), onde, "cooperados")
    empregos = converter_inteiro(l.get("empregos"), onde, "empregos")
    val_econ = converter_valor_economico(l.get("valor_economico"))

    links = ler_links(l.get("link"), onde)

    item = {
        "id": did,
        "ano": ano,
        "origem": l.get("origem", ""),
        "nivel": nivel,
        "pais": pais,
        "estado": estado,
        "cidade": l.get("cidade", ""),
        "ramo": ramo,
        "cooperativas": coops,
        "cooperados": cooperados,
        "empregos": empregos,
        "valor_economico": val_econ,
        "ref_id": l.get("ref_id", ""),
        "ref_tipo": l.get("ref_tipo", ""),
        "tags": lista(l.get("tags")),
        "fonte": l.get("fonte", ""),
        "link": links[0]["url"] if links else "",
        "links": links
    }
    dados.append(item)

# Ordena por ano decrescente por padrão (mais recentes primeiro)
dados.sort(key=lambda x: (x.get("ano") or 0), reverse=True)

with open("dados.json", "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

for a in avisos:
    print(f"::warning::{a}")
print(f"{len(dados)} registro(s) gravado(s) em dados.json")
