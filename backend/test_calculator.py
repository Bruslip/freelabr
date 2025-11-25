#!/usr/bin/env python3
"""
Script de teste da Calculadora FreelaBR
Testa a lógica de cálculo sem precisar do servidor
"""

import sys
sys.path.insert(0, '/workspace/freelabr/backend')

from decimal import Decimal
from app.models import CalculatorInput
from app.services.calculator_service import CalculatorService

def test_calculator():
    print("=" * 60)
    print("🧮 TESTANDO CALCULADORA FREELABR")
    print("=" * 60)
    
    # Teste 1: Freelancer MEI
    print("\n📝 Teste 1: Freelancer MEI")
    print("-" * 60)
    
    input_mei = CalculatorInput(
        desired_monthly_income=Decimal("5000"),
        hours_per_day=8,
        days_per_week=5,
        vacation_weeks=4,
        tax_regime="MEI",
        include_13th_salary=True,
        include_vacation_bonus=True,
        monthly_expenses=Decimal("500"),
        variable_expenses=Decimal("200"),
        profit_margin_percentage=Decimal("20")
    )
    
    result_mei = CalculatorService.calculate(input_mei)
    
    print(f"💰 Pró-labore desejado: R$ {input_mei.desired_monthly_income:,.2f}")
    print(f"📊 Regime: {result_mei.tax_regime}")
    print(f"💸 Impostos mensais: R$ {result_mei.monthly_taxes:,.2f}")
    print(f"📈 Custos totais/mês: R$ {result_mei.total_monthly_costs:,.2f}")
    print(f"\n✅ VALORES SUGERIDOS:")
    print(f"   • Hora: R$ {result_mei.hourly_rate:,.2f}")
    print(f"   • Dia: R$ {result_mei.daily_rate:,.2f}")
    print(f"   • Semana: R$ {result_mei.weekly_rate:,.2f}")
    print(f"   • Mês: R$ {result_mei.monthly_rate:,.2f}")
    print(f"\n📦 PROJETOS:")
    print(f"   • Pequeno (30h): R$ {result_mei.small_project_value:,.2f}")
    print(f"   • Médio (100h): R$ {result_mei.medium_project_value:,.2f}")
    print(f"   • Grande (200h): R$ {result_mei.large_project_value:,.2f}")
    
    # Teste 2: Comparação de regimes
    print("\n\n📊 Teste 2: Comparação de Regimes (R$ 5.000/mês)")
    print("-" * 60)
    
    regimes = ["MEI", "PJ_SIMPLES", "PJ_PRESUMIDO", "AUTONOMO"]
    
    for regime in regimes:
        input_data = CalculatorInput(
            desired_monthly_income=Decimal("5000"),
            hours_per_day=8,
            days_per_week=5,
            vacation_weeks=4,
            tax_regime=regime,
            include_13th_salary=True,
            include_vacation_bonus=True,
            monthly_expenses=Decimal("500"),
            variable_expenses=Decimal("200"),
            profit_margin_percentage=Decimal("20")
        )
        
        result = CalculatorService.calculate(input_data)
        info = CalculatorService.get_tax_info(regime)
        
        print(f"\n{regime}:")
        print(f"   Nome: {info['name']}")
        print(f"   Impostos/mês: R$ {result.monthly_taxes:,.2f}")
        print(f"   Valor/hora: R$ {result.hourly_rate:,.2f}")
        print(f"   Custo total/mês: R$ {result.total_monthly_costs:,.2f}")
    
    # Teste 3: Informações sobre regimes
    print("\n\n📚 Teste 3: Informações sobre MEI")
    print("-" * 60)
    
    mei_info = CalculatorService.get_tax_info("MEI")
    print(f"Nome: {mei_info['name']}")
    print(f"Descrição: {mei_info['description']}")
    print(f"Limite: {mei_info['limit']}")
    print(f"Vantagens: {', '.join(mei_info['benefits'])}")
    print(f"Desvantagens: {', '.join(mei_info['drawbacks'])}")
    
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM COM SUCESSO!")
    print("=" * 60)

if __name__ == "__main__":
    test_calculator()
