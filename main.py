import os
import re
from datetime import datetime, time
import httpx
from typing import Optional
import pytz

from fastapi import FastAPI, Query, Depends, HTTPException, status, Body
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import uvicorn

# --- CONFIGURAÇÕES ---
tz_am = pytz.timezone('America/Manaus')

# Melhoria: User-Agent único para evitar bloqueios na API de Mapas
geolocator = Nominatim(user_agent="SentinelaMulherAM_SistemaSeguranca_v3")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "import os
import re
from datetime import datetime, time
import httpx
from typing import Optional
import pytz

from fastapi import FastAPI, Query, Depends, HTTPException, status, Body
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import uvicorn

# --- CONFIGURAÇÕES ---
tz_am = pytz.timezone('America/Manaus')

# Melhoria: User-Agent único para evitar bloqueios na API de Mapas
geolocator = Nominatim(user_agent="SentinelaMulherAM_SistemaSeguranca_v3")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://webhook.site/01357d1f-0b8a-4527-884f-41579b128943
Copiar para a área de transferência
")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "seguranca_2026")
SECRET_KEY = os.getenv("SECRET_KEY", "chave_mestra_sentinela_99")

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

app = FastAPI(title="Sentinela Mulher AM - v3.3.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- CACHE SIMPLES PARA EVITAR TIMEOUT DE ENDEREÇO ---
cache_localizacao = {}

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def obter_endereco(lat, lon):
    """Converte coordenadas com lógica de Cache e Retry."""
    chave = f"{round(lat, 4)},{round(lon, 4)}" # Cache por proximidade de 10 metros
    if chave in cache_localizacao:
        return cache_localizacao[chave]

    try:
        # Aumentado timeout para 10 segundos para evitar erro no Render
        location = geolocator.reverse((lat, lon), timeout=10)
        if location:
            addr = location.address
            cache_localizacao[chave] = addr
            return addr
        return "Endereço não identificado"
    except (GeocoderTimedOut, GeocoderServiceError):
        return f"Coordenadas: {lat}, {lon} (Serviço de busca ocupado)"
    except Exception:
        return "Erro na API de Localização"

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

# --- SEGURANÇA ---

@app.post("/token", tags=["Segurança"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == ADMIN_USER and form_data.password == ADMIN_PASSWORD:
        return {"access_token": SECRET_KEY, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorreto")

def verificar_token(token: str = Depends(oauth2_scheme)):
    if token != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Inválido")
    return token

# --- OPERACIONAL ---

async def disparar_webhook(dados: dict):
    if not WEBHOOK_URL: return
    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {
            "content": "⚠️ **ALERTA SENTINELA**",
            "embeds": [{
                "title": dados["titulo"],
                "color": dados["cor"],
                "fields": [
                    {"name": "Vítima", "value": dados["vitima"], "inline": True},
                    {"name": "Local", "value": dados["endereco"]},
                    {"name": "Distância", "value": dados.get("distancia", "N/A"), "inline": True},
                    {"name": "Status", "value": dados["status_juridico"], "inline": True}
                ],
                "image": {"url": dados.get("foto") if dados.get("foto") else ""}
            }]
        }
        try: await client.post(WEBHOOK_URL, json=payload)
        except: pass

@app.post("/monitorar", tags=["Operacional"])
async def monitorar(id_caso: str = Query(...), ag_lat: float = Query(...), ag_long: float = Query(...), vi_lat: float = Query(...), vi_long: float = Query(...), db: Session = Depends(get_db), token: str = Depends(verificar_token)):
    medida = db.query(MedidaProtetiva).filter(MedidaProtetiva.processo_id == id_caso.strip()).first()
    if not medida: raise HTTPException(status_code=404, detail="Não encontrado")

    vigente = verificar_vigencia(medida.data_validade)
    dist = geodesic((ag_lat, ag_long), (vi_lat, vi_long)).meters
    endereco = obter_endereco(ag_lat, ag_long)
    
    if dist <= medida.distancia_minima:
        log = HistoricoViolacao(
            medida_id=medida.id, distancia_detectada=round(dist, 2),
            lat_agressor=ag_lat, long_agressor=ag_long,
            endereco_aproximado=endereco,
            medida_vigente_na_hora="SIM" if vigente else "NÃO"
        )
        db.add(log)
        db.commit()

        await disparar_webhook({
            "titulo": "VIOLAÇÃO DE PERÍMETRO", "cor": 16776960,
            "vitima": medida.nome_vitima, "contato": medida.telefone_vitima,
            "endereco": endereco, "distancia": f"{round(dist, 2)}m",
            "status_juridico": "VIGENTE" if vigente else "EXPIRADA",
            "foto": medida.foto_agressor_url
        })

    return {"resultado": "ALERTA" if dist <= medida.distancia_minima else "OK", "local": endereco}

@app.get("/relatorio-impressao/{processo_id}", response_class=HTMLResponse, tags=["Relatórios"])
async def relatorio(processo_id: str, db: Session = Depends(get_db)):
    medida = db.query(MedidaProtetiva).filter(MedidaProtetiva.processo_id == processo_id.strip()).first()
    if not medida: return "<h1>Erro: Processo não encontrado.</h1>"
    
    vigente = verificar_vigencia(medida.data_validade)
    violacoes = db.query(HistoricoViolacao).filter(HistoricoViolacao.medida_id == medida.id).order_by(HistoricoViolacao.timestamp.desc()).all()
    
    # Foto com Fallback (Se não houver URL, usa uma imagem de silhueta padrão)
    foto_html = f'<img src="{medida.foto_agressor_url}" class="foto" onerror="this.src=\'https://www.w3schools.com/howto/img_avatar.png\';">'
    
    linhas = ""
    for v in violacoes:
        v_cor = "green" if v.medida_vigente_na_hora == "SIM" else "red"
        linhas += f"<tr><td>{v.timestamp.strftime('%d/%m/%Y %H:%M')}</td><td>{v.distancia_detectada}m</td><td>{v.endereco_aproximado}</td><td style='color:{v_cor}'>{v.medida_vigente_na_hora}</td></tr>"

    return f"""
    <html><head><meta charset="UTF-8"><style>
        body {{ font-family: sans-serif; padding: 20px; }}
        .header {{ text-align: center; border-bottom: 5px solid #003366; }}
        .card {{ display: flex; margin-top: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f9f9f9; }}
        .foto {{ width: 150px; height: 180px; object-fit: cover; border: 2px solid #003366; border-radius: 5px; }}
        .info {{ margin-left: 20px; line-height: 1.8; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
        th, td {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
        th {{ background: #003366; color: white; }}
    </style></head>
    <body>
        <div class="header"><h2>SENTINELA MULHER - AM</h2></div>
        <div class="card">
            {foto_html}
            <div class="info">
                <p><b>PROCESSO:</b> {medida.processo_id}</p>
                <p><b>VÍTIMA:</b> {medida.nome_vitima}</p>
                <p><b>VALIDADE:</b> {medida.data_validade} ({'VIGENTE' if vigente else 'EXPIRADA'})</p>
            </div>
        </div>
        <table>
            <thead><tr><th>Data/Hora</th><th>Distância</th><th>Localização</th><th>Vigente?</th></tr></thead>
            <tbody>{linhas or "<tr><td colspan='4'>Sem registros.</td></tr>"}</tbody>
        </table>
    </body></html>
    """

@app.post("/cadastrar-medida", tags=["Administrativo"])
async def cadastrar(processo: str = Body(...), vitima: str = Body(...), telefone: str = Body(...), validade: str = Body(...), raio: float = Body(500.0), foto: str = Body(None), db: Session = Depends(get_db), token: str = Depends(verificar_token)):
    nova = MedidaProtetiva(processo_id=processo, nome_vitima=vitima, telefone_vitima=telefone, distancia_minima=raio, foto_agressor_url=foto, data_validade=validade)
    db.add(nova)
    db.commit()
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "seguranca_am_2026")
SECRET_KEY = os.getenv("SECRET_KEY", "chave_mestra_sentinela_99")

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

app = FastAPI(title="Sentinela Mulher AM - v3.3.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- CACHE SIMPLES PARA EVITAR TIMEOUT DE ENDEREÇO ---
cache_localizacao = {}

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def obter_endereco(lat, lon):
    """Converte coordenadas com lógica de Cache e Retry."""
    chave = f"{round(lat, 4)},{round(lon, 4)}" # Cache por proximidade de 10 metros
    if chave in cache_localizacao:
        return cache_localizacao[chave]

    try:
        # Aumentado timeout para 10 segundos para evitar erro no Render
        location = geolocator.reverse((lat, lon), timeout=10)
        if location:
            addr = location.address
            cache_localizacao[chave] = addr
            return addr
        return "Endereço não identificado"
    except (GeocoderTimedOut, GeocoderServiceError):
        return f"Coordenadas: {lat}, {lon} (Serviço de busca ocupado)"
    except Exception:
        return "Erro na API de Localização"

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

# --- SEGURANÇA ---

@app.post("/token", tags=["Segurança"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == ADMIN_USER and form_data.password == ADMIN_PASSWORD:
        return {"access_token": SECRET_KEY, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorreto")

def verificar_token(token: str = Depends(oauth2_scheme)):
    if token != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Inválido")
    return token

# --- OPERACIONAL ---

async def disparar_webhook(dados: dict):
    if not WEBHOOK_URL: return
    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {
            "content": "⚠️ **ALERTA SENTINELA**",
            "embeds": [{
                "title": dados["titulo"],
                "color": dados["cor"],
                "fields": [
                    {"name": "Vítima", "value": dados["vitima"], "inline": True},
                    {"name": "Local", "value": dados["endereco"]},
                    {"name": "Distância", "value": dados.get("distancia", "N/A"), "inline": True},
                    {"name": "Status", "value": dados["status_juridico"], "inline": True}
                ],
                "image": {"url": dados.get("foto") if dados.get("foto") else ""}
            }]
        }
        try: await client.post(WEBHOOK_URL, json=payload)
        except: pass

@app.post("/monitorar", tags=["Operacional"])
async def monitorar(id_caso: str = Query(...), ag_lat: float = Query(...), ag_long: float = Query(...), vi_lat: float = Query(...), vi_long: float = Query(...), db: Session = Depends(get_db), token: str = Depends(verificar_token)):
    medida = db.query(MedidaProtetiva).filter(MedidaProtetiva.processo_id == id_caso.strip()).first()
    if not medida: raise HTTPException(status_code=404, detail="Não encontrado")

    vigente = verificar_vigencia(medida.data_validade)
    dist = geodesic((ag_lat, ag_long), (vi_lat, vi_long)).meters
    endereco = obter_endereco(ag_lat, ag_long)
    
    if dist <= medida.distancia_minima:
        log = HistoricoViolacao(
            medida_id=medida.id, distancia_detectada=round(dist, 2),
            lat_agressor=ag_lat, long_agressor=ag_long,
            endereco_aproximado=endereco,
            medida_vigente_na_hora="SIM" if vigente else "NÃO"
        )
        db.add(log)
        db.commit()

        await disparar_webhook({
            "titulo": "VIOLAÇÃO DE PERÍMETRO", "cor": 16776960,
            "vitima": medida.nome_vitima, "contato": medida.telefone_vitima,
            "endereco": endereco, "distancia": f"{round(dist, 2)}m",
            "status_juridico": "VIGENTE" if vigente else "EXPIRADA",
            "foto": medida.foto_agressor_url
        })

    return {"resultado": "ALERTA" if dist <= medida.distancia_minima else "OK", "local": endereco}

@app.get("/relatorio-impressao/{processo_id}", response_class=HTMLResponse, tags=["Relatórios"])
async def relatorio(processo_id: str, db: Session = Depends(get_db)):
    medida = db.query(MedidaProtetiva).filter(MedidaProtetiva.processo_id == processo_id.strip()).first()
    if not medida: return "<h1>Erro: Processo não encontrado.</h1>"
    
    vigente = verificar_vigencia(medida.data_validade)
    violacoes = db.query(HistoricoViolacao).filter(HistoricoViolacao.medida_id == medida.id).order_by(HistoricoViolacao.timestamp.desc()).all()
    
    # Foto com Fallback (Se não houver URL, usa uma imagem de silhueta padrão)
    foto_html = f'<img src="{medida.foto_agressor_url}" class="foto" onerror="this.src=\'https://www.w3schools.com/howto/img_avatar.png\';">'
    
    linhas = ""
    for v in violacoes:
        v_cor = "green" if v.medida_vigente_na_hora == "SIM" else "red"
        linhas += f"<tr><td>{v.timestamp.strftime('%d/%m/%Y %H:%M')}</td><td>{v.distancia_detectada}m</td><td>{v.endereco_aproximado}</td><td style='color:{v_cor}'>{v.medida_vigente_na_hora}</td></tr>"

    return f"""
    <html><head><meta charset="UTF-8"><style>
        body {{ font-family: sans-serif; padding: 20px; }}
        .header {{ text-align: center; border-bottom: 5px solid #003366; }}
        .card {{ display: flex; margin-top: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f9f9f9; }}
        .foto {{ width: 150px; height: 180px; object-fit: cover; border: 2px solid #003366; border-radius: 5px; }}
        .info {{ margin-left: 20px; line-height: 1.8; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
        th, td {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
        th {{ background: #003366; color: white; }}
    </style></head>
    <body>
        <div class="header"><h2>SENTINELA MULHER - AM</h2></div>
        <div class="card">
            {foto_html}
            <div class="info">
                <p><b>PROCESSO:</b> {medida.processo_id}</p>
                <p><b>VÍTIMA:</b> {medida.nome_vitima}</p>
                <p><b>VALIDADE:</b> {medida.data_validade} ({'VIGENTE' if vigente else 'EXPIRADA'})</p>
            </div>
        </div>
        <table>
            <thead><tr><th>Data/Hora</th><th>Distância</th><th>Localização</th><th>Vigente?</th></tr></thead>
            <tbody>{linhas or "<tr><td colspan='4'>Sem registros.</td></tr>"}</tbody>
        </table>
    </body></html>
    """

@app.post("/cadastrar-medida", tags=["Administrativo"])
async def cadastrar(processo: str = Body(...), vitima: str = Body(...), telefone: str = Body(...), validade: str = Body(...), raio: float = Body(500.0), foto: str = Body(None), db: Session = Depends(get_db), token: str = Depends(verificar_token)):
    nova = MedidaProtetiva(processo_id=processo, nome_vitima=vitima, telefone_vitima=telefone, distancia_minima=raio, foto_agressor_url=foto, data_validade=validade)
    db.add(nova)
    db.commit()
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
