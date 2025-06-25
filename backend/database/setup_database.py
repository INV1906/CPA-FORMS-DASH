#!/usr/bin/env python3
"""
Setup do banco de dados Firebase
Inicializa o Firebase e cria dados básicos necessários
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.database.firebase_connection import FirebaseManager
from backend.core.config import settings
from datetime import datetime
import hashlib

def hash_password(password: str) -> str:
    """Hash de senha usando SHA-256 (básico para setup)"""
    return hashlib.sha256(password.encode()).hexdigest()

def setup_firebase():
    """Configurar Firebase e dados iniciais"""
    
    print("=== CONFIGURAÇÃO DO FIREBASE ===")
    print(f"Projeto: {settings.FIREBASE_PROJECT_ID}")
    print(f"Firebase habilitado: {settings.FIREBASE_ENABLED}")
    print("")
    
    try:
        # Inicializar Firebase
        firebase_manager = FirebaseManager()
        
        if not firebase_manager.is_connected():
            print("❌ Erro: Firebase não conectado")
            print("Verifique as credenciais no arquivo .env")
            return False
        
        if firebase_manager.is_demo_mode:
            print("⚠️ Firebase em modo DEMO")
            print("Para usar dados reais, configure as credenciais no .env")
        else:
            print("✅ Firebase conectado com credenciais reais")
        
        print("\n=== CRIANDO DADOS INICIAIS ===")
        
        # Verificar se já existe usuário admin
        users_result = firebase_manager.query_collection("usuarios", [("email", "==", "admin@sistema.com")])
        
        if users_result["success"] and len(users_result["data"]) > 0:
            print("✅ Usuário admin já existe")
        else:            # Criar usuário admin
            admin_user = {
                "nome": "Administrador",
                "email": "admin@sistema.com",
                "senha_hash": hash_password("admin123"),
                "cargo": "admin",
                "tipo_usuario": "admin",  # Campo adicional para compatibilidade
                "setor": "TI",
                "ativo": True,
                "ultimo_login": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            result = firebase_manager.create_document("usuarios", admin_user)
            if result["success"]:
                print("✅ Usuário admin criado: admin@sistema.com / admin123")
            else:
                print(f"❌ Erro ao criar usuário admin: {result.get('error')}")
        
        # Criar configurações básicas
        configs = [
            {
                "chave": "sistema_nome",
                "valor": "Sistema de Gestão de Sugestões",
                "descricao": "Nome do sistema",
                "tipo": "texto",
                "categoria": "geral"
            },
            {
                "chave": "versao",
                "valor": "2.0.0",
                "descricao": "Versão do sistema",
                "tipo": "texto",
                "categoria": "geral"
            },
            {
                "chave": "manutencao",
                "valor": "false",
                "descricao": "Modo manutenção",
                "tipo": "boolean",
                "categoria": "sistema"
            }
        ]
        
        for config in configs:
            # Verificar se já existe
            existing = firebase_manager.query_collection("configuracoes", [("chave", "==", config["chave"])])
            
            if existing["success"] and len(existing["data"]) == 0:
                result = firebase_manager.create_document("configuracoes", config)
                if result["success"]:
                    print(f"✅ Configuração criada: {config['chave']}")
                else:
                    print(f"❌ Erro ao criar configuração: {config['chave']}")
        
        print("\n=== SETUP CONCLUÍDO ===")
        print("✅ Firebase configurado com sucesso")
        print("✅ Dados iniciais criados")
        print("✅ Sistema pronto para uso")
        print("")
        print("Credenciais de acesso:")
        print("Email: admin@sistema.com")
        print("Senha: admin123")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante setup: {e}")
        print("\nSoluções possíveis:")
        print("1. Verifique as credenciais Firebase no .env")
        print("2. Verifique se o projeto Firebase existe")
        print("3. Para modo demo, deixe FIREBASE_ENABLED=False")
        return False

def main():
    """Função principal"""
    
    success = setup_firebase()
    
    if success:
        print("\n🎉 Setup concluído com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Setup falhou!")
        sys.exit(1)

if __name__ == "__main__":
    main()