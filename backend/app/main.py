from fastapi import FastAPI, HTTPException, Depends, status, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from app.models import CalculatorInput, CalculatorResult, UserCreate
from app.services.calculator_service import CalculatorService
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import mercadopago
from datetime import datetime, timedelta
from typing import Optional

load_dotenv()

# Inicializar Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = None

if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

# Inicializar Mercado Pago
mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
mp = None
if mp_access_token:
    mp = mercadopago.SDK(mp_access_token)

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

# ==================== PRO SUBSCRIPTION ROUTES ====================

@app.get("/api/subscription/status")
async def get_subscription_status(current_user: dict = Depends(get_current_user)):
    """
    Retorna status da assinatura PRO do usuário
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database não configurado"
        )
    
    try:
        # Buscar informações do usuário
        user_result = supabase.table("users").select(
            "is_pro, subscription_status, subscription_plan, subscription_end_date"
        ).eq("id", current_user["id"]).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_data = user_result.data[0]
        
        # Verificar se assinatura expirou
        is_expired = False
        if user_data.get("subscription_end_date"):
            end_date = datetime.fromisoformat(user_data["subscription_end_date"].replace("Z", "+00:00"))
            is_expired = end_date < datetime.now()
            
            if is_expired and user_data.get("is_pro"):
                # Atualizar status se expirou
                supabase.table("users").update({
                    "is_pro": False,
                    "subscription_status": "expired"
                }).eq("id", current_user["id"]).execute()
                user_data["is_pro"] = False
                user_data["subscription_status"] = "expired"
        
        return {
            "is_pro": user_data.get("is_pro", False),
            "status": user_data.get("subscription_status", "free"),
            "plan": user_data.get("subscription_plan"),
            "end_date": user_data.get("subscription_end_date"),
            "is_expired": is_expired
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao verificar status: {str(e)}"
        )

@app.post("/api/subscription/create-preference")
async def create_payment_preference(
    plan_type: str,  # 'monthly' ou 'annual'
    current_user: dict = Depends(get_current_user)
):
    """
    Cria preferência de pagamento no Mercado Pago
    """
    if not mp:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mercado Pago não configurado"
        )
    
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database não configurado"
        )
    
    # Validar tipo de plano
    if plan_type not in ["monthly", "annual"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de plano inválido. Use 'monthly' ou 'annual'"
        )
    
    # Definir preços
    prices = {
        "monthly": 29.90,
        "annual": 299.00
    }
    
    price = prices[plan_type]
    plan_name = "Mensal" if plan_type == "monthly" else "Anual"
    
    try:
        # Buscar dados do usuário
        user_result = supabase.table("users").select("email, full_name").eq("id", current_user["id"]).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user_data = user_result.data[0]
        
        # Criar preferência de pagamento
        preference_data = {
            "items": [
                {
                    "title": f"FreelaBR PRO - Plano {plan_name}",
                    "quantity": 1,
                    "unit_price": price,
                    "currency_id": "BRL"
                }
            ],
            "payer": {
                "email": user_data["email"],
                "name": user_data["full_name"]
            },
            "back_urls": {
                "success": f"{os.getenv('FRONTEND_URL')}/payment-success",
                "failure": f"{os.getenv('FRONTEND_URL')}/payment-failure",
                "pending": f"{os.getenv('FRONTEND_URL')}/payment-pending"
            },
            "auto_return": "approved",
            "external_reference": f"{current_user['id']}|{plan_type}",
            "notification_url": f"{os.getenv('BACKEND_URL', 'https://freelabr-backend.onrender.com')}/api/subscription/webhook",
            "statement_descriptor": "FREELABR PRO",
            "metadata": {
                "user_id": current_user["id"],
                "plan_type": plan_type
            }
        }
        
        # Criar preferência no Mercado Pago
        preference_response = mp.preference().create(preference_data)
        preference = preference_response["response"]
        
        return {
            "preference_id": preference["id"],
            "init_point": preference["init_point"],
            "sandbox_init_point": preference.get("sandbox_init_point")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar preferência: {str(e)}"
        )

@app.post("/api/subscription/webhook")
async def mercadopago_webhook(request: Request):
    """
    Recebe notificações de pagamento do Mercado Pago
    """
    if not mp or not supabase:
        return {"status": "service_unavailable"}
    
    try:
        # Pegar dados do webhook
        data = await request.json()
        
        # Mercado Pago envia o tipo da notificação
        if data.get("type") == "payment":
            payment_id = data["data"]["id"]
            
            # Buscar informações do pagamento
            payment_info = mp.payment().get(payment_id)
            payment = payment_info["response"]
            
            # Verificar se pagamento foi aprovado
            if payment["status"] == "approved":
                # Extrair user_id e plan_type do external_reference
                external_ref = payment.get("external_reference", "")
                if "|" in external_ref:
                    user_id, plan_type = external_ref.split("|")
                    
                    # Calcular data de expiração
                    start_date = datetime.now()
                    if plan_type == "monthly":
                        end_date = start_date + timedelta(days=30)
                    else:  # annual
                        end_date = start_date + timedelta(days=365)
                    
                    # Atualizar usuário para PRO
                    supabase.table("users").update({
                        "is_pro": True,
                        "subscription_status": "active",
                        "subscription_plan": plan_type,
                        "subscription_start_date": start_date.isoformat(),
                        "subscription_end_date": end_date.isoformat(),
                        "mercadopago_customer_id": payment.get("payer", {}).get("id")
                    }).eq("id", user_id).execute()
                    
                    # Criar registro de assinatura
                    subscription_data = {
                        "user_id": user_id,
                        "plan_type": plan_type,
                        "plan_price": payment["transaction_amount"],
                        "status": "active",
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "mercadopago_payment_id": str(payment_id)
                    }
                    supabase.table("subscriptions").insert(subscription_data).execute()
                    
                    # Criar registro de pagamento
                    payment_data = {
                        "user_id": user_id,
                        "subscription_id": None,  # Será preenchido depois
                        "amount": payment["transaction_amount"],
                        "status": "approved",
                        "payment_method": payment.get("payment_method_id"),
                        "mercadopago_payment_id": str(payment_id),
                        "mercadopago_status": payment["status"],
                        "mercadopago_status_detail": payment.get("status_detail"),
                        "paid_at": datetime.now().isoformat()
                    }
                    supabase.table("payments").insert(payment_data).execute()
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Erro no webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/api/subscription/cancel")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """
    Cancela assinatura PRO do usuário
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database não configurado"
        )
    
    try:
        # Atualizar status da assinatura
        supabase.table("users").update({
            "subscription_status": "canceled"
        }).eq("id", current_user["id"]).execute()
        
        # Atualizar assinatura ativa
        supabase.table("subscriptions").update({
            "status": "canceled",
            "canceled_at": datetime.now().isoformat()
        }).eq("user_id", current_user["id"]).eq("status", "active").execute()
        
        return {"message": "Assinatura cancelada com sucesso"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao cancelar assinatura: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
