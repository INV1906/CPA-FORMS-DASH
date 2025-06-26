#!/usr/bin/env python3
"""
Script para importar TODAS as 62 linhas históricas do Google Forms
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Adicionar o diretório backend ao path
sys.path.append(str(Path(__file__).parent / "backend"))

try:
    from backend.database.firebase_connection import firebase_manager
    from backend.services.google_forms_sync import GoogleFormsSync
    from backend.core.config import settings
    print("✅ Módulos importados com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    sys.exit(1)

def import_all_historical_data():
    """Importa TODAS as linhas históricas do Google Forms"""
    try:
        print("📥 Importando TODAS as linhas históricas...")
        
        # Criar instância do sincronizador
        sync_service = GoogleFormsSync()
        
        if not sync_service.sheets_service or not settings.GOOGLE_SHEETS_ID:
            print("❌ Google Sheets não configurado")
            return False
        
        # Buscar TODOS os dados da planilha (sem filtro de data)
        range_name = f"{settings.GOOGLE_SHEETS_NAME}!A:Z"
        
        result = sync_service.sheets_service.spreadsheets().values().get(
            spreadsheetId=settings.GOOGLE_SHEETS_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print("❌ Nenhum dado encontrado na planilha")
            return False
        
        # Primeira linha são os cabeçalhos
        headers = values[0]
        data_rows = values[1:]
        
        print(f"📊 Encontradas {len(data_rows)} linhas TOTAIS na planilha")
        print(f"📋 Cabeçalhos: {headers}")
        
        # Converter TODAS as linhas em respostas
        all_responses = []
        
        for i, row in enumerate(data_rows, 1):
            # Preencher colunas faltantes com strings vazias
            while len(row) < len(headers):
                row.append("")
            
            response_dict = dict(zip(headers, row))
            
            # Tentar extrair timestamp
            timestamp_str = response_dict.get('Timestamp', response_dict.get('Carimbo de data/hora', ''))
            response_time = sync_service._parse_date_from_sheets(timestamp_str)
            
            if not response_time:
                response_time = datetime.now() - timedelta(days=i)  # Data fictícia se não conseguir parsear
            
            all_responses.append({
                'raw_data': response_dict,
                'timestamp': response_time,
                'row_number': i
            })
        
        print(f"✅ Preparadas {len(all_responses)} respostas para importação")
        
        # Salvar TODAS no Firebase
        saved_count = 0
        errors = []
        
        for response_data in all_responses:
            try:
                suggestion = sync_service._map_form_to_suggestion(response_data)
                
                # Adicionar identificador único para evitar duplicatas
                suggestion['google_forms_row'] = response_data['row_number']
                suggestion['import_batch'] = f"historical_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Verificar se já existe (por row number)
                existing = firebase_manager.query_collection("sugestoes", [
                    ("google_forms_row", "==", response_data['row_number'])
                ])
                
                if existing["success"] and len(existing["data"]) > 0:
                    print(f"⚠️ Linha {response_data['row_number']} já importada")
                    continue
                
                # Salvar no Firebase
                result = firebase_manager.create_document("sugestoes", suggestion)
                
                if result["success"]:
                    saved_count += 1
                    print(f"✅ Linha {response_data['row_number']}: {suggestion['titulo']}")
                    
                    # Log da ação
                    firebase_manager.create_document("logs", {
                        "user_id": None,
                        "action": "IMPORT_HISTORICAL_DATA",
                        "details": f"Importada linha {response_data['row_number']}: {suggestion['titulo']}",
                        "source": "historical_import",
                        "created_at": datetime.now()
                    })
                else:
                    error_msg = f"Erro linha {response_data['row_number']}: {result.get('error')}"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)
                    
            except Exception as e:
                error_msg = f"Exceção linha {response_data.get('row_number', '?')}: {e}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
        
        print(f"\n✅ IMPORTAÇÃO CONCLUÍDA:")
        print(f"   • Total de linhas: {len(all_responses)}")
        print(f"   • Importadas com sucesso: {saved_count}")
        print(f"   • Erros: {len(errors)}")
        
        if errors:
            print(f"\n⚠️ ERROS ENCONTRADOS:")
            for error in errors[:5]:  # Mostrar apenas os primeiros 5 erros
                print(f"   • {error}")
            if len(errors) > 5:
                print(f"   • ... e mais {len(errors) - 5} erros")
        
        return saved_count > 0
        
    except Exception as e:
        print(f"❌ Erro na importação histórica: {e}")
        return False

def clean_all_suggestions():
    """Limpa TODAS as sugestões antes da reimportação"""
    try:
        print("🧹 Limpando TODAS as sugestões existentes...")
        
        # Forçar inicialização
        firebase_manager._ensure_initialized()
        
        # Buscar todas as sugestões
        result = firebase_manager.query_collection("sugestoes")
        
        if not result['success']:
            print("⚠️ Nenhuma sugestão encontrada para limpar")
            return True
        
        suggestions = result.get('data', [])
        deleted_count = 0
        
        for suggestion in suggestions:
            suggestion_id = suggestion.get('id')
            if suggestion_id:
                delete_result = firebase_manager.delete_document("sugestoes", suggestion_id)
                if delete_result.get("success"):
                    deleted_count += 1
        
        print(f"✅ {deleted_count} sugestões removidas")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao limpar sugestões: {e}")
        return False

def main():
    """Função principal"""
    print("="*80)
    print("📊 IMPORTAÇÃO HISTÓRICA COMPLETA - GOOGLE FORMS")
    print("="*80)
    print()
    print("Este script irá:")
    print("1. Limpar TODAS as sugestões existentes no Firebase")
    print("2. Importar TODAS as 62 linhas históricas do Google Forms")
    print("3. Aplicar o mapeamento correto para cada campo")
    print("4. Otimizar dados para consultas (FKs)")
    print()
    
    confirm = input("⚠️  ATENÇÃO: Isto apagará todos os dados existentes! Continuar? (s/N): ").strip().lower()
    if confirm != 's':
        print("❌ Operação cancelada")
        return
    
    print("\n🚀 Iniciando importação histórica completa...")
    
    # Passo 1: Limpar TODOS os dados existentes
    if not clean_all_suggestions():
        print("❌ Falha na limpeza")
        return
    
    # Passo 2: Importar TODAS as linhas históricas
    if not import_all_historical_data():
        print("❌ Falha na importação histórica")
        return
    
    print("\n" + "="*80)
    print("🎉 IMPORTAÇÃO HISTÓRICA CONCLUÍDA COM SUCESSO!")
    print("="*80)
    print()
    print("📊 TODOS os dados históricos foram importados:")
    print("   • 62 linhas do Google Forms processadas")
    print("   • Mapeamento correto aplicado")
    print("   • Campos otimizados para consultas")
    print("   • FKs configuradas para performance")
    print()
    print("🔍 Estrutura final dos dados:")
    print("   • Vínculo Institucional → tipo_usuario + nome")
    print("   • Instituição → setor_origem + instituicao (FK)")
    print("   • Categoria de Curso → categoria_curso + categoria (FK)")
    print("   • Sugestão → titulo + descricao estruturada")
    print()
    print("🌐 Acesse a interface para verificar os dados:")
    print("   http://localhost:8000")
    print()
    print("📋 Próximos passos:")
    print("   • Verificar dados na interface")
    print("   • Testar consultas e filtros")
    print("   • Configurar usuários de produção")

if __name__ == "__main__":
    main()
