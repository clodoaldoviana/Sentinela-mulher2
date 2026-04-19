# 🛡️ Sentinela Mulher + Botão do Pânico (Amazonas)

O **Sentinela Mulher** é uma plataforma de segurança pública inteligente desenvolvida para o monitoramento ativo de Medidas Protetivas de Urgência. O sistema combina geofencing preditivo com uma ferramenta de resposta imediata (Botão do Pânico), integrando dados geográficos e jurídicos para a proteção de mulheres em situação de vulnerabilidade.

## 🚀 Funcionalidades Principais

* **Inteligência Preditiva (Sentinela):** Monitora em tempo real a distância entre agressor e vítima.
* **Botão do Pânico Universal:** Acionamento de emergência que funciona independentemente da vigência da medida judicial.
* **Geocodificação Reversa:** Converte coordenadas (Latitude/Longitude) em endereços legíveis (Rua, Bairro, Cidade) para facilitar a ação policial.
* **Relatórios Periciais:** Geração de documentos em HTML/PDF com histórico de violações para uso judicial.
* **Alertas Ricos (Webhooks):** Notificações formatadas enviadas instantaneamente para centros de comando (Discord/Slack/Telegram) com foto do agressor e mapa.

## 🛠️ Tecnologias Utilizadas

* **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python)
* **Banco de Dados:** SQLite (Desenvolvimento) / PostgreSQL (Produção)
* **Geolocalização:** [GeoPy](https://geopy.readthedocs.io/)
* **Segurança:** OAuth2 + Variáveis de Ambiente
* **Deploy:** Render.com
* **Documentação:** Swagger UI (Automática)

## 📦 Como Instalar e Rodar

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/sentinela-mulher.git](https://github.com/seu-usuario/sentinela-mulher.git)
   cd sentinela_mulher