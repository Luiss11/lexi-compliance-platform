from app.agents.supervisor import audit_gaps


def test_detects_missing_civil_protection_program():
    gaps = audit_gaps("clinica", ["Licencia sanitaria 2025", "Aviso de privacidad v2023"])
    names = [g.requirement for g in gaps]
    assert "Programa Interno de Protección Civil" in names
    assert "Licencia sanitaria" not in names
