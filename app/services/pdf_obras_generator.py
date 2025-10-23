from fpdf import FPDF
from datetime import datetime
from typing import List, Dict

class OrcamentoObrasPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        """Cabeçalho do PDF"""
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'ORÇAMENTO DE MATERIAIS PARA OBRA', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, f'Gerado em: {datetime.now().strftime("%d/%m/%Y às %H:%M")}', 0, 1, 'C')
        self.ln(10)
    
    def footer(self):
        """Rodapé do PDF"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
    
    def add_materials_table(self, materials: List[Dict[str, str]], obra_type: str = "obra"):
        """Adiciona tabela de materiais ao PDF"""
        
        # Título da seção
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, f'MATERIAIS PARA {obra_type.upper()}', 0, 1, 'L')
        self.ln(5)
        
        # Cabeçalho da tabela
        self.set_font('Arial', 'B', 10)
        self.cell(40, 8, 'QUANTIDADE', 1, 0, 'C')
        self.cell(30, 8, 'UNIDADE', 1, 0, 'C')
        self.cell(120, 8, 'MATERIAL', 1, 1, 'C')
        
        # Dados da tabela
        self.set_font('Arial', '', 9)
        for material in materials:
            # Quebra de linha se o texto for muito longo
            material_name = material['material']
            if len(material_name) > 25:
                material_name = material_name[:22] + "..."
            
            self.cell(40, 8, material['quantidade'], 1, 0, 'C')
            self.cell(30, 8, material['unidade'], 1, 0, 'C')
            self.cell(120, 8, material_name, 1, 1, 'L')
        
        self.ln(10)
    
    def add_summary_section(self, materials: List[Dict[str, str]]):
        """Adiciona seção de resumo"""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'RESUMO DO ORÇAMENTO', 0, 1, 'L')
        
        self.set_font('Arial', '', 10)
        self.cell(0, 6, f'Total de itens: {len(materials)}', 0, 1, 'L')
        
        # Contagem por categoria
        categorias = {}
        for material in materials:
            categoria = self._get_material_category(material['material'])
            if categoria not in categorias:
                categorias[categoria] = 0
            categorias[categoria] += 1
        
        self.ln(5)
        self.set_font('Arial', 'B', 10)
        self.cell(0, 6, 'Distribuição por categoria:', 0, 1, 'L')
        
        self.set_font('Arial', '', 9)
        for categoria, count in categorias.items():
            self.cell(0, 5, f'- {categoria}: {count} itens', 0, 1, 'L')
        
        self.ln(10)
    
    def add_notes_section(self):
        """Adiciona seção de observações"""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'OBSERVAÇÕES IMPORTANTES', 0, 1, 'L')
        
        self.set_font('Arial', '', 9)
        observacoes = [
            "- Este orçamento foi gerado automaticamente a partir de áudio transcrito",
            "- Verifique as quantidades e especificações antes da compra",
            "- Consulte um profissional para validação técnica",
            "- Preços podem variar conforme fornecedor e região",
            "- Considere margem de segurança para perdas e desperdícios"
        ]
        
        for obs in observacoes:
            self.cell(0, 5, obs, 0, 1, 'L')
        
        self.ln(10)
    
    def _get_material_category(self, material: str) -> str:
        """Categoriza o material"""
        material_lower = material.lower()
        
        if any(word in material_lower for word in ['cimento', 'argamassa', 'rejunte', 'gesso', 'cal']):
            return 'Cimentos e Argamassas'
        elif any(word in material_lower for word in ['tijolo', 'bloco']):
            return 'Tijolos e Blocos'
        elif any(word in material_lower for word in ['madeira', 'tábua', 'ripa', 'caibro']):
            return 'Madeiras'
        elif any(word in material_lower for word in ['ferro', 'aço', 'vergalhão', 'tela', 'arame']):
            return 'Metais'
        elif any(word in material_lower for word in ['telha']):
            return 'Telhas e Coberturas'
        elif any(word in material_lower for word in ['piso', 'cerâmica', 'porcelanato', 'azulejo']):
            return 'Pisos e Revestimentos'
        elif any(word in material_lower for word in ['cano', 'tubo', 'válvula', 'torneira']):
            return 'Hidráulica'
        elif any(word in material_lower for word in ['fio', 'cabo', 'disjuntor', 'tomada']):
            return 'Elétrica'
        elif any(word in material_lower for word in ['martelo', 'chave', 'furadeira', 'serra']):
            return 'Ferramentas'
        else:
            return 'Outros'

def create_construction_budget_pdf(materials: List[Dict[str, str]], obra_type: str = "obra", output_path: str = None):
    """
    Cria um PDF de orçamento para obras com lista de materiais.
    
    Args:
        materials: Lista de materiais com quantidade e unidade
        obra_type: Tipo de obra (casa, apartamento, reforma, etc.)
        output_path: Caminho para salvar o PDF
        
    Returns:
        Caminho do arquivo PDF gerado
    """
    if not output_path:
        output_path = f"app/temp/orcamento_obra_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    pdf = OrcamentoObrasPDF()
    pdf.add_page()
    
    # Adiciona tabela de materiais
    pdf.add_materials_table(materials, obra_type)
    
    # Adiciona seção de resumo
    pdf.add_summary_section(materials)
    
    # Adiciona seção de observações
    pdf.add_notes_section()
    
    # Salva o PDF
    pdf.output(output_path)
    
    return output_path

def create_simple_materials_list_pdf(materials: List[Dict[str, str]], output_path: str = None):
    """
    Cria um PDF simples com lista de materiais (versão mais básica).
    
    Args:
        materials: Lista de materiais com quantidade e unidade
        output_path: Caminho para salvar o PDF
        
    Returns:
        Caminho do arquivo PDF gerado
    """
    if not output_path:
        output_path = f"app/temp/lista_materiais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Lista de Materiais para Obra', 0, 1, 'C')
    pdf.ln(10)
    
    # Lista de materiais
    pdf.set_font("Arial", '', 12)
    for i, material in enumerate(materials, 1):
        item_text = f"{i}. {material['quantidade']} {material['unidade']} de {material['material']}"
        pdf.cell(0, 8, item_text, 0, 1)
    
    pdf.output(output_path)
    return output_path
