"""
Gerador de PDF de orçamento de materiais para obra.

- Fonte Unicode (DejaVu Sans) para acentuação em português
- Identidade visual via `Branding` (env hoje; multi-tenant no futuro)
- Mantém a API pública `create_construction_budget_pdf` usada pelo job
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fpdf import FPDF

logger = logging.getLogger(__name__)

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


@dataclass
class Branding:
    company_name: str = "Sua Empresa de Materiais"
    tagline: str = "Orçamentos para obra, direto no WhatsApp"
    logo_path: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    primary_color: Tuple[int, int, int] = (27, 54, 93)
    accent_color: Tuple[int, int, int] = (242, 141, 62)
    row_alt_color: Tuple[int, int, int] = (245, 246, 248)
    border_color: Tuple[int, int, int] = (223, 226, 230)
    text_color: Tuple[int, int, int] = (40, 44, 52)
    muted_text_color: Tuple[int, int, int] = (110, 116, 122)
    validade_dias: int = 7


DEFAULT_BRANDING = Branding()


def _parse_rgb(value: Optional[str], fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    if not value:
        return fallback
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 3:
        return fallback
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return fallback


def branding_from_settings(settings: Any = None) -> Branding:
    """Monta Branding a partir das env/Settings (preparado para multi-tenant depois)."""
    if settings is None:
        try:
            from app.core.config import get_settings

            settings = get_settings()
        except Exception:
            return DEFAULT_BRANDING

    logo = (getattr(settings, "pdf_logo_path", None) or "").strip() or None
    if logo and not os.path.isabs(logo):
        # relativo à raiz do projeto
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidate = os.path.join(root, logo)
        logo = candidate if os.path.isfile(candidate) else logo

    return Branding(
        company_name=(getattr(settings, "pdf_company_name", None) or DEFAULT_BRANDING.company_name).strip(),
        tagline=(getattr(settings, "pdf_tagline", None) or DEFAULT_BRANDING.tagline).strip(),
        logo_path=logo,
        phone=(getattr(settings, "pdf_phone", None) or "").strip() or None,
        website=(getattr(settings, "pdf_website", None) or "").strip() or None,
        primary_color=_parse_rgb(
            getattr(settings, "pdf_primary_color", None),
            DEFAULT_BRANDING.primary_color,
        ),
        accent_color=_parse_rgb(
            getattr(settings, "pdf_accent_color", None),
            DEFAULT_BRANDING.accent_color,
        ),
        validade_dias=int(getattr(settings, "pdf_validade_dias", None) or DEFAULT_BRANDING.validade_dias),
    )


def _money(value: Any) -> str:
    try:
        number = float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        number = 0.0
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class OrcamentoObrasPDF(FPDF):
    def __init__(self, branding: Branding = None):
        super().__init__()
        self.branding = branding or DEFAULT_BRANDING
        self.set_auto_page_break(auto=True, margin=20)
        self._register_fonts()
        self._orcamento_numero = datetime.now().strftime("%Y%m%d%H%M")

    def _register_fonts(self):
        regular = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
        bold = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
        italic = os.path.join(FONTS_DIR, "DejaVuSans-Oblique.ttf")
        missing = [p for p in (regular, bold, italic) if not os.path.isfile(p)]
        if missing:
            raise FileNotFoundError(
                "Fontes DejaVu não encontradas em app/services/fonts/. "
                f"Arquivos ausentes: {', '.join(os.path.basename(m) for m in missing)}"
            )
        self.add_font("DejaVu", "", regular)
        self.add_font("DejaVu", "B", bold)
        self.add_font("DejaVu", "I", italic)

    def _fill(self, rgb):
        self.set_fill_color(*rgb)

    def _text(self, rgb):
        self.set_text_color(*rgb)

    def _draw(self, rgb):
        self.set_draw_color(*rgb)

    def header(self):
        b = self.branding
        banner_h = 28

        self._fill(b.primary_color)
        self.rect(0, 0, self.w, banner_h, "F")

        logo_x, logo_y, logo_size = 12, 5, 18
        if b.logo_path and os.path.isfile(b.logo_path):
            try:
                self.image(b.logo_path, x=logo_x, y=logo_y, h=logo_size)
            except RuntimeError:
                self._draw_logo_placeholder(logo_x, logo_y, logo_size)
        else:
            self._draw_logo_placeholder(logo_x, logo_y, logo_size)

        text_x = logo_x + logo_size + 6
        self.set_xy(text_x, 6)
        self._text((255, 255, 255))
        self.set_font("DejaVu", "B", 14)
        self.cell(0, 8, b.company_name, 0, 2, "L")
        self.set_x(text_x)
        self.set_font("DejaVu", "", 9)
        self._text((235, 238, 242))
        self.cell(0, 5, b.tagline, 0, 0, "L")

        self.set_xy(-90, 6)
        self._text((255, 255, 255))
        self.set_font("DejaVu", "B", 9)
        self.cell(78, 5, f"Orçamento Nº {self._orcamento_numero}", 0, 2, "R")
        self.set_x(-90)
        self.set_font("DejaVu", "", 8)
        self._text((235, 238, 242))
        self.cell(78, 5, datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M"), 0, 0, "R")

        self.set_y(banner_h + 8)
        self._text(b.text_color)

    def _draw_logo_placeholder(self, x, y, size):
        b = self.branding
        initials = "".join(w[0] for w in b.company_name.split()[:2]).upper() or "?"
        self._fill(b.accent_color)
        self.set_draw_color(255, 255, 255)
        self.ellipse(x, y, size, size, "F")
        self.set_xy(x, y + size / 2 - 4)
        self._text((255, 255, 255))
        self.set_font("DejaVu", "B", 11)
        self.cell(size, 8, initials, 0, 0, "C")

    def footer(self):
        b = self.branding
        self.set_y(-18)
        self._draw(b.border_color)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self._text(b.muted_text_color)

        rodape_esquerda = b.company_name
        if b.phone:
            rodape_esquerda += f"  ·  {b.phone}"
        if b.website:
            rodape_esquerda += f"  ·  {b.website}"

        self.cell(0, 6, rodape_esquerda, 0, 0, "L")
        self.set_font("DejaVu", "", 8)
        self.cell(0, 6, f"Página {self.page_no()}", 0, 0, "R")

    def add_materials_table(self, materials: List[Dict[str, Any]], obra_type: str = "obra"):
        b = self.branding
        self.set_font("DejaVu", "B", 13)
        self._text(b.text_color)
        self.cell(0, 9, f"Materiais para {obra_type}", 0, 1, "L")
        self.ln(2)

        col_widths = {"qtd": 18, "unidade": 26, "material": 76, "unitario": 33, "total": 33}
        row_h = 8

        self._fill(b.primary_color)
        self._text((255, 255, 255))
        self.set_font("DejaVu", "B", 9)
        self.cell(col_widths["qtd"], row_h, "QTD", 0, 0, "C", True)
        self.cell(col_widths["unidade"], row_h, "UNIDADE", 0, 0, "C", True)
        self.cell(col_widths["material"], row_h, "MATERIAL", 0, 0, "L", True)
        self.cell(col_widths["unitario"], row_h, "UNITÁRIO", 0, 0, "R", True)
        self.cell(col_widths["total"], row_h, "TOTAL", 0, 1, "R", True)

        self.set_font("DejaVu", "", 9)
        for i, material in enumerate(materials):
            name = str(material.get("material", ""))
            fill = i % 2 == 1
            if fill:
                self._fill(b.row_alt_color)
            self._text(b.text_color)

            lines = self.multi_cell(
                col_widths["material"],
                row_h,
                text=name,
                border=0,
                align="L",
                dry_run=True,
                output="LINES",
            )
            n_lines = max(1, len(lines))
            line_height = row_h * n_lines

            if self.get_y() + line_height > self.page_break_trigger:
                self.add_page()
                self._fill(b.primary_color)
                self._text((255, 255, 255))
                self.set_font("DejaVu", "B", 9)
                self.cell(col_widths["qtd"], row_h, "QTD", 0, 0, "C", True)
                self.cell(col_widths["unidade"], row_h, "UNIDADE", 0, 0, "C", True)
                self.cell(col_widths["material"], row_h, "MATERIAL", 0, 0, "L", True)
                self.cell(col_widths["unitario"], row_h, "UNITÁRIO", 0, 0, "R", True)
                self.cell(col_widths["total"], row_h, "TOTAL", 0, 1, "R", True)
                self.set_font("DejaVu", "", 9)

            x0, y0 = self.get_x(), self.get_y()
            self.cell(
                col_widths["qtd"],
                line_height,
                str(material.get("quantidade", "")),
                0,
                0,
                "C",
                fill,
            )
            self.cell(
                col_widths["unidade"],
                line_height,
                str(material.get("unidade", "")),
                0,
                0,
                "C",
                fill,
            )

            x_mat = self.get_x()
            if fill:
                self._fill(b.row_alt_color)
                self.rect(x_mat, y0, col_widths["material"], line_height, "F")
            self.set_xy(x_mat, y0)
            self.multi_cell(col_widths["material"], row_h, name, 0, "L", False)

            self.set_xy(x_mat + col_widths["material"], y0)
            self.cell(
                col_widths["unitario"],
                line_height,
                _money(material.get("preco_unitario", 0)),
                0,
                0,
                "R",
                fill,
            )
            self.cell(
                col_widths["total"],
                line_height,
                _money(material.get("preco_total", 0)),
                0,
                1,
                "R",
                fill,
            )

            self._draw(b.border_color)
            self.line(x0, y0 + line_height, x0 + sum(col_widths.values()), y0 + line_height)

        self.ln(8)

    def add_summary_section(self, materials: List[Dict[str, Any]], total_amount: float = 0.0):
        b = self.branding
        self.set_font("DejaVu", "B", 12)
        self._text(b.text_color)
        self.cell(0, 9, "Resumo do orçamento", 0, 1, "L")
        self.ln(1)

        card_h = 22
        x, y = self.get_x(), self.get_y()
        self._fill(b.accent_color)
        self.rect(x, y, self.w - 24, card_h, "F")

        self.set_xy(x + 6, y + 4)
        self._text((255, 255, 255))
        self.set_font("DejaVu", "", 9)
        self.cell(
            0,
            5,
            f"Total de {len(materials)} {'item' if len(materials) == 1 else 'itens'}",
            0,
            2,
            "L",
        )
        self.set_x(x + 6)
        self.set_font("DejaVu", "B", 15)
        self.cell(0, 9, f"Valor total estimado: {_money(total_amount)}", 0, 0, "L")

        self.set_y(y + card_h + 6)

        categorias: Dict[str, int] = {}
        for material in materials:
            categoria = self._get_material_category(str(material.get("material", "")))
            categorias[categoria] = categorias.get(categoria, 0) + 1

        self.set_font("DejaVu", "B", 10)
        self._text(b.text_color)
        self.cell(0, 6, "Distribuição por categoria", 0, 1, "L")
        self.ln(1)

        self.set_font("DejaVu", "", 8.5)
        chip_x, chip_y = self.get_x(), self.get_y()
        max_x = self.w - 12
        for categoria, count in categorias.items():
            label = f"  {categoria} · {count}  "
            chip_w = self.get_string_width(label) + 4
            if chip_x + chip_w > max_x:
                chip_x = 12
                chip_y += 8
            self.set_xy(chip_x, chip_y)
            self._fill(b.row_alt_color)
            self._draw(b.border_color)
            self._text(b.text_color)
            self.cell(chip_w, 7, label, 1, 0, "C", True)
            chip_x += chip_w + 3

        self.set_xy(12, chip_y + 10)
        self.ln(4)

        validade = (datetime.now() + timedelta(days=b.validade_dias)).strftime("%d/%m/%Y")
        self.set_font("DejaVu", "I", 9)
        self._text(b.muted_text_color)
        self.cell(
            0,
            6,
            f"Orçamento válido até {validade} ({b.validade_dias} dias). Preços sujeitos a alteração.",
            0,
            1,
            "L",
        )
        self.ln(4)

    def add_notes_section(self):
        b = self.branding
        self.set_font("DejaVu", "B", 11)
        self._text(b.text_color)
        self.cell(0, 8, "Observações importantes", 0, 1, "L")
        self.set_font("DejaVu", "", 9)
        self._text(b.muted_text_color)
        observacoes = [
            "Orçamento gerado automaticamente a partir de áudio transcrito.",
            "Verifique quantidades e especificações antes da compra.",
            "Preços são estimativas e podem variar por região/fornecedor.",
            "Consulte um profissional para validação técnica.",
            "Considere margem de segurança para perdas e desperdícios.",
        ]
        for obs in observacoes:
            self.set_x(12)
            self.cell(4, 5.5, "•", 0, 0, "L")
            self.cell(0, 5.5, obs, 0, 1, "L")
        self.ln(6)

    def _get_material_category(self, material: str) -> str:
        material_lower = material.lower()
        if any(
            w in material_lower
            for w in [
                "cimento",
                "argamassa",
                "rejunte",
                "gesso",
                "cal",
                "massa corrida",
                "reboco",
                "chapisco",
            ]
        ):
            return "Cimentos e Argamassas"
        if any(w in material_lower for w in ["tijolo", "bloco"]):
            return "Tijolos e Blocos"
        if any(w in material_lower for w in ["madeira", "tabua", "tábua", "ripa", "caibro"]):
            return "Madeiras"
        if any(
            w in material_lower
            for w in ["ferro", "aco", "aço", "vergalhao", "vergalhão", "tela", "arame"]
        ):
            return "Metais"
        if "telha" in material_lower:
            return "Telhas e Coberturas"
        if any(
            w in material_lower
            for w in ["piso", "ceramica", "cerâmica", "porcelanato", "azulejo"]
        ):
            return "Pisos e Revestimentos"
        if any(w in material_lower for w in ["cano", "tubo", "valvula", "válvula", "torneira"]):
            return "Hidráulica"
        if any(w in material_lower for w in ["fio", "cabo", "disjuntor", "tomada"]):
            return "Elétrica"
        if any(w in material_lower for w in ["martelo", "furadeira", "serra"]):
            return "Ferramentas"
        return "Outros"


def create_construction_budget_pdf(
    materials: List[Dict[str, Any]],
    obra_type: str = "obra",
    output_path: str = None,
    total_amount: float = None,
    branding: Branding = None,
):
    """API pública usada pelo job. `branding` opcional; se omitido, lê Settings/env."""
    if not output_path:
        output_path = f"app/temp/orcamento_obra_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    os.makedirs(os.path.dirname(output_path) or "app/temp", exist_ok=True)

    if total_amount is None:
        total_amount = 0.0
        for item in materials:
            try:
                total_amount += float(str(item.get("preco_total", "0")).replace(",", "."))
            except (ValueError, TypeError):
                pass

    resolved = branding or branding_from_settings()
    pdf = OrcamentoObrasPDF(branding=resolved)
    pdf.add_page()
    pdf.add_materials_table(materials, obra_type)
    pdf.add_summary_section(materials, float(total_amount))
    pdf.add_notes_section()
    pdf.output(output_path)
    logger.info("PDF gerado: %s (branding=%s)", output_path, resolved.company_name)
    return output_path


def create_simple_materials_list_pdf(
    materials: List[Dict[str, Any]],
    output_path: str = None,
    branding: Branding = None,
):
    b = branding or branding_from_settings()
    if not output_path:
        output_path = f"app/temp/lista_materiais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    os.makedirs(os.path.dirname(output_path) or "app/temp", exist_ok=True)

    pdf = OrcamentoObrasPDF(branding=b)
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 13)
    pdf._text(b.text_color)
    pdf.cell(0, 9, "Lista de materiais para obra", 0, 1, "L")
    pdf.ln(4)
    pdf.set_font("DejaVu", "", 11)
    for i, material in enumerate(materials, 1):
        pdf.set_x(12)
        item_text = (
            f"{i}. {material['quantidade']} {material['unidade']} de {material['material']}"
        )
        pdf.cell(0, 7, item_text, 0, 1)
    pdf.output(output_path)
    return output_path
