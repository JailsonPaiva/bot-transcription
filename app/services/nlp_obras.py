import re
from typing import List, Dict, Tuple

# Lista de materiais de construção conhecidos
MATERIAIS_CONSTRUCAO = [
    # Cimentos e Argamassas
    "cimento", "argamassa", "rejunte", "gesso", "cal", "areia", "brita", "pedra",
    
    # Tijolos e Blocos
    "tijolo", "tijolos", "jolo", "jolos", "bloco", "blocos", "tijolo cerâmico", "tijolo de barro", "bloco de concreto", 
    "tijolo de vidro", "tijolo refratário",
    
    # Madeiras
    "madeira", "tábua", "ripa", "caibro", "viga", "pontalete", "sarrafos",
    "compensado", "mdf", "osb", "madeira tratada", "madeira serrada",
    
    # Metais
    "ferro", "aço", "vergalhão", "tela", "arame", "prego", "parafuso", "porca",
    "porca", "arruela", "chapa", "perfil", "cantoneira", "tubo", "cano",
    
    # Telhas e Coberturas
    "telha", "telha cerâmica", "telha de barro", "telha de concreto", "telha metálica",
    "telha de fibrocimento", "telha de vidro", "telha colonial", "telha francesa",
    
    # Pisos e Revestimentos
    "piso", "cerâmica", "porcelanato", "granito", "mármore", "pedra", "azulejo",
    "pastilha", "revestimento", "textura", "tinta", "verniz", "esmalte",
    
    # Hidráulica
    "cano", "tubo", "conexão", "válvula", "registro", "torneira", "chuveiro",
    "ralo", "sifão", "caixa d'água", "bomba", "hidrômetro",
    
    # Elétrica
    "fio", "cabo", "disjuntor", "tomada", "interruptor", "luminária", "lâmpada",
    "quadro", "conduíte", "eletroduto", "caixa", "soquete",
    
    # Ferramentas
    "martelo", "chave", "furadeira", "parafusadeira", "serra", "nível", "esquadro",
    "trena", "colher", "espátula", "rolo", "pincel",
    
    # Outros
    "isolante", "manta", "lã de vidro", "poliuretano", "espuma", "cola", "silicone",
    "massas", "primer", "selador", "impermeabilizante"
]

# Unidades de medida comuns em construção
UNIDADES_MEDIDA = [
    "metro", "metros", "m", "m²", "m³", "metro quadrado", "metro cúbico",
    "kg", "quilo", "quilograma", "tonelada", "ton", "saco", "sacos",
    "unidade", "un", "unidades", "peça", "peças", "rolo", "rolos",
    "caixa", "caixas", "pacote", "pacotes", "litro", "litros", "l",
    "galão", "galões", "balde", "baldes", "pé", "pés", "polegada", "polegadas"
]

# Palavras que indicam quantidades
PALAVRAS_QUANTIDADE = [
    "um", "uma", "dois", "duas", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez",
    "onze", "doze", "treze", "catorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove", "vinte",
    "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa", "cem",
    "mil", "milhão", "bilhão", "meia", "meio", "alguns", "algumas", "poucos", "poucas",
    "muitos", "muitas", "vários", "várias", "diversos", "diversas"
]

def extract_materials_and_quantities(text: str) -> List[Dict[str, str]]:
    """
    Extrai materiais de construção e suas quantidades do texto transcrito.
    
    Args:
        text: Texto transcrito do áudio
        
    Returns:
        Lista de dicionários com material, quantidade e unidade
    """
    found_materials = []
    text_lower = text.lower()
    
    # Padrões para encontrar quantidades
    quantity_patterns = [
        r'(\d+(?:[.,]\d+)?)\s*(' + '|'.join(UNIDADES_MEDIDA) + r')',
        r'(' + '|'.join(PALAVRAS_QUANTIDADE) + r')\s*(' + '|'.join(UNIDADES_MEDIDA) + r')',
        r'(\d+(?:[.,]\d+)?)\s*(saco|sacos|unidade|unidades|peça|peças)',
        r'(' + '|'.join(PALAVRAS_QUANTIDADE) + r')\s*(saco|sacos|unidade|unidades|peça|peças)'
    ]
    
    # Busca por materiais conhecidos
    for material in MATERIAIS_CONSTRUCAO:
        # Padrão para encontrar o material e sua quantidade próxima
        material_pattern = r'\b' + re.escape(material) + r'(?:s)?\b'
        
        if re.search(material_pattern, text_lower):
            # Busca por quantidade próxima ao material
            quantity_found = None
            unit_found = None
            
            # Procura por padrões de quantidade antes ou depois do material
            for pattern in quantity_patterns:
                # Busca antes do material (até 20 caracteres)
                before_match = re.search(
                    pattern + r'\s*(?:de\s+)?' + re.escape(material) + r'(?:s)?\b',
                    text_lower
                )
                if before_match:
                    quantity_found = before_match.group(1)
                    unit_found = before_match.group(2)
                    break
                
                # Busca depois do material (até 20 caracteres)
                after_match = re.search(
                    re.escape(material) + r'(?:s)?\b\s*(?:de\s+)?' + pattern,
                    text_lower
                )
                if after_match:
                    quantity_found = after_match.group(1)
                    unit_found = after_match.group(2)
                    break
            
            # Se não encontrou quantidade específica, tenta encontrar números próximos
            if not quantity_found:
                # Busca por números próximos ao material
                number_pattern = r'(\d+(?:[.,]\d+)?)'
                material_pos = text_lower.find(material)
                if material_pos != -1:
                    # Busca em um raio de 30 caracteres
                    search_start = max(0, material_pos - 30)
                    search_end = min(len(text_lower), material_pos + len(material) + 30)
                    search_text = text_lower[search_start:search_end]
                    
                    number_match = re.search(number_pattern, search_text)
                    if number_match:
                        quantity_found = number_match.group(1)
                        unit_found = "unidade"  # Unidade padrão
            
            # Se ainda não encontrou quantidade, assume 1
            if not quantity_found:
                quantity_found = "1"
                unit_found = "unidade"
            
            found_materials.append({
                "material": material.capitalize(),
                "quantidade": quantity_found,
                "unidade": unit_found
            })
    
    return found_materials

def extract_construction_context(text: str) -> Dict[str, any]:
    """
    Extrai contexto completo de uma obra do texto transcrito.
    
    Args:
        text: Texto transcrito do áudio
        
    Returns:
        Dicionário com informações estruturadas da obra
    """
    materials = extract_materials_and_quantities(text)
    
    # Detecta tipo de obra
    obra_types = {
        "casa": ["casa", "residência", "moradia", "habitação"],
        "apartamento": ["apartamento", "apto", "apartamento"],
        "comercial": ["comercial", "loja", "escritório", "empresa"],
        "reforma": ["reforma", "reformar", "reformando", "reformado"],
        "construção": ["construção", "construir", "construindo", "obra"]
    }
    
    detected_type = "obra"
    text_lower = text.lower()
    for tipo, palavras in obra_types.items():
        if any(palavra in text_lower for palavra in palavras):
            detected_type = tipo
            break
    
    return {
        "tipo_obra": detected_type,
        "materiais": materials,
        "total_materiais": len(materials),
        "texto_original": text
    }

def format_materials_for_pdf(materials: List[Dict[str, str]]) -> List[str]:
    """
    Formata a lista de materiais para exibição no PDF.
    
    Args:
        materials: Lista de materiais com quantidade e unidade
        
    Returns:
        Lista de strings formatadas
    """
    formatted_list = []
    for material in materials:
        formatted_item = f"{material['quantidade']} {material['unidade']} de {material['material']}"
        formatted_list.append(formatted_item)
    
    return formatted_list
