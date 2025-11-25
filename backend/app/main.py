from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.models import CalculatorInput, CalculatorResult
from app.services.calculator_service import CalculatorService
import os
from dotenv import load_dotenv

load_dotenv()

# Inicializar FastAPI
app = FastAPI(
    title="FreelaBR API",
    description="API completa para gestão de freelancers brasileiros",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== HEALTH CHECK ====================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "FreelaBR API",
        "version": "1.0.0",
        "message": "🚀 API funcionando perfeitamente!"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": "connected"  # Depois vamos adicionar check real do Supabase
    }

# ==================== CALCULATOR ROUTES ====================

@app.post("/api/calculator/calculate", response_model=CalculatorResult)
async def calculate_rates(input_data: CalculatorInput):
    """
    Calcula valores de hora/dia/projeto para freelancer
    Considera impostos brasileiros (MEI, PJ, Autônomo)
    """
    try:
        result = CalculatorService.calculate(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/calculator/tax-info/{tax_regime}")
async def get_tax_info(tax_regime: str):
    """
    Retorna informações sobre regime tributário
    """
    valid_regimes = ["MEI", "PJ_SIMPLES", "PJ_PRESUMIDO", "AUTONOMO"]
    
    if tax_regime not in valid_regimes:
        raise HTTPException(
            status_code=400,
            detail=f"Regime inválido. Use: {', '.join(valid_regimes)}"
        )
    
    info = CalculatorService.get_tax_info(tax_regime)
    return info

@app.get("/api/calculator/compare")
async def compare_tax_regimes(monthly_income: float = 5000):
    """
    Compara custos entre diferentes regimes tributários
    """
    regimes = ["MEI", "PJ_SIMPLES", "PJ_PRESUMIDO", "AUTONOMO"]
    comparisons = []
    
    for regime in regimes:
        input_data = CalculatorInput(
            desired_monthly_income=monthly_income,
            hours_per_day=8,
            days_per_week=5,
            vacation_weeks=4,
            tax_regime=regime,
            include_13th_salary=True,
            include_vacation_bonus=True,
            monthly_expenses=500,
            variable_expenses=200,
            profit_margin_percentage=20
        )
        
        result = CalculatorService.calculate(input_data)
        
        comparisons.append({
            "regime": regime,
            "info": CalculatorService.get_tax_info(regime),
            "monthly_taxes": float(result.monthly_taxes),
            "hourly_rate": float(result.hourly_rate),
            "total_monthly_cost": float(result.total_monthly_costs)
        })
    
    return {
        "monthly_income": monthly_income,
        "comparisons": comparisons
    }

# ==================== EXAMPLES ENDPOINT ====================

@app.get("/api/examples")
async def get_examples():
    """
    Retorna exemplos de cálculos prontos
    """
    examples = [
        {
            "name": "Freelancer Iniciante (MEI)",
            "description": "Desenvolvedor júnior começando como MEI",
            "input": {
                "desired_monthly_income": 3000,
                "hours_per_day": 6,
                "days_per_week": 5,
                "vacation_weeks": 2,
                "tax_regime": "MEI",
                "include_13th_salary": True,
                "include_vacation_bonus": True,
                "monthly_expenses": 300,
                "variable_expenses": 100,
                "profit_margin_percentage": 15
            }
        },
        {
            "name": "Freelancer Intermediário (PJ Simples)",
            "description": "Designer com experiência, PJ Simples",
            "input": {
                "desired_monthly_income": 7000,
                "hours_per_day": 8,
                "days_per_week": 5,
                "vacation_weeks": 4,
                "tax_regime": "PJ_SIMPLES",
                "include_13th_salary": True,
                "include_vacation_bonus": True,
                "monthly_expenses": 800,
                "variable_expenses": 400,
                "profit_margin_percentage": 25
            }
        },
        {
            "name": "Freelancer Sênior (PJ Presumido)",
            "description": "Consultor experiente, faturamento alto",
            "input": {
                "desired_monthly_income": 15000,
                "hours_per_day": 8,
                "days_per_week": 5,
                "vacation_weeks": 6,
                "tax_regime": "PJ_PRESUMIDO",
                "include_13th_salary": True,
                "include_vacation_bonus": True,
                "monthly_expenses": 2000,
                "variable_expenses": 1000,
                "profit_margin_percentage": 30
            }
        }
    ]
    
    # Calcular os resultados
    for example in examples:
        input_data = CalculatorInput(**example["input"])
        result = CalculatorService.calculate(input_data)
        example["result"] = {
            "hourly_rate": float(result.hourly_rate),
            "daily_rate": float(result.daily_rate),
            "monthly_rate": float(result.monthly_rate),
            "small_project": float(result.small_project_value),
            "medium_project": float(result.medium_project_value),
            "large_project": float(result.large_project_value)
        }
    
    return examples

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
