"""
Sistema de Backup e Restore para Firebase
Sistema de Gestão de Sugestões v2.0
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import asyncio

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from backend.database.firebase_connection import firebase_manager

class FirebaseBackupManager:
    """Gerenciador de backup e restore Firebase"""
    
    def __init__(self):
        self.backup_dir = Path("data/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_backup(self, backup_name=None):
        """Cria backup completo do Firebase"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        print(f"📦 Criando backup: {backup_name}")
        print("=" * 50)
        
        if not firebase_manager.is_connected():
            print("❌ Firebase não conectado!")
            return False
        
        backup_data = {
            "metadata": {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "version": "2.0.0",
                "firebase_mode": "demo" if firebase_manager.is_demo_mode else "production"
            },
            "collections": {}
        }
        
        # Coleções para backup
        collections = ["usuarios", "sugestoes", "configuracoes", "setores", "logs", "relatorios"]
        
        for collection in collections:
            print(f"📋 Fazendo backup da coleção: {collection}")
            try:
                result = firebase_manager.query_collection(collection)
                if result.get("success"):
                    data = result.get("data", [])
                    # Converter datetime para string para JSON
                    for item in data:
                        for key, value in item.items():
                            if isinstance(value, datetime):
                                item[key] = value.isoformat()
                    
                    backup_data["collections"][collection] = data
                    print(f"   ✅ {len(data)} documentos salvos")
                else:
                    print(f"   ⚠️ Coleção {collection} vazia ou erro")
                    backup_data["collections"][collection] = []
            except Exception as e:
                print(f"   ❌ Erro no backup de {collection}: {e}")
                backup_data["collections"][collection] = []
        
        # Salvar backup
        backup_file = self.backup_dir / f"{backup_name}.json"
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n✅ Backup criado com sucesso!")
            print(f"📄 Arquivo: {backup_file}")
            print(f"📊 Tamanho: {backup_file.stat().st_size / 1024:.2f} KB")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar backup: {e}")
            return False
    
    async def restore_backup(self, backup_name):
        """Restaura backup do Firebase"""
        backup_file = self.backup_dir / f"{backup_name}.json"
        
        if not backup_file.exists():
            print(f"❌ Backup não encontrado: {backup_file}")
            return False
        
        print(f"🔄 Restaurando backup: {backup_name}")
        print("=" * 50)
        
        if not firebase_manager.is_connected():
            print("❌ Firebase não conectado!")
            return False
        
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            metadata = backup_data.get("metadata", {})
            print(f"📋 Backup criado em: {metadata.get('created_at')}")
            print(f"🔧 Versão: {metadata.get('version')}")
            
            collections = backup_data.get("collections", {})
            
            for collection_name, documents in collections.items():
                print(f"\n📚 Restaurando coleção: {collection_name}")
                
                if not documents:
                    print("   ⚠️ Coleção vazia, pulando...")
                    continue
                
                restored_count = 0
                for doc in documents:
                    try:
                        # Converter strings ISO de volta para datetime
                        for key, value in doc.items():
                            if isinstance(value, str) and 'T' in value and value.endswith('Z') or '+' in value[-6:]:
                                try:
                                    doc[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    pass  # Manter como string se não for datetime válido
                        
                        result = firebase_manager.add_document(collection_name, doc)
                        if result.get("success"):
                            restored_count += 1
                        else:
                            print(f"   ⚠️ Erro ao restaurar documento: {doc.get('id', 'Unknown')}")
                    
                    except Exception as e:
                        print(f"   ❌ Erro no documento: {e}")
                
                print(f"   ✅ {restored_count}/{len(documents)} documentos restaurados")
            
            print(f"\n🎉 Restore concluído!")
            return True
            
        except Exception as e:
            print(f"❌ Erro durante restore: {e}")
            return False
    
    def list_backups(self):
        """Lista backups disponíveis"""
        print("📦 Backups Disponíveis:")
        print("=" * 50)
        
        backup_files = list(self.backup_dir.glob("*.json"))
        
        if not backup_files:
            print("⚠️ Nenhum backup encontrado")
            return []
        
        backups = []
        for backup_file in sorted(backup_files, reverse=True):
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                metadata = backup_data.get("metadata", {})
                size = backup_file.stat().st_size / 1024
                
                backup_info = {
                    "name": backup_file.stem,
                    "file": backup_file.name,
                    "created": metadata.get("created_at", "Unknown"),
                    "size": f"{size:.2f} KB",
                    "version": metadata.get("version", "Unknown"),
                    "mode": metadata.get("firebase_mode", "Unknown")
                }
                
                backups.append(backup_info)
                
                print(f"📄 {backup_info['name']}")
                print(f"   📅 Criado: {backup_info['created']}")
                print(f"   📊 Tamanho: {backup_info['size']}")
                print(f"   🔧 Versão: {backup_info['version']}")
                print(f"   🏭 Modo: {backup_info['mode']}")
                print()
                
            except Exception as e:
                print(f"❌ Erro ao ler {backup_file.name}: {e}")
        
        return backups

async def main():
    """Interface principal"""
    print("🔥 FIREBASE BACKUP MANAGER")
    print("Sistema de Gestão de Sugestões v2.0")
    print("=" * 50)
    
    manager = FirebaseBackupManager()
    
    while True:
        print("\n📋 Opções:")
        print("1. Criar backup")
        print("2. Restaurar backup")
        print("3. Listar backups")
        print("4. Sair")
        
        choice = input("\nEscolha uma opção (1-4): ").strip()
        
        if choice == "1":
            backup_name = input("Nome do backup (Enter para automático): ").strip()
            if not backup_name:
                backup_name = None
            await manager.create_backup(backup_name)
        
        elif choice == "2":
            backups = manager.list_backups()
            if backups:
                backup_name = input("Nome do backup para restaurar: ").strip()
                if backup_name:
                    await manager.restore_backup(backup_name)
            else:
                print("⚠️ Nenhum backup disponível para restaurar")
        
        elif choice == "3":
            manager.list_backups()
        
        elif choice == "4":
            print("👋 Até logo!")
            break
        
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    asyncio.run(main())
