from fpdf import FPDF

def create_product_list_pdf(products: list, output_path: str):
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'Lista de Compras Automática', 0, 1, 'C')
    pdf.ln(10)

    # Lista de produtos
    pdf.set_font("Arial", '', 12)
    for product in products:
        pdf.cell(0, 10, f'- {product}', 0, 1)

    pdf.output(output_path)