import re
import unicodedata
from typing import Dict, List, Optional

# Catálogo canônico: nome oficial -> sinônimos/variantes
CATALOGO_MATERIAIS: Dict[str, List[str]] = {
    # Cimentos e argamassas
    "cimento": ["cimento"],
    "argamassa": ["argamassa", "argamassa aci", "argamassa aciii"],
    "massa corrida": ["massa corrida", "massa acrílica", "massa acrilica"],
    "reboco": ["reboco", "reboco interno", "reboco externo"],
    "chapisco": ["chapisco"],
    "contrapiso": ["contrapiso", "contra piso", "contra-piso"],
    "emboço": ["emboço", "emboco"],
    "rejunte": ["rejunte"],
    "gesso": ["gesso"],
    "cal": ["cal", "cal hidratada"],
    "areia": ["areia", "areia média", "areia fina", "areia grossa"],
    "brita": ["brita", "brita 0", "brita 1"],
    "pedra": ["pedra"],
    # Tijolos e blocos
    "tijolo": ["tijolo", "tijolos", "jolo", "jolos", "tijolo ceramico", "tijolo cerâmico", "tijolo de barro"],
    "bloco": ["bloco", "blocos", "bloco de concreto", "bloco ceramico", "bloco cerâmico"],
    # Madeiras
    "madeira": ["madeira", "madeira tratada", "madeira serrada"],
    "tábua": ["tabua", "tábua", "tábuas", "tabuas"],
    "ripa": ["ripa", "ripas"],
    "caibro": ["caibro", "caibros"],
    "viga": ["viga", "vigas"],
    "pontalete": ["pontalete", "pontaletes"],
    "sarrafo": ["sarrafo", "sarrafos"],
    "compensado": ["compensado"],
    "mdf": ["mdf"],
    "osb": ["osb"],
    # Metais
    "ferro": ["ferro"],
    "aço": ["aco", "aço"],
    "vergalhão": ["vergalhao", "vergalhão", "ferro de construção", "ferro de construcao"],
    "tela": ["tela", "tela soldada"],
    "arame": ["arame", "arame recozido"],
    "prego": ["prego", "pregos"],
    "parafuso": ["parafuso", "parafusos"],
    "porca": ["porca", "porcas"],
    "arruela": ["arruela", "arruelas"],
    "chapa": ["chapa", "chapas"],
    "perfil": ["perfil", "perfis"],
    "cantoneira": ["cantoneira", "cantoneiras"],
    "tubo": ["tubo", "tubos"],
    "cano": ["cano", "canos"],
    # Telhas
    "telha": [
        "telha",
        "telhas",
        "telha ceramica",
        "telha cerâmica",
        "telha de barro",
        "telha de concreto",
        "telha metalica",
        "telha metálica",
        "telha de fibrocimento",
        "telha colonial",
        "telha francesa",
    ],
    # Pisos e revestimentos
    "piso": ["piso", "pisos"],
    "cerâmica": ["ceramica", "cerâmica"],
    "porcelanato": ["porcelanato"],
    "granito": ["granito"],
    "mármore": ["marmore", "mármore"],
    "azulejo": ["azulejo", "azulejos"],
    "pastilha": ["pastilha", "pastilhas"],
    "revestimento": ["revestimento", "revestimentos"],
    "textura": ["textura"],
    "tinta": ["tinta", "tintas"],
    "verniz": ["verniz"],
    "esmalte": ["esmalte"],
    # Hidráulica
    "conexão": ["conexao", "conexão", "conexões", "conexoes"],
    "válvula": ["valvula", "válvula"],
    "registro": ["registro", "registros"],
    "torneira": ["torneira", "torneiras"],
    "chuveiro": ["chuveiro", "chuveiros"],
    "ralo": ["ralo", "ralos"],
    "sifão": ["sifao", "sifão"],
    "caixa d'água": ["caixa d'agua", "caixa d'água", "caixa dagua", "caixa d agua"],
    "bomba": ["bomba", "bombas"],
    "hidrômetro": ["hidrometro", "hidrômetro"],
    # Elétrica
    "fio": ["fio", "fios", "fio eletrico", "fio elétrico"],
    "cabo": ["cabo", "cabos"],
    "disjuntor": ["disjuntor", "disjuntores"],
    "tomada": ["tomada", "tomadas"],
    "interruptor": ["interruptor", "interruptores"],
    "luminária": ["luminaria", "luminária"],
    "lâmpada": ["lampada", "lâmpada", "lampadas", "lâmpadas"],
    "quadro elétrico": ["quadro", "quadro eletrico", "quadro elétrico"],
    "conduíte": ["conduite", "conduíte", "eletroduto"],
    "soquete": ["soquete", "soquetes"],
    # Ferramentas
    "martelo": ["martelo"],
    "furadeira": ["furadeira"],
    "parafusadeira": ["parafusadeira"],
    "serra": ["serra"],
    "nível": ["nivel", "nível"],
    "esquadro": ["esquadro"],
    "trena": ["trena"],
    "colher de pedreiro": ["colher", "colher de pedreiro"],
    "espátula": ["espatula", "espátula"],
    "rolo": ["rolo", "rolo de pintura"],
    "pincel": ["pincel"],
    # Outros
    "isolante": ["isolante"],
    "manta": ["manta", "manta asfaltica", "manta asfáltica"],
    "lã de vidro": ["la de vidro", "lã de vidro"],
    "poliuretano": ["poliuretano"],
    "espuma": ["espuma", "espuma expansiva"],
    "cola": ["cola"],
    "silicone": ["silicone"],
    "primer": ["primer"],
    "selador": ["selador"],
    "impermeabilizante": ["impermeabilizante", "impermeabilizante liquido", "impermeabilizante líquido"],
}

UNIDADES_MEDIDA = [
    "metro quadrado",
    "metro cúbico",
    "metros",
    "metro",
    "m²",
    "m2",
    "m³",
    "m3",
    "m",
    "quilograma",
    "quilo",
    "kg",
    "tonelada",
    "ton",
    "sacos",
    "saco",
    "unidades",
    "unidade",
    "un",
    "peças",
    "peça",
    "pecas",
    "peca",
    "rolos",
    "rolo",
    "caixas",
    "caixa",
    "pacotes",
    "pacote",
    "litros",
    "litro",
    "l",
    "galões",
    "galão",
    "galoes",
    "baldes",
    "balde",
]

NUMERO_POR_EXTENSO = {
    "zero": "0",
    "meio": "0.5",
    "meia": "0.5",
    "um": "1",
    "uma": "1",
    "dois": "2",
    "duas": "2",
    "três": "3",
    "tres": "3",
    "quatro": "4",
    "cinco": "5",
    "seis": "6",
    "sete": "7",
    "oito": "8",
    "nove": "9",
    "dez": "10",
    "onze": "11",
    "doze": "12",
    "treze": "13",
    "catorze": "14",
    "quatorze": "14",
    "quinze": "15",
    "dezesseis": "16",
    "dezessete": "17",
    "dezoito": "18",
    "dezenove": "19",
    "vinte": "20",
    "trinta": "30",
    "quarenta": "40",
    "cinquenta": "50",
    "sessenta": "60",
    "setenta": "70",
    "oitenta": "80",
    "noventa": "90",
    "cem": "100",
    "cento": "100",
    "duzentos": "200",
    "trezentos": "300",
    "quatrocentos": "400",
    "quinhentos": "500",
    "seiscentos": "600",
    "setecentos": "700",
    "oitocentos": "800",
    "novecentos": "900",
    "mil": "1000",
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = strip_accents(text)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_quantity_token(token: str) -> str:
    token = token.strip().lower().replace(",", ".")
    token_norm = strip_accents(token)
    if token_norm in NUMERO_POR_EXTENSO:
        return NUMERO_POR_EXTENSO[token_norm]
    if re.fullmatch(r"\d+(?:\.\d+)?", token_norm):
        if "." in token_norm:
            return token_norm.rstrip("0").rstrip(".") if token_norm.endswith("0") else token_norm
        return str(int(token_norm)) if token_norm.isdigit() else token_norm
    return token


def normalize_numbers_in_text(text: str) -> str:
    """Substitui números por extenso por dígitos no texto."""
    words = sorted(NUMERO_POR_EXTENSO.keys(), key=len, reverse=True)
    pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\b"

    def repl(match: re.Match) -> str:
        return NUMERO_POR_EXTENSO[strip_accents(match.group(1).lower())]

    return re.sub(pattern, repl, text, flags=re.IGNORECASE)


def get_catalog_canonical_names() -> List[str]:
    return sorted(CATALOGO_MATERIAIS.keys(), key=len, reverse=True)


def build_synonym_index() -> List[tuple]:
    """Lista (sinonimo_normalizado, nome_canonico) ordenada do mais longo para o mais curto."""
    pairs = []
    for canonical, synonyms in CATALOGO_MATERIAIS.items():
        all_names = set([canonical] + synonyms)
        for name in all_names:
            pairs.append((normalize_text(name), canonical))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


_SYNONYM_INDEX = build_synonym_index()


def match_catalog_name(raw_name: str) -> Optional[str]:
    """Mapeia um nome livre para o canônico do catálogo, se possível."""
    norm = normalize_text(raw_name)
    if not norm:
        return None

    # 1) Match exato
    for synonym, canonical in _SYNONYM_INDEX:
        if norm == synonym:
            return canonical

    # 2) Sinônimo aparece como termo completo dentro do nome informado
    for synonym, canonical in _SYNONYM_INDEX:
        if re.search(r"(?<!\w)" + re.escape(synonym) + r"(?:s)?(?!\w)", norm):
            return canonical

    return None


def dedupe_materials(materials: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for item in materials:
        key = normalize_text(item["material"])
        if key not in merged:
            merged[key] = {
                "material": item["material"],
                "quantidade": normalize_quantity_token(str(item.get("quantidade", "1"))),
                "unidade": item.get("unidade") or "unidade",
            }
        else:
            # Mantém a primeira ocorrência; se quantidade atual for genérica, troca
            existing_qty = merged[key]["quantidade"]
            new_qty = normalize_quantity_token(str(item.get("quantidade", "1")))
            if existing_qty == "1" and new_qty != "1":
                merged[key]["quantidade"] = new_qty
                merged[key]["unidade"] = item.get("unidade") or merged[key]["unidade"]
    return list(merged.values())


def extract_materials_and_quantities(text: str) -> List[Dict[str, str]]:
    """
    Extrai materiais de construção e quantidades do texto.
    Normaliza números por extenso e deduplica por nome canônico.
    """
    normalized_source = normalize_numbers_in_text(text)
    text_norm = normalize_text(normalized_source)
    found_materials: List[Dict[str, str]] = []

    units_pattern = "|".join(re.escape(normalize_text(u)) for u in sorted(UNIDADES_MEDIDA, key=len, reverse=True))
    quantity_token = r"(\d+(?:[.,]\d+)?)"

    seen_spans = []

    for synonym, canonical in _SYNONYM_INDEX:
        material_pattern = r"(?<!\w)" + re.escape(synonym) + r"(?:s)?(?!\w)"
        for match in re.finditer(material_pattern, text_norm):
            start, end = match.span()
            # Evita overlaps (ex.: pegar "massa" dentro de "massa corrida")
            if any(not (end <= s or start >= e) for s, e in seen_spans):
                continue

            window_start = max(0, start - 40)
            window = text_norm[window_start:end + 40]

            quantity_found = None
            unit_found = None

            before = re.search(
                quantity_token + r"\s*(" + units_pattern + r")?\s*(?:de\s+)?" + re.escape(synonym) + r"(?:s)?(?:\b|$)",
                window,
            )
            if before:
                quantity_found = before.group(1)
                unit_found = before.group(2) or "unidade"
            else:
                after = re.search(
                    re.escape(synonym) + r"(?:s)?\s*(?:de\s+)?" + quantity_token + r"\s*(" + units_pattern + r")?",
                    window,
                )
                if after:
                    quantity_found = after.group(1)
                    unit_found = after.group(2) or "unidade"
                else:
                    nearby = re.search(quantity_token, window)
                    if nearby:
                        quantity_found = nearby.group(1)
                        unit_found = "unidade"

            if not quantity_found:
                quantity_found = "1"
                unit_found = "unidade"

            found_materials.append(
                {
                    "material": canonical.capitalize() if canonical.islower() else canonical.title(),
                    "quantidade": normalize_quantity_token(quantity_found),
                    "unidade": unit_found or "unidade",
                }
            )
            seen_spans.append((start, end))

    # Ajuste de capitalização canônica
    for item in found_materials:
        canon = match_catalog_name(item["material"]) or item["material"]
        item["material"] = canon.title()

    return dedupe_materials(found_materials)


def validate_materials_against_catalog(materials: List[Dict]) -> List[Dict[str, str]]:
    """Valida e normaliza materiais vindos do Gemini (ou outra fonte) contra o catálogo."""
    validated: List[Dict[str, str]] = []
    for item in materials or []:
        raw_name = str(item.get("material") or item.get("nome") or "").strip()
        if not raw_name:
            continue
        canonical = match_catalog_name(raw_name)
        if not canonical:
            print(f"[NLP] Material fora do catálogo ignorado: {raw_name}")
            continue
        quantidade = normalize_quantity_token(str(item.get("quantidade") or item.get("qtd") or "1"))
        unidade = str(item.get("unidade") or "unidade").strip().lower() or "unidade"
        validated.append(
            {
                "material": canonical.title(),
                "quantidade": quantidade,
                "unidade": unidade,
            }
        )
    return dedupe_materials(validated)


def extract_construction_context(text: str) -> Dict:
    materials = extract_materials_and_quantities(text)

    obra_types = {
        "casa": ["casa", "residencia", "moradia", "habitacao"],
        "apartamento": ["apartamento", "apto"],
        "comercial": ["comercial", "loja", "escritorio", "empresa"],
        "reforma": ["reforma", "reformar", "reformando", "reformado"],
        "construção": ["construcao", "construir", "construindo", "obra"],
    }

    detected_type = "obra"
    text_norm = normalize_text(text)
    for tipo, palavras in obra_types.items():
        if any(normalize_text(p) in text_norm for p in palavras):
            detected_type = tipo
            break

    return {
        "tipo_obra": detected_type,
        "materiais": materials,
        "total_materiais": len(materials),
        "texto_original": text,
    }


def format_materials_for_message(materials: List[Dict[str, str]]) -> str:
    lines = []
    for i, material in enumerate(materials, 1):
        lines.append(
            f"{i}. {material['quantidade']} {material['unidade']} de {material['material']}"
        )
    return "\n".join(lines)


def format_materials_for_pdf(materials: List[Dict[str, str]]) -> List[str]:
    return [
        f"{m['quantidade']} {m['unidade']} de {m['material']}"
        for m in materials
    ]
