"""Testes unitários dos parsers de edição de lista (Sprint 3)."""
from app.domain.conversation import (
    apply_quantity_change,
    apply_remove_material,
    is_delete_data_request,
    is_privacy_policy_request,
    parse_add_material,
    parse_quantity_change,
    parse_remove_item,
)


def test_parse_remove_by_index():
    assert parse_remove_item("remove 2") == ("index", 2)
    assert parse_remove_item("remover item 3") == ("index", 3)


def test_parse_remove_by_name():
    assert parse_remove_item("tira cimento") == ("name", "cimento")


def test_parse_quantity():
    assert parse_quantity_change("qtd 2=10") == (2, "10")
    assert parse_quantity_change("muda 1 para 5,5") == (1, "5.5")


def test_parse_add():
    assert parse_add_material("adiciona 10 saco cimento") == "10 saco cimento"


def test_apply_remove_and_qty():
    materials = [
        {"material": "cimento", "quantidade": "1", "unidade": "saco"},
        {"material": "areia", "quantidade": "2", "unidade": "m3"},
    ]
    updated, note = apply_remove_material(materials, ("index", 1))
    assert len(updated) == 1
    assert updated[0]["material"] == "areia"
    assert "cimento" in (note or "").lower()

    updated2, _ = apply_quantity_change(materials, 2, "9")
    assert updated2[1]["quantidade"] == "9"


def test_lgpd_triggers():
    assert is_privacy_policy_request("privacidade")
    assert is_delete_data_request("apagar meus dados")
    assert is_delete_data_request("excluir dados")
