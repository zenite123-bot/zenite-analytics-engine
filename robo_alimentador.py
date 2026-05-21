import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# 1. Carrega as chaves secretas do arquivo .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip('/')
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") # Certifique-se de ter essa chave no seu .env

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def limpar_jogos_antigos():
    """Limpa a tabela antes de colocar os novos palpites do dia"""
    print("🧹 Limpando jogos antigos do Supabase para atualizar a lista...")
    url_delete = f"{SUPABASE_URL}/rest/v1/eventos_predicao?id=not.is.null"
    try:
        requests.delete(url_delete, headers=HEADERS)
    except Exception as e:
        print(f"Erro ao limpar banco: {e}")

def analisar_jogo_com_gemini(time_casa, time_fora, liga_nome, cotacao_casa):
    """Aciona a Inteligência Artificial para gerar palpites realistas de Gols e Escanteios"""
    print(f"🤖 Inteligência Artificial analisando: {time_casa} x {time_fora}...")
    
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Você é o analista estatístico do aplicativo ZeniteSafeScan. Analise o confronto de futebol:
    Jogo: {time_casa} x {time_fora} pela liga {liga_nome}.
    Cotação atual para vitória do {time_casa}: {cotacao_casa}.

    Gere previsões estritamente baseadas em probabilidades matemáticas para as próximas colunas:
    1. Sugestão de Escanteios (Ex: "Mais de 8.5 escanteios", "Entre 9 e 11 cantos")
    2. Tendência de Gols (Ex: "Mais de 1.5 gols", "Ambos Marcam - Sim", "Jogo truncado, menos de 2.5 gols")
    3. Análise do Jogo (Um resumo de quem tem vantagem ou se tende a empate)

    Responda EXCLUSIVAMENTE em formato JSON puro, sem formatação markdown (sem ```json), exatamente com esta estrutura de chaves:
    {{
        "escanteios": "sua previsao curta aqui",
        "tendencia_gols": "sua tendencia curta aqui",
        "justificativa": "seu resumo curto de analise aqui"
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url_gemini, json=payload)
        if response.status_code == 200:
            texto_ia = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            # Garante a limpeza de caracteres extras que a IA possa colocar
            if texto_ia.startswith("```"):
                texto_ia = texto_ia.split("```")[1].replace("json", "").strip()
            return json.loads(texto_ia)
    except Exception as e:
        print(f"⚠️ Falha na análise da IA: {e}")
        
    # Caso falhe, retorna um padrão seguro para não travar o app
    return {
        "escanteios": "Análise de cantos indisponível",
        "tendencia_gols": "Análise de mercado padrão",
        "justificativa": f"Confronto equilibrado entre {time_casa} e {time_fora}."
    }

def rodar_robo_alimentador():
    limpar_jogos_antigos()
    
    # Campeonatos mundiais e nacionais configurados
    ligas_alvo = [
        {"key": "soccer_brazil_campeonato", "nome": "Brasileirão Série A"},
        {"key": "soccer_uefa_champs_league", "nome": "Champions League"},
        {"key": "soccer_conmebol_libertadores", "nome": "Copa Libertadores"},
        {"key": "soccer_england_league_one", "nome": "Premier League (Inglaterra)"},
        {"key": "soccer_spain_la_liga", "nome": "La Liga (Espanha)"}
    ]
    
    for liga in ligas_alvo:
        print(f"⚽ Buscando rodadas de: {liga['nome']}...")
        url_odds = f"[https://api.the-odds-api.com/v4/sports/](https://api.the-odds-api.com/v4/sports/){liga['key']}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        
        try:
            resposta = requests.get(url_odds)
            if resposta.status_code != 200:
                continue
                
            jogos = resposta.json()
            
            for jogo in jogos:
                event_id = jogo.get("id")
                time_casa = jogo.get("home_team")
                time_fora = jogo.get("away_team")
                nome_evento = f"{time_casa} x {time_fora}"
                
                # Formata Data e Horário
                data_iso = jogo.get("commence_time")
                data_formatada = "Hoje"
                horario_formatado = "--:--"
                if data_iso:
                    try:
                        dt = datetime.strptime(data_iso, "%Y-%m-%dT%H:%M:%SZ")
                        data_formatada = dt.strftime("%d/%m/%Y")
                        horario_formatado = dt.strftime("%H:%M")
                    except Exception:
                        pass
                
                # Extrai as Cotações Básicas
                cotacao_atual = 2.00
                prob_vitoria = 0.50
                try:
                    bookmakers = jogo.get("bookmakers", [])
                    if bookmakers:
                        outcomes = bookmakers[0].get("markets", [])[0].get("outcomes", [])
                        for out in outcomes:
                            if out.get("name") == time_casa:
                                cotacao_atual = float(out.get("price", 2.00))
                                prob_vitoria = round(1 / cotacao_atual, 2)
                except Exception:
                    pass

                # 🤖 CHAMA A INTELIGÊNCIA ARTIFICIAL PARA OS CAMPOS QUE ESTÃO CARREGANDO
                analise_ia = analisar_jogo_com_gemini(time_casa, time_fora, liga["nome"], cotacao_atual)

                # Monta a estrutura batendo exatamente com as colunas do seu Supabase
                dados_jogo = {
                    "event_id": event_id,
                    "nome_evento": nome_evento,
                    "time_casa": time_casa,
                    "time_visitante": time_fora,
                    "probabilidade_vitoria": prob_vitoria,
                    "cotacao_atual": cotacao_atual,
                    "data_jogo": data_formatada,
                    "horario_jogo": horario_formatado,
                    "liga": liga["nome"],
                    "escanteios": analise_ia.get("escanteios"),
                    "tendencia_gols": analise_ia.get("tendencia_gols"),
                    "justificativa": analise_ia.get("justificativa")
                }
                
                # Envia para a tabela eventos_predicao no Supabase
                url_insert = f"{SUPABASE_URL}/rest/v1/eventos_predicao"
                res_ins = requests.post(url_insert, headers=HEADERS, json=dados_jogo)
                
                if res_ins.status_code in [200, 201, 204]:
                    print(f"🚀 Previsões completas salvas para: {nome_evento}")
                else:
                    print(f"⚠️ Erro ao salvar {nome_evento}: {res_ins.text}")
                    
        except Exception as e:
            print(f"Falha de conexão na liga {liga['nome']}: {e}")

if __name__ == "__main__":
    rodar_robo_alimentador()
