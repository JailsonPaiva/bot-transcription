from fpdf import FPDF
from datetime import datetime
from typing import List, Dict, Any


def _money(value: Any) -> str:
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        number = 0.0
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class OrcamentoObrasPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "ORCAMENTO DE MATERIAIS PARA OBRA", 0, 1, "C")
        self.set_font("Arial", "", 10)
        self.cell(0, 5, f"Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M')}", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")

    def add_materials_table(self, materials: List[Dict[str, Any]], obra_type: str = "obra"):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, f"MATERIAIS PARA {obra_type.upper()}", 0, 1, "L")
        self.ln(3)

        self.set_font("Arial", "B", 9)
        self.cell(22, 8, "QTD", 1, 0, "C")
        self.cell(28, 8, "UNIDADE", 1, 0, "C")
        self.cell(70, 8, "MATERIAL", 1, 0, "C")
        self.cell(35, 8, "UNITARIO", 1, 0, "C")
        self.cell(35, 8, "TOTAL", 1, 1, "C")

        self.set_font("Arial", "", 8)
        for material in materials:
            name = str(material.get("material", ""))
            if len(name) > 28:
                name = name[:25] + "..."
            self.cell(22, 8, str(material.get("quantidade", "")), 1, 0, "C")
            self.cell(28, 8, str(material.get("unidade", "")), 1, 0, "C")
            self.cell(70, 8, name, 1, 0, "L")
            self.cell(35, 8, _money(material.get("preco_unitario", 0)), 1, 0, "R")
            self.cell(35, 8, _money(material.get("preco_total", 0)), 1, 1, "R")

        self.ln(8)

    def add_summary_section(self, materials: List[Dict[str, Any]], total_amount: float = 0.0):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "RESUMO DO ORCAMENTO", 0, 1, "L")

        self.set_font("Arial", "", 10)
        self.cell(0, 6, f"Total de itens: {len(materials)}", 0, 1, "L")
        self.set_font("Arial", "B", 11)
        self.cell(0, 8, f"Valor total estimado: {_money(total_amount)}", 0, 1, "L")

        categorias = {}
        for material in materials:
            categoria = self._get_material_category(str(material.get("material", "")))
            categorias[categoria] = categorias.get(categoria, 0) + 1

        self.ln(4)
        self.set_font("Arial", "B", 10)
        self.cell(0, 6, "Distribuicao por categoria:", 0, 1, "L")
        self.set_font("Arial", "", 9)
        for categoria, count in categorias.items():
            self.cell(0, 5, f"- {categoria}: {count} itens", 0, 1, "L")
        self.ln(8)

    def add_notes_section(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "OBSERVACOES IMPORTANTES", 0, 1, "L")
        self.set_font("Arial", "", 9)
        observacoes = [
            "- Orcamento gerado automaticamente a partir de audio transcrito",
            "- Verifique quantidades e especificacoes antes da compra",
            "- Precos sao estimativas e podem variar por regiao/fornecedor",
            "- Consulte um profissional para validacao tecnica",
            "- Considere margem de seguranca para perdas e desperdicios",
        ]
        for obs in observacoes:
            self.cell(0, 5, obs, 0, 1, "L")
        self.ln(8)

    def _get_material_category(self, material: str) -> str:
        material_lower = material.lower()
        if any(word in material_lower for word in ["cimento", "argamassa", "rejunte", "gesso", "cal", "massa corrida", "reboco", "chapisco"]):
            return "Cimentos e Argamassas"
        if any(word in material_lower for word in ["tijolo", "bloco"]):
            return "Tijolos e Blocos"
        if any(word in material_lower for word in ["madeira", "tabua", "tábua", "ripa", "caibro"]):
            return "Madeiras"
        if any(word in material_lower for word in ["ferro", "aco", "aço", "vergalhao", "vergalhão", "tela", "arame"]):
            return "Metais"
        if "telha" in material_lower:
            return "Telhas e Coberturas"
        if any(word in material_lower for word in ["piso", "ceramica", "cerâmica", "porcelanato", "azulejo"]):
            return "Pisos e Revestimentos"
        if any(word in material_lower for word in ["cano", "tubo", "valvula", "válvula", "torneira"]):
            return "Hidraulica"
        if any(word in material_lower for word in ["fio", "cabo", "disjuntor", "tomada"]):
            return "Eletrica"
        if any(word in material_lower for word in ["martelo", "furadeira", "serra"]):
            return "Ferramentas"
        return "Outros"


def create_construction_budget_pdf(
    materials: List[Dict[str, Any]],
    obra_type: str = "obra",
    output_path: str = None,
    total_amount: float = None,
):
    if not output_path:
        output_path = f"app/temp/orcamento_obra_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    if total_amount is None:
        total_amount = 0.0
        for item in materials:
            try:
                total_amount += float(str(item.get("preco_total", "0")).replace(",", "."))
            except ValueError:
                pass

    pdf = OrcamentoObrasPDF()
    pdf.add_page()
    pdf.add_materials_table(materials, obra_type)
    pdf.add_summary_section(materials, float(total_amount))
    pdf.add_notes_section()
    pdf.output(output_path)
    return output_path


def create_simple_materials_list_pdf(materials: List[Dict[str, Any]], output_path: str = None):
    if not output_path:
        output_path = f"app/temp/lista_materiais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Lista de Materiais para Obra", 0, 1, "C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    for i, material in enumerate(materials, 1):
        item_text = f"{i}. {material['quantidade']} {material['unidade']} de {material['material']}"
        pdf.cell(0, 8, item_text, 0, 1)
    pdf.output(output_path)
    return output_path
