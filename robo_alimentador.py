import os
import json
import requests
from dotenv import load_dotenv

# 1. Carrega as senhas do seu arquivo .env
load_dotenv()

# Pegamos as credenciais e limpamos qualquer barra extra no final da URL
SUPABASE_URL = os.getenv("SUPABASE_URL").rstrip('/')
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

def rodar_robo_alimentador():
    # Definimos que queremos o Brasileirão
    sport_key = 'soccer_brazil_campeonato' 
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'eu',
        'markets': 'h2h',
        'bookmakers': 'pinnacle',
    }

    print("🤖 Robô Zênite iniciado. Buscando jogos na The Odds API...")
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"❌ Erro ao conectar na API de Odds: {response.text}")
        return

    jogos = response.json()
    print(f"⚽ Encontrados {len(jogos)} jogos. Processando dados...")

    for jogo in jogos:
        event_id = jogo['id']
        nome_evento = f"{jogo['home_team']} vs {jogo['away_team']}"
        
        if not jogo.get('bookmakers'):
            continue
            
        mercado = jogo['bookmakers'][0]['markets'][0]
        time_mandante = jogo['home_team']
        odd_mandante = next((opcao['price'] for opcao in mercado['outcomes'] if opcao['name'] == time_mandante), None)

        if odd_mandante:
            prob_implicita = round(1 / odd_mandante, 3)

            # Preparamos os dados exatamente como a sua tabela no Supabase espera
            dados_banco = {
                "event_id": event_id,
                "nome_evento": nome_evento,
                "probabilidade_vitoria": prob_implicita,
                "cotacao_atual": odd_mandante,
                "justificativa": f"Coleta automática Zênite para {time_mandante}."
            }

            # AJUSTE DEFINITIVO DO ENDEREÇO (Sem duplicar /rest/v1)
            # Se sua URL já tem /rest/v1, aqui apenas apontamos para a tabela
            supabase_endpoint = f"{SUPABASE_URL}/eventos_predicao"
            
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates" # Isso faz o 'upsert' (atualiza se já existir)
            }

            try:
                res = requests.post(supabase_endpoint, headers=headers, json=dados_banco)
                if res.status_code in [200, 201]:
                    print(f"✅ Salvo com sucesso: {nome_evento}")
                else:
                    print(f"⚠️ Erro do Supabase ao salvar {nome_evento}: {res.text}")
            except Exception as e:
                print(f"⚠️ Erro de conexão ao salvar {nome_evento}: {e}")

    print("🏁 Robô Zênite finalizou a varredura com sucesso!")

if __name__ == "__main__":
    rodar_robo_alimentador()