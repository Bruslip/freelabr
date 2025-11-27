from fastapi import FastAPI, HTTPException, Depends, status, Form
from fastapi.middleware.cors import CORSMiddleware
from app.models import CalculatorInput, CalculatorResult, UserCreate
from app.services.calculator_service import CalculatorService
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Inicializar Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = None

if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

# Inicializar FastAPI
app = FastAPI(
    title="FreelaBR API",
    description="API completa para gestão de freelancers brasileiros",
    version="1.0.0"
)

# Configurar CORS - CORRIGIDO
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    frontend_url,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://freelabr.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
        "database": "connected" if supabase else "not_configured"
    }

# ==================== AUTH ROUTES ====================

@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    """
    Registra um novo usuário
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database não configurado. Configure SUPABASE_URL e SUPABASE_ANON_KEY"
        )
    
    try:
        # Verifica se email já existe
        existing = supabase.table("users").select("*").eq("email", user_data.email).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )
        
        # Hash da senha
        hashed_password = AuthService.get_password_hash(user_data.password)
        
        # Insere no banco
        result = supabase.table("users").insert({
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar usuário"
            )
        
        user = result.data[0]
        
        # Cria token
        access_token = AuthService.create_access_token(
            data={"sub": user["id"], "email": user["email"]}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar: {str(e)}"
        )

@app.post("/api/auth/login")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    """
    Faz login e retorna token JWT
    Aceita Form data do frontend HTML
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database não configurado"
        )
    
    try:
        # Busca usuário
        result = supabase.table("users").select("*").eq("email", email).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )
        
        user = result.data[0]
        
        # Verifica senha
        if not AuthService.verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )
        
        # Cria token
        access_token = AuthService.create_access_token(
            data={"sub": user["id"], "email": user["email"]}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer login: {str(e)}"
        )

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Retorna informações do usuário logado
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database não configurado"
        )
    
    try:
        result = supabase.table("users").select("id, email, full_name, created_at").eq("id", current_user["id"]).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar usuário: {str(e)}"
        )

# ✅ NOVO ENDPOINT ADICIONADO
@app.put("/api/auth/update-profile")
async def update_profile(
    update_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza informações do perfil do usuário logado
    Requer senha atual para qualquer alteração
    Permite atualizar: full_name, email, password
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database não configurado"
        )
    
    try:
        # VALIDAR SENHA ATUAL (obrigatória)
        if "current_password" not in update_data or not update_data["current_password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual é obrigatória para fazer alterações"
            )
        
        # Buscar usuário com senha hash
        user_result = supabase.table("users").select("*").eq("id", current_user["id"]).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user = user_result.data[0]
        
        # Verificar se a senha atual está correta
        if not AuthService.verify_password(update_data["current_password"], user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Senha atual incorreta"
            )
        
        # Preparar dados para atualização
        update_fields = {}
        
        # Validar e adicionar campos permitidos
        if "full_name" in update_data and update_data["full_name"]:
            update_fields["full_name"] = update_data["full_name"].strip()
        
        if "email" in update_data and update_data["email"]:
            new_email = update_data["email"].strip().lower()
            
            # Verificar se o novo email já está em uso por outro usuário
            existing = supabase.table("users").select("id").eq("email", new_email).execute()
            if existing.data and existing.data[0]["id"] != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este email já está em uso"
                )
            
            update_fields["email"] = new_email
        
        if "password" in update_data and update_data["password"]:
            # Hash da nova senha
            hashed_password = AuthService.get_password_hash(update_data["password"])
            update_fields["hashed_password"] = hashed_password
        
        # Verificar se há algo para atualizar
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo válido para atualizar"
            )
        
        # Atualizar no banco
        result = supabase.table("users").update(update_fields).eq("id", current_user["id"]).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Retornar dados atualizados (sem senha)
        updated_user = result.data[0]
        return {
            "id": updated_user["id"],
            "email": updated_user["email"],
            "full_name": updated_user["full_name"],
            "message": "Perfil atualizado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar perfil: {str(e)}"
        )

# ==================== CALCULATOR ROUTES ====================

@app.post("/api/calculator/calculate", response_model=CalculatorResult)
async def calculate_rates(input_data: CalculatorInput, current_user: dict = Depends(get_current_user)):
    """
    Calcula valores de hora/dia/projeto para freelancer
    Considera impostos brasileiros (MEI, PJ, Autônomo)
    
    **Requer autenticação**
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
