"""
Serviço de sincronização do Google Forms/Sheets para Firebase
Importa sugestões em tempo real do Google Forms
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
import logging

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from backend.database.firebase_connection import firebase_manager
from backend.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleFormsSync:
    """Serviço de sincronização Google Forms → Firebase"""
    
    def __init__(self):
        self.credentials = None
        self.sheets_service = None
        self.last_sync_file = Path(settings.LAST_SYNC_TIMESTAMP_FILE)
        self.last_sync_file.parent.mkdir(exist_ok=True)
        self._initialize_google_client()
    
    def _initialize_google_client(self):
        """Inicializar cliente Google Sheets"""
        if not GOOGLE_AVAILABLE:
            logger.warning("Google API client não disponível. Instale: pip install google-api-python-client google-auth")
            return
        
        credentials_file = Path(settings.GOOGLE_CREDENTIALS_FILE)
        if not credentials_file.exists():
            logger.warning(f"Arquivo de credenciais não encontrado: {credentials_file}")
            return
        
        try:
            # Carregar credenciais
            self.credentials = Credentials.from_service_account_file(
                str(credentials_file),
                scopes=settings.GOOGLE_SHEETS_SCOPES
            )
            
            # Criar serviço
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            logger.info("✅ Cliente Google Sheets inicializado")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Google Sheets: {e}")
    
    def _get_last_sync_timestamp(self) -> datetime:
        """Obter timestamp da última sincronização"""
        try:
            if self.last_sync_file.exists():
                with open(self.last_sync_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.error(f"Erro ao ler timestamp: {e}")
        
        # Se não conseguir ler, usar 24h atrás como padrão
        return datetime.now() - timedelta(hours=24)
    
    def _save_last_sync_timestamp(self, timestamp: datetime):
        """Salvar timestamp da última sincronização"""
        try:
            with open(self.last_sync_file, 'w') as f:
                f.write(timestamp.isoformat())
        except Exception as e:
            logger.error(f"Erro ao salvar timestamp: {e}")
    
    def _parse_date_from_sheets(self, date_str: str) -> Optional[datetime]:
        """Converter data do Google Sheets para datetime"""
        if not date_str:
            return None
        
        # Formatos comuns do Google Forms
        formats = [
            "%d/%m/%Y %H:%M:%S",  # 24/06/2025 14:30:00
            "%m/%d/%Y %H:%M:%S",  # 06/24/2025 14:30:00
            "%Y-%m-%d %H:%M:%S",  # 2025-06-24 14:30:00
            "%d/%m/%Y",           # 24/06/2025
            "%m/%d/%Y",           # 06/24/2025
            "%Y-%m-%d"            # 2025-06-24
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Não foi possível converter data: {date_str}")
        return datetime.now()
    
    def fetch_new_responses(self) -> List[Dict[str, Any]]:
        """Buscar novas respostas do Google Sheets"""
        if not self.sheets_service or not settings.GOOGLE_SHEETS_ID:
            logger.warning("Google Sheets não configurado")
            return []
        
        try:
            # Buscar dados da planilha
            range_name = f"{settings.GOOGLE_SHEETS_NAME}!A:Z"  # Buscar todas as colunas
            
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=settings.GOOGLE_SHEETS_ID,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                logger.info("Nenhum dado encontrado na planilha")
                return []
            
            # Primeira linha são os cabeçalhos
            headers = values[0]
            data_rows = values[1:]
            
            logger.info(f"Encontradas {len(data_rows)} linhas na planilha")
            
            # Converter em dicionários
            responses = []
            last_sync = self._get_last_sync_timestamp()
            
            for row in data_rows:
                # Preencher colunas faltantes com strings vazias
                while len(row) < len(headers):
                    row.append("")
                
                response_dict = dict(zip(headers, row))
                
                # Verificar se é uma resposta nova
                timestamp_str = response_dict.get('Timestamp', response_dict.get('Carimbo de data/hora', ''))
                response_time = self._parse_date_from_sheets(timestamp_str)
                
                if response_time and response_time > last_sync:
                    responses.append({
                        'raw_data': response_dict,
                        'timestamp': response_time
                    })
            
            logger.info(f"Encontradas {len(responses)} novas respostas desde {last_sync}")
            return responses
            
        except Exception as e:
            logger.error(f"Erro ao buscar respostas: {e}")
            return []
    
    def _map_form_to_suggestion(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mapear dados do formulário para estrutura de sugestão"""
        raw = form_data['raw_data']
        
        suggestion = {
            'timestamp': form_data['timestamp'],
            'created_at': form_data['timestamp'],
            'updated_at': form_data['timestamp'],
            'status': 'pendente',
            'prioridade': 'media',
            'source': 'google_forms'
        }
        
        # Mapeamento específico para seus campos do Google Forms
        # Extrair dados principais
        vinculo = raw.get('Vínculo Institucional', '').strip()
        instituicao = raw.get('A qual instituição de ensino está vinculado?', '').strip()
        categoria_curso = raw.get('Qual categoria de curso está vinculado?', '').strip()
        descricao_sugestao = raw.get('Informe aqui sua sugestão:', '').strip()
        
        # Mapear vínculo institucional para tipo de usuário
        if vinculo == 'Aluno':
            suggestion['nome'] = 'Aluno'
            suggestion['tipo_usuario'] = 'aluno'
        elif vinculo == 'Colaborador':
            suggestion['nome'] = 'Colaborador'
            suggestion['tipo_usuario'] = 'colaborador'
        else:
            suggestion['nome'] = vinculo if vinculo else 'Usuário Anônimo'
            suggestion['tipo_usuario'] = 'externo'
        
        # Mapear instituição para setor de origem
        if instituicao == 'Biopark Educação':
            suggestion['setor_origem'] = 'Biopark Educação'
            suggestion['instituicao'] = 'biopark'
        elif instituicao == 'Uniamérica':
            suggestion['setor_origem'] = 'Uniamérica'
            suggestion['instituicao'] = 'uniamerica'
        else:
            suggestion['setor_origem'] = instituicao if instituicao else 'Outra Instituição'
            suggestion['instituicao'] = 'outra'
        
        # Mapear categoria do curso
        if categoria_curso in ['Pós-Graduação', 'Graduação', 'Técnico']:
            suggestion['categoria_curso'] = categoria_curso.lower().replace('-', '_')
            suggestion['categoria'] = categoria_curso
        else:
            suggestion['categoria_curso'] = 'outro'
            suggestion['categoria'] = categoria_curso if categoria_curso else 'Outro'
        
        # Dados principais da sugestão
        suggestion['titulo'] = f"Sugestão - {vinculo} {categoria_curso}".strip()
        suggestion['descricao'] = descricao_sugestao if descricao_sugestao else 'Sem descrição'
        
        # Campos adicionais
        suggestion['email'] = f"{vinculo.lower()}@{suggestion['instituicao']}.edu"
        suggestion['setor_destino'] = 'Gestão Acadêmica'
        suggestion['tipo_sugestao'] = 'Sugestão de Melhoria'
        
        # Dados estruturados para consultas otimizadas
        suggestion['dados_estruturados'] = {
            'vinculo_institucional': vinculo,
            'instituicao_ensino': instituicao,
            'categoria_curso': categoria_curso,
            'sugestao_completa': descricao_sugestao
        }
        
        return suggestion
    
    def save_suggestions_to_firebase(self, suggestions: List[Dict[str, Any]]) -> int:
        """Salvar sugestões no Firebase"""
        saved_count = 0
        
        for suggestion_data in suggestions:
            try:
                suggestion = self._map_form_to_suggestion(suggestion_data)
                
                # Verificar se já existe (evitar duplicatas)
                existing = firebase_manager.query_collection("sugestoes", [
                    ("email", "==", suggestion['email']),
                    ("titulo", "==", suggestion['titulo']),
                    ("created_at", "==", suggestion['created_at'])
                ])
                
                if existing["success"] and len(existing["data"]) > 0:
                    logger.info(f"Sugestão já existe: {suggestion['titulo']}")
                    continue
                
                # Salvar no Firebase
                result = firebase_manager.create_document("sugestoes", suggestion)
                
                if result["success"]:
                    saved_count += 1
                    logger.info(f"✅ Sugestão salva: {suggestion['titulo']}")
                    
                    # Log da ação
                    firebase_manager.create_document("logs", {
                        "user_id": None,
                        "action": "IMPORT_SUGGESTION",
                        "details": f"Importada sugestão via Google Forms: {suggestion['titulo']}",
                        "source": "google_forms_sync",
                        "created_at": datetime.now()
                    })
                else:
                    logger.error(f"Erro ao salvar sugestão: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Erro ao processar sugestão: {e}")
        
        return saved_count
    
    def sync_now(self) -> Dict[str, Any]:
        """Executar sincronização manual"""
        logger.info("🔄 Iniciando sincronização Google Forms...")
        
        if not settings.AUTO_SYNC_ENABLED:
            return {"success": False, "message": "Sincronização desabilitada"}
        
        try:
            # Buscar novas respostas
            new_responses = self.fetch_new_responses()
            
            if not new_responses:
                return {
                    "success": True,
                    "message": "Nenhuma nova resposta encontrada",
                    "imported": 0
                }
            
            # Salvar no Firebase
            saved_count = self.save_suggestions_to_firebase(new_responses)
            
            # Atualizar timestamp
            self._save_last_sync_timestamp(datetime.now())
            
            logger.info(f"✅ Sincronização concluída: {saved_count} sugestões importadas")
            
            return {
                "success": True,
                "message": f"Sincronização concluída com sucesso",
                "imported": saved_count,
                "total_found": len(new_responses)
            }
            
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            return {
                "success": False,
                "message": f"Erro na sincronização: {str(e)}"
            }
    
    async def start_background_sync(self):
        """Iniciar sincronização em background"""
        if not settings.AUTO_SYNC_ENABLED:
            logger.info("Sincronização automática desabilitada")
            return
        
        logger.info(f"🔄 Iniciando sincronização automática (intervalo: {settings.SYNC_INTERVAL}s)")
        
        while True:
            try:
                result = self.sync_now()
                if result["success"] and result["imported"] > 0:
                    logger.info(f"✅ Auto-sync: {result['imported']} sugestões importadas")
                
                await asyncio.sleep(settings.SYNC_INTERVAL)
                
            except Exception as e:
                logger.error(f"Erro no auto-sync: {e}")
                await asyncio.sleep(60)  # Aguardar 1 minuto antes de tentar novamente

# Instância global
google_forms_sync = GoogleFormsSync()
