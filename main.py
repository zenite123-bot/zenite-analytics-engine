import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sentry_sdk
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# 1. Configuração de Monitoramento e Banco
sentry_sdk.init(dsn=os.getenv("SENTRY_DSN", ""), traces_sample_rate=1.0)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Configuração do Rate Limiter (Proteção)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Zênite Analytics Engine")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 3. Modelos de Dados
class PredictionResponse(BaseModel):
    event_id: str
    ev_percentage: float
    kelly_criterion: float
    justificativa: str

# 4. Motor Matemático (Kelly Criterion)
def calculate_kelly(probability: float, odds: float) -> float:
    b = odds - 1.0
    p = probability
    q = 1.0 - p
    if b <= 0: return 0.0 
    kelly_fraction = (b * p - q) / b
    return max(0.0, round(kelly_fraction * 100, 2))

# 5. Endpoints
@app.get("/")
def read_root():
    return {"status": "Motor Zênite Conectado ao Banco e Operacional"}

@app.get("/api/v1/engine/prediction/{event_id}", response_model=PredictionResponse)
@limiter.limit("30/minute")
def get_prediction(request: Request, event_id: str):
    # BUSCA REAL NO SUPABASE
    query = supabase.table("eventos_predicao").select("*").eq("event_id", event_id).execute()
    
    if not query.data:
        raise HTTPException(status_code=404, detail="Evento não encontrado no banco Zênite")
    
    dados_evento = query.data[0]
    
    prob = dados_evento['probabilidade_vitoria']
    odds = dados_evento['cotacao_atual']
    
    kelly_pct = calculate_kelly(prob, odds)
    ev = round((prob * odds - 1) * 100, 2)
    
    return PredictionResponse(
        event_id=event_id,
        ev_percentage=ev,
        kelly_criterion=kelly_pct,
        justificativa=dados_evento['justificativa']
    )
