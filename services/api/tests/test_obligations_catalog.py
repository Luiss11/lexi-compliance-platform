"""El catálogo de obligaciones es válido y no promete más de lo que se verificó."""
from app.services import obligations_catalog as oc


def test_catalog_loads_and_has_every_sector():
    cat = oc.load_catalog()
    sectors = {o.sector for o in cat.obligaciones}
    assert sectors == {"todos", "clinica", "comercio"}
    assert len(cat.obligaciones) >= 25


def test_ids_are_unique():
    ids = [o.id for o in oc.load_catalog().obligaciones]
    assert len(ids) == len(set(ids))


def test_every_obligation_names_its_source():
    for o in oc.load_catalog().obligaciones:
        assert o.norma and o.cita and o.publicacion, o.id
        assert o.obligacion.strip() and o.evidencia_sugerida.strip(), o.id


def test_pending_entries_do_not_pretend_to_have_an_article():
    for o in oc.load_catalog().obligaciones:
        if o.estado_verificacion == "pendiente":
            assert "verificar" in o.cita.lower(), o.id
            assert o.nota, o.id
            assert o.cita_textual is None, o.id


def test_unofficial_sources_are_marked_partial():
    for o in oc.load_catalog().obligaciones:
        if "no oficial" in o.publicacion.lower():
            assert o.estado_verificacion == "parcial", o.id
            assert o.nota, o.id


def test_quotes_are_short_excerpts():
    for o in oc.load_catalog().obligaciones:
        if o.cita_textual:
            assert len(o.cita_textual) <= 200, o.id


def test_for_sector_adds_common_obligations():
    clinica = {o.id for o in oc.for_sector("clinica")}
    assert "INC-06" in clinica and "CLI-01" in clinica
    assert "COM-01" not in clinica

    comercio = {o.id for o in oc.for_sector("comercio")}
    assert "COM-01" in comercio and "INC-06" in comercio
    assert "CLI-01" not in comercio


def test_sector_aliases_and_unknown_sector():
    assert {o.id for o in oc.for_sector("retail")} == {o.id for o in oc.for_sector("comercio")}
    assert {o.id for o in oc.for_sector(" Clinica ")} == {o.id for o in oc.for_sector("clinica")}
    unknown = oc.for_sector("minería")
    assert unknown and all(o.sector == "todos" for o in unknown)
    assert oc.for_sector(None)


def test_open_topics_are_listed():
    pend = oc.load_catalog().pendientes
    assert pend and all(p.motivo for p in pend)


def test_municipal_regulation_applies_to_every_sector():
    municipal = [o for o in oc.load_catalog().obligaciones if o.id.startswith("PCM-")]
    assert len(municipal) >= 8
    assert all(o.sector == "todos" and o.estado_verificacion == "verificado" for o in municipal)
    assert all("Durango" in o.norma for o in municipal)
    # Un consultorio y un comercio de Durango deben ver los simulacros municipales
    assert "PCM-03" in {o.id for o in oc.for_sector("clinica")}
    assert "PCM-03" in {o.id for o in oc.for_sector("comercio")}
