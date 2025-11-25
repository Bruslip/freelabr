from decimal import Decimal
from app.models import CalculatorInput, CalculatorResult

class CalculatorService:
    """
    Serviço para cálculo de valores de freelancer
    Considera impostos brasileiros por regime tributário
    """
    
    # Valores fixos 2025
    MEI_DAS_VALUE = Decimal("81.90")  # DAS MEI 2025 para serviços
    MINIMUM_WAGE = Decimal("1518.00")  # Salário mínimo 2025
    
    # Alíquotas por regime
    TAX_RATES = {
        "MEI": {
            "fixed_monthly": MEI_DAS_VALUE,
            "percentage": Decimal("0"),  # MEI paga valor fixo
        },
        "PJ_SIMPLES": {
            "percentage": Decimal("6.0"),  # Anexo III - Inicial (até R$ 180k)
        },
        "PJ_PRESUMIDO": {
            "percentage": Decimal("16.33"),  # IR + CSLL + PIS/COFINS + ISS médio
        },
        "AUTONOMO": {
            "inss": Decimal("20.0"),  # INSS autônomo sobre salário mínimo
            "ir_progressive": True,  # IR progressivo
        }
    }
    
    @classmethod
    def calculate(cls, input_data: CalculatorInput) -> CalculatorResult:
        """Calcula todos os valores baseado nos inputs"""
        
        # 1. Calcular horas e dias trabalhados
        working_days_per_week = input_data.days_per_week
        working_weeks_per_year = 52 - input_data.vacation_weeks
        working_days_per_year = working_days_per_week * working_weeks_per_year
        working_days_per_month = working_days_per_year / 12
        
        working_hours_per_day = input_data.hours_per_day
        working_hours_per_month = working_hours_per_day * working_days_per_month
        
        # 2. Calcular impostos mensais
        monthly_taxes = cls._calculate_monthly_taxes(
            input_data.desired_monthly_income,
            input_data.tax_regime
        )
        
        # 3. Calcular provisões (férias e 13º)
        monthly_provisions = Decimal("0")
        if input_data.include_13th_salary:
            monthly_provisions += input_data.desired_monthly_income / 12
        if input_data.include_vacation_bonus:
            monthly_provisions += (input_data.desired_monthly_income / 3) / 12
        
        # 4. Somar custos totais mensais
        total_monthly_costs = (
            input_data.desired_monthly_income +  # Pró-labore
            monthly_taxes +                      # Impostos
            monthly_provisions +                 # Provisões
            input_data.monthly_expenses +        # Despesas fixas
            input_data.variable_expenses         # Despesas variáveis
        )
        
        # 5. Aplicar margem de lucro
        profit_margin = input_data.profit_margin_percentage / 100
        total_monthly_rate = total_monthly_costs / (1 - profit_margin)
        
        # 6. Calcular valores por unidade de tempo
        hourly_rate = total_monthly_rate / Decimal(str(working_hours_per_month))
        daily_rate = hourly_rate * Decimal(str(working_hours_per_day))
        weekly_rate = daily_rate * Decimal(str(working_days_per_week))
        
        # 7. Sugerir valores para projetos
        small_project_value = hourly_rate * Decimal("30")   # ~30h
        medium_project_value = hourly_rate * Decimal("100")  # ~100h
        large_project_value = hourly_rate * Decimal("200")   # ~200h
        
        # 8. Retornar resultado
        return CalculatorResult(
            hourly_rate=hourly_rate.quantize(Decimal("0.01")),
            daily_rate=daily_rate.quantize(Decimal("0.01")),
            weekly_rate=weekly_rate.quantize(Decimal("0.01")),
            monthly_rate=total_monthly_rate.quantize(Decimal("0.01")),
            
            total_monthly_costs=total_monthly_costs.quantize(Decimal("0.01")),
            total_annual_costs=(total_monthly_costs * 12).quantize(Decimal("0.01")),
            monthly_taxes=monthly_taxes.quantize(Decimal("0.01")),
            monthly_provisions=monthly_provisions.quantize(Decimal("0.01")),
            net_monthly_income=input_data.desired_monthly_income,
            
            working_hours_per_month=int(working_hours_per_month),
            working_days_per_month=int(working_days_per_month),
            tax_regime=input_data.tax_regime,
            
            small_project_value=small_project_value.quantize(Decimal("0.01")),
            medium_project_value=medium_project_value.quantize(Decimal("0.01")),
            large_project_value=large_project_value.quantize(Decimal("0.01")),
        )
    
    @classmethod
    def _calculate_monthly_taxes(cls, monthly_income: Decimal, tax_regime: str) -> Decimal:
        """Calcula impostos mensais baseado no regime tributário"""
        
        if tax_regime == "MEI":
            # MEI paga valor fixo mensal
            return cls.MEI_DAS_VALUE
        
        elif tax_regime == "PJ_SIMPLES":
            # Simples Nacional - Anexo III (serviços)
            rate = cls.TAX_RATES["PJ_SIMPLES"]["percentage"]
            return monthly_income * (rate / 100)
        
        elif tax_regime == "PJ_PRESUMIDO":
            # Lucro Presumido - alíquota média
            rate = cls.TAX_RATES["PJ_PRESUMIDO"]["percentage"]
            return monthly_income * (rate / 100)
        
        elif tax_regime == "AUTONOMO":
            # Autônomo - INSS + IR progressivo
            inss = cls.MINIMUM_WAGE * Decimal("0.20")  # 20% sobre salário mínimo
            ir = cls._calculate_progressive_ir(monthly_income)
            return inss + ir
        
        return Decimal("0")
    
    @classmethod
    def _calculate_progressive_ir(cls, monthly_income: Decimal) -> Decimal:
        """
        Calcula Imposto de Renda progressivo (Tabela 2025)
        """
        # Tabela IR 2025 (simplificada)
        if monthly_income <= Decimal("2259.20"):
            return Decimal("0")
        elif monthly_income <= Decimal("2828.65"):
            return (monthly_income * Decimal("0.075")) - Decimal("169.44")
        elif monthly_income <= Decimal("3751.05"):
            return (monthly_income * Decimal("0.15")) - Decimal("381.44")
        elif monthly_income <= Decimal("4664.68"):
            return (monthly_income * Decimal("0.225")) - Decimal("662.77")
        else:
            return (monthly_income * Decimal("0.275")) - Decimal("896.00")
    
    @classmethod
    def get_tax_info(cls, tax_regime: str) -> dict:
        """Retorna informações sobre o regime tributário"""
        
        tax_info = {
            "MEI": {
                "name": "Microempreendedor Individual (MEI)",
                "monthly_cost": float(cls.MEI_DAS_VALUE),
                "description": "Valor fixo mensal de R$ 81,90 (DAS 2025)",
                "limit": "Faturamento anual até R$ 81.000",
                "benefits": ["Simples", "Barato", "Poucos obrigações"],
                "drawbacks": ["Limite de faturamento", "Apenas 1 funcionário"]
            },
            "PJ_SIMPLES": {
                "name": "Simples Nacional - Anexo III",
                "percentage": "6% a 33%",
                "description": "Alíquota inicial de 6% sobre faturamento",
                "limit": "Faturamento anual até R$ 4,8 milhões",
                "benefits": ["Menos burocracia", "Alíquota progressiva"],
                "drawbacks": ["Aumenta com faturamento", "Obrigações acessórias"]
            },
            "PJ_PRESUMIDO": {
                "name": "Lucro Presumido",
                "percentage": "~16,33%",
                "description": "IR + CSLL + PIS/COFINS + ISS",
                "limit": "Faturamento anual até R$ 78 milhões",
                "benefits": ["Previsível", "Bom para margens altas"],
                "drawbacks": ["Mais complexo", "Mais caro que Simples inicial"]
            },
            "AUTONOMO": {
                "name": "Autônomo (Pessoa Física)",
                "percentage": "20% INSS + IR progressivo",
                "description": "INSS 20% sobre salário mínimo + IR progressivo",
                "limit": "Sem limite",
                "benefits": ["Flexível", "Sem burocracia"],
                "drawbacks": ["IR progressivo alto", "Menos benefícios"]
            }
        }
        
        return tax_info.get(tax_regime, {})
