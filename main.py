import os
import re
from datetime import datetime, time
import httpx
from typing import Optional
import pytz

from fastapi import FastAPI, Query, Depends, HTTPException, status, Body
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import uvicorn

# --- CONFIGURAÇÃO ---
tz_am = pytz.timezone('America/Manaus')
geolocator = Nominatim(user_agent="sentinela_mulher_am_v3")

# Puxa a URL do Render/Ambiente para segurança no GitHub
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://webhook.site/01357d1f-0b8a-4527-884f-41579b128943")

SQLALCHEMY_DATABASE_URL = "sqlite:///./sentinela_mulher.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS ---

class MedidaProtetiva(Base):
    __tablename__ = "medidas_protetivas"
    id = Column(Integer, primary_key=True, index=True)
    processo_id = Column(String, unique=True, index=True)
    nome_vitima = Column(String)
    telefone_vitima = Column(String)
    distancia_minima = Column(Float, default=500.0)
    foto_agressor_url = Column(String, nullable=True)
    data_validade = Column(String)

class HistoricoViolacao(Base):
    __tablename__ = "historico_violacoes"
    id = Column(Integer, primary_key=True, index=True)
    medida_id = Column(Integer, ForeignKey("medidas_protetivas.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(tz_am))
    distancia_detectada = Column(Float)
    lat_agressor = Column(Float)
    long_agressor = Column(Float)
    endereco_aproximado = Column(String)
    medida_vigente_na_hora = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sentinela Mulher + Botão do Pânico AM", version="3.1.0")

# --- FUNÇÕES CORE ---

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def obter_endereco(lat, lon):
    try:
        location = geolocator.reverse(f"{lat}, {lon}", timeout=3)
        return location.address if location else "Endereço não identificado"
    except:
        return "Erro ao obter endereço (Timeout/API)"

def verificar_vigencia(data_str: str) -> bool:
    if not data_str: return False
    try:
        data_limpa = data_str.strip().replace("-", "/")
        agora = datetime.now(tz_am)
        data_exp = datetime.strptime(data_limpa, "%d/%m/%Y")
        data_exp_final = tz_am.localize(datetime.combine(data_exp.date(), time(23, 59, 59)))
        return agora <= data_exp_final
    except:
        return False

# --- FUNÇÃO DE ALERTA INTEGRADA ---

async def disparar_webhook_emergencia(dados: dict):
    """Envia alerta formatado para o canal de segurança."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {
            "content": "⚠️ **NOTIFICAÇÃO DE SEGURANÇA - SISTEMA SENTINELA** ⚠️",
            "embeds": [{
                "title": dados["titulo"],
                "color": dados["cor"],
                "fields": [
                    {"name": "👤 Vítima", "value": dados["vitima"], "inline": True},
                    {"name": "📞 Contato", "value": dados["contato"], "inline": True},
                    {"name": "📍 Localização", "value": dados["endereco"]},
                    {"name": "📏 Distância", "value": dados.get("distancia", "N/A"), "inline": True},
                    {"name": "⚖️ Medida Protetiva", "value": dados["status_juridico"], "inline": True},
                ],
                "image": {"url": dados.get("foto", "")},
                "footer": {"text": f"Manaus/AM - {datetime.now(tz_am).strftime('%d/%m/%Y %H:%M:%S')}"}
            }]
        }
        try:
            await client.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Falha ao enviar Webhook: {e}")

# --- ENDPOINTS ---

@app.post("/botao-panico", tags=["Emergência"])
async def acionar_botao_panico(
    telefone_vitima: str = Body(...),
    lat: float = Body(...),
    long: float = Body(...),
    db: Session = Depends(get_db)
):
    endereco = obter_endereco(lat, long)
    
    # Busca se a vítima tem cadastro para pegar o nome
    cadastro = db.query(MedidaProtetiva).filter(MedidaProtetiva.telefone_vitima.contains(telefone_vitima[-8:])).first()
    nome_vitima = cadastro.nome_vitima if cadastro else "Usuária Não Identificada"

    alerta = {
        "titulo": "🚨 BOTÃO DO PÂNICO ACIONADO 🚨",
        "cor": 15158332, # Vermelho
        "vitima": nome_vitima,
        "contato": telefone_vitima,
        "endereco": endereco,
        "status_juridico": "ACIONAMENTO VOLUNTÁRIO",
        "lat": lat, "long": long
    }
    await disparar_webhook_emergencia(alerta)
    return {"status": "Emergência disparada", "local": endereco}

@app.post("/monitorar", tags=["Operacional"])
async def monitorar_proximidade(
    id_caso: str = Query(...), 
    ag_lat: float = Query(...), ag_long: float = Query(...),
    vi_lat: float = Query(...), vi_long: float = Query(...),
    db: Session = Depends(get_db)
):
    medida = db.query(MedidaProtetiva).filter(MedidaProtetiva.processo_id == id_caso.strip()).first()
    if not medida: raise HTTPException(status_code=404, detail="Processo não encontrado.")

    vigente = verificar_vigencia(medida.data_validade)
    dist = geodesic((ag_lat, ag_long), (vi_lat, vi_long)).meters
    endereco = obter_endereco(ag_lat, ag_long)
    
    if dist <= medida.distancia_minima:
        # Salva histórico
        log = HistoricoViolacao(
            medida_id=medida.id, distancia_detectada=round(dist, 2),
            lat_agressor=ag_lat, long_agressor=ag_long,
            endereco_aproximado=endereco,
            medida_vigente_na_hora="SIM" if vigente else "NÃO"
        )
        db.add(log)
        db.commit()

        # Envia alerta rico
        alerta = {
            "titulo": "⚠️ VIOLAÇÃO DE PERÍMETRO DETECTADA",
            "cor": 16776960, # Amarelo/Laranja
            "vitima": medida.nome_vitima,
            "contato": medida.telefone_vitima,
            "endereco": endereco,
            "distancia": f"{round(dist, 2)}m",
            "status_juridico": "VIGENTE" if vigente else "EXPIRADA (Alerta Preventivo)",
            "foto": medida.foto_agressor_url,
            "lat": ag_lat, "long": ag_long
        }
        await disparar_webhook_emergencia(alerta)

    return {"resultado": "ALERTA" if dist <= medida.distancia_minima else "OK", "local": endereco}

@app.post("/cadastrar-medida", tags=["Administrativo"])
async def cadastrar(processo: str = Body(...), vitima: str = Body(...), telefone: str = Body(...), validade: str = Body(...), raio: float = Body(500.0), foto: str = Body(None), db: Session = Depends(get_db)):
    nova = MedidaProtetiva(processo_id=processo, nome_vitima=vitima, telefone_vitima=telefone, distancia_minima=raio, foto_agressor_url=foto, data_validade=validade)
    db.add(nova)
    db.commit()
    return {"status": "Cadastrado"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
