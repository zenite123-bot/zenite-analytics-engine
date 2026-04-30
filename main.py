import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sentry_sdk

# 1. Configuração do Sentry (Monitoramento de Erros)
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", ""),
    traces_sample_rate=1.0,
)

# 2. Configuração do Rate Limiter (Proteção do Servidor contra ataques)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Zênite Analytics Engine")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 3. Modelos de Dados (O que o FlutterFlow vai ler)
class PredictionResponse(BaseModel):
    event_id: str
    ev_percentage: float
    kelly_criterion: float
    justificativa: str

# 4. Motor Matemático (Cálculo do Kelly Criterion)
def calculate_kelly(probability: float, odds: float) -> float:
    b = odds - 1.0
    p = probability
    q = 1.0 - p
    kelly_fraction = (b * p - q) / b
    # Se a vantagem for negativa, a recomendação é 0 (não apostar)
    return max(0.0, round(kelly_fraction * 100, 2))

# 5. Endpoints (As rotas da API)
@app.get("/")
def read_root():
    return {"status": "Motor Zênite Analytics Operacional e Protegido"}

@app.get("/api/v1/engine/prediction/{event_id}", response_model=PredictionResponse)
@limiter.limit("30/minute") # Limita a 30 requisições por minuto por IP
def get_prediction(request: Request, event_id: str):
    # Valores de exemplo simulando o banco de dados (será conectado ao Supabase depois)
    probabilidade_vitoria = 0.65  # 65% de chance
    cotacao = 2.10                # Odds
    
    kelly_pct = calculate_kelly(probabilidade_vitoria, cotacao)
    ev = round((probabilidade_vitoria * cotacao - 1) * 100, 2)
    
    return PredictionResponse(
        event_id=event_id,
        ev_percentage=ev,
        kelly_criterion=kelly_pct,
        justificativa="Alta probabilidade de vitória baseada no histórico recente do mandante e desfalques do visitante."
    )
