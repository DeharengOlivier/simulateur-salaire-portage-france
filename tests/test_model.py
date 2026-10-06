from dataclasses import replace
from decimal import Decimal as D

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from portage.model import Scenario, budget, gross_for_budget, reconcile, simulate, target_expenses
from portage.money import CENT, amount, decimal, money, percent, rate
from portage.tax import BRACKETS, neutral_rate


def test_rounding_is_decimal_half_up() -> None:
    assert money(D("1.005")) == D("1.01")
    assert money(D("-1.005")) == D("-1.01")
    assert decimal("1,25") == D("1.25")
    assert amount("0") == D("0.00")


@pytest.mark.parametrize("value", [True, 0.1, "NaN", "Infinity", "1e99", "1e-9", "x", "9" * 40])
def test_invalid_numbers(value: object) -> None:
    with pytest.raises(ValueError):
        decimal(value)


@pytest.mark.parametrize("value", ["-1", "0.001"])
def test_invalid_amount(value: str) -> None:
    with pytest.raises(ValueError):
        amount(value)


def test_rate_limits() -> None:
    with pytest.raises(ValueError):
        rate("101")
    assert rate("100") == 100


def test_all_pas_boundaries() -> None:
    for index, (cap, value) in enumerate(BRACKETS):
        assert neutral_rate(cap - CENT) == value
        next_rate = BRACKETS[index + 1][1] if index + 1 < len(BRACKETS) else D("43")
        assert neutral_rate(cap) == next_rate
        assert neutral_rate(cap + CENT) == next_rate


def test_fee_cap_is_monthly_and_fixed_fee_is_outside() -> None:
    s = Scenario(
        tjm=D("1000"),
        jours=D("20"),
        gestion=D("8"),
        plafond_gestion=D("600"),
        forfait_gestion=D("50"),
    )
    assert budget(s)["gestion"] == 650
    assert budget(replace(s, plafond_gestion=None))["gestion"] == 1650
    assert budget(replace(s, plafond_gestion=D("0")))["gestion"] == 50


def test_independent_hand_calculation() -> None:
    s = Scenario(
        tjm=D("100"),
        jours=D("10"),
        gestion=D("10"),
        charges_patronales=D("25"),
        charges_salariales=D("20"),
        csg_non_deductible=D("2"),
        taux_pas=D("10"),
        frais=D("100"),
        teletravail=D("25"),
        titres=D("10"),
        titre_employeur=D("2.50"),
        titre_salarie=D("2"),
        frais_refactures=D("50"),
    )
    r = simulate(s)
    # 1000 - 100 - 100 - 25 - 25 = 750 = 600 gross + 150 employer
    assert r["brut"] == 600
    assert r["cotisations_salariales"] == 120
    assert r["net_imposable"] == 492
    assert r["pas"] == D("49.20")
    assert r["net_verse"] == D("585.80")
    assert r["solde_budget"] == 0


def test_reserve_and_adjustment() -> None:
    r = budget(
        Scenario(
            tjm=D("100"),
            jours=D("10"),
            gestion=D("10"),
            reserve=D("20"),
            taux_reserve=D("10"),
            ajustement=D("-30"),
        )
    )
    assert r == {
        "chiffre_affaires": D("1000"),
        "gestion": D("100"),
        "reserve": D("110"),
        "budget": D("760"),
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"jours": D("32")},
        {"jours": D("0.3")},
        {"titres": D("21")},
        {"titres": D("1.5")},
        {"mois": "2026-13"},
        {"mois": "2027-01"},
        {"csg_non_deductible": D("30")},
        {"tjm": D("1.001")},
        {"gestion": D("101")},
        {"plafond_frais": D("-1")},
    ],
)
def test_scenario_validation(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Scenario(**changes)


def test_personal_pas_outside_embedded_grid() -> None:
    assert simulate(Scenario(mois="2027-01", taux_pas=D("0")))["pas"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"forfait_gestion": D("99999")},
        {"reserve": D("99999")},
        {"frais": D("99999")},
        {"brut_minimum": D("99999")},
        {"frais": D("2000"), "plafond_frais": D("1")},
        {"tjm": D("1000000")},
    ],
)
def test_impossible_scenarios(changes: dict[str, D]) -> None:
    with pytest.raises(ValueError):
        simulate(Scenario(**changes))


def test_reconciliation_synthetic_fixture() -> None:
    r = reconcile(
        brut=D("3000"),
        cotisations=D("630"),
        csg_non_deductible=D("85.50"),
        pas=D("130"),
        frais=D("400"),
        teletravail=D("40"),
        titres_salarie=D("120"),
    )
    assert r["net_verse"] == D("2560")
    assert r["net_imposable"] == D("2455.50")
    assert (
        reconcile(
            brut=D("100"),
            cotisations=D("20"),
            csg_non_deductible=D("2"),
            pas=D("0"),
            reintegration_fiscale=D("10"),
            autres_retenues=D("3"),
            autres_versements=D("4"),
        )["net_verse"]
        == 81
    )


@pytest.mark.parametrize("gross,contributions,csg", [("1", "2", "0"), ("2", "1", "2")])
def test_reconciliation_refuses_incoherent_totals(gross: str, contributions: str, csg: str) -> None:
    with pytest.raises(ValueError):
        reconcile(
            brut=D(gross), cotisations=D(contributions), csg_non_deductible=D(csg), pas=D("0")
        )


@given(st.integers(0, 1000000), st.integers(0, 10000))
def test_gross_solver_budget_conservation(cents: int, basis_points: int) -> None:
    available = D(cents) / 100
    employer = D(basis_points) / 100
    gross = gross_for_budget(available, employer)
    assert gross + percent(gross, employer) <= available
    assert gross + CENT + percent(gross + CENT, employer) > available


@settings(max_examples=100)
@given(
    st.integers(0, 10000),
    st.integers(0, 10000),
    st.integers(0, 10000),
    st.integers(0, 10000),
    st.integers(0, 400000),
)
def test_net_monotonicity_for_objective(
    employer: int,
    employee: int,
    nondeductible: int,
    pas: int,
    frais: int,
) -> None:
    s = Scenario(
        tjm=D("500"),
        charges_patronales=D(employer) / 100,
        charges_salariales=D(employee) / 100,
        csg_non_deductible=D(min(employee, nondeductible)) / 100,
        taux_pas=D(pas) / 100,
        frais=D(frais) / 100,
    )
    assert simulate(replace(s, frais=s.frais + CENT))["net_verse"] >= simulate(s)["net_verse"]


def test_objective_minimal_cent_and_known_expenses() -> None:
    s = Scenario(
        tjm=D("500"), jours=D("20"), frais=D("100"), plafond_frais=D("80"), brut_minimum=D("1000")
    )
    result = target_expenses(s, D("5500"))
    assert result["net_verse"] >= 5500
    assert simulate(replace(s, frais=result["frais"] - CENT))["net_verse"] < 5500
    assert result["frais_supplementaires"] == result["frais"] - 100
    assert target_expenses(s, D("0"))["frais"] == 0
    assert target_expenses(s, D("0"))["frais_supplementaires"] == 0


def test_objective_unreachable_respects_cap_and_floor() -> None:
    for s in (Scenario(plafond_frais=D("0")), Scenario(brut_minimum=D("6000"))):
        with pytest.raises(ValueError, match="inaccessible"):
            target_expenses(s, D("9000"))


def test_objective_pas_discontinuity_and_exhaustive_oracle() -> None:
    # Small budget so exhaustive enumeration is practical; no binary-search oracle.
    s = Scenario(
        tjm=D("10"),
        jours=D("1"),
        gestion=D("0"),
        taux_pas=D("20"),
        charges_patronales=D("25"),
        charges_salariales=D("20"),
        csg_non_deductible=D("2"),
        plafond_frais=D("50"),
    )
    feasible = []
    for cents in range(1001):
        try:
            feasible.append(simulate(replace(s, frais=D(cents) / 100)))
        except ValueError:
            break
    for cents in range(480, 651, 7):
        expected = next((r for r in feasible if r["net_verse"] >= D(cents) / 100), None)
        if expected is None:
            with pytest.raises(ValueError):
                target_expenses(s, D(cents) / 100)
        else:
            assert target_expenses(s, D(cents) / 100)["frais"] == expected["frais"]


def test_objective_large_budget_respects_input_domain() -> None:
    s = Scenario(
        tjm=D("50000"), jours=D("20"), gestion=D("0"), ajustement=D("1000000"), taux_pas=D("0")
    )
    assert target_expenses(s, D("0"))["frais"] == 0
    # A nonzero objective must also find the bounded valid endpoint.
    assert target_expenses(s, D("1000000"))["net_verse"] >= 1000000
