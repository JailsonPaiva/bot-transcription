import re

# Lista de produtos conhecidos (pode vir de um banco de dados no futuro)
KNOWN_PRODUCTS = [
    "leite", "pão", "ovos", "queijo", "presunto", "arroz", "feijão", "maçã",
    "banana", "tomate", "cebola", "alface", "frango", "carne moída", "sabão em pó", "papel higiênico","carne", "macarrão", "fruta"
]

def extract_products_from_text(text: str) -> list:
    found_products = []
    text_lower = text.lower()
    
    # Busca por palavras exatas e suas formas no plural (simples)
    for product in KNOWN_PRODUCTS:
        # Usando regex para encontrar a palavra exata (evita "tomateiro" para "tomate")
        # e o plural simples com "s" ou "ns"
        pattern = r'\b' + re.escape(product) + r'(s|ns)?\b'
        if re.search(pattern, text_lower):
            found_products.append(product.capitalize())
            
    return list(set(found_products)) # Remove duplicatas