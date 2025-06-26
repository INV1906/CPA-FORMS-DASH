"""
Firebase Firestore connection with lazy initialization
"""

import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Optional, Any
import os
from datetime import datetime
import json
from pathlib import Path
from backend.core.config import settings

class MockFirestore:
    """Mock Firestore for demo purposes"""
    
    def __init__(self):
        self.data = {
            "usuarios": [
                {
                    "id": "admin_user_123",
                    "nome": "Administrador",
                    "email": "admin@sistema.com",
                    "senha_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # admin123
                    "tipo_usuario": "admin",
                    "cargo": "admin",
                    "setor": "TI",
                    "ativo": True,
                    "ultimo_login": None,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            ],
            "configuracoes": [
                {
                    "id": "config_1",
                    "chave": "sistema_nome",
                    "valor": "Sistema de Gestão de Sugestões",
                    "descricao": "Nome do sistema",
                    "tipo": "texto",
                    "categoria": "geral",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            ],
            "sugestoes": [],
            "logs": []
        }
    
    def query_collection(self, collection: str, filters: Optional[List[tuple]] = None):
        """Mock query collection"""
        data = self.data.get(collection, [])
        
        if filters:
            for field, operator, value in filters:
                if operator == "==":
                    data = [item for item in data if item.get(field) == value]
        
        return {"success": True, "data": data}
    
    def create_document(self, collection: str, data: Dict[str, Any]):
        """Mock create document"""
        doc_id = f"{collection}_{len(self.data.get(collection, []))}"
        data['id'] = doc_id
        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        
        if collection not in self.data:
            self.data[collection] = []
        
        self.data[collection].append(data)
        return {"success": True, "id": doc_id}
    
    def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]):
        """Mock update document"""
        collection_data = self.data.get(collection, [])
        for item in collection_data:
            if item.get('id') == doc_id:
                item.update(data)
                item['updated_at'] = datetime.now()
                return {"success": True}
        return {"success": False, "error": "Document not found"}
    
    def get_document(self, collection: str, doc_id: str):
        """Mock get document"""
        collection_data = self.data.get(collection, [])
        for item in collection_data:
            if item.get('id') == doc_id:
                return {"success": True, "data": item}
        return {"success": False, "error": "Document not found"}
    
    def delete_document(self, collection: str, doc_id: str):
        """Mock delete document"""
        collection_data = self.data.get(collection, [])
        for i, item in enumerate(collection_data):
            if item.get('id') == doc_id:
                del collection_data[i]
                return {"success": True}
        return {"success": False, "error": "Document not found"}

class FirebaseManager:
    """Firebase Firestore database manager with lazy initialization"""
    
    def __init__(self):
        self.db = None
        self.is_demo_mode = False
        self._initialized = False
        print("🔥 Firebase Manager criado (inicialização lazy)")
    
    def _ensure_initialized(self):
        """Ensure Firebase is initialized when needed"""
        if self._initialized:
            return
        
        try:
            # Check if Firebase is disabled
            if not settings.FIREBASE_ENABLED:
                print("🔥 Firebase DESABILITADO - usando modo DEMO")
                self.db = MockFirestore()
                self.is_demo_mode = True
                self._initialized = True
                return
                
            # Check for demo/mock mode
            if (settings.FIREBASE_PRIVATE_KEY_ID == "dummy_key_id_for_testing" or 
                "DUMMY" in settings.FIREBASE_PRIVATE_KEY):
                print("🔥 Firebase em modo DEMO (sem credenciais reais)")
                self.db = MockFirestore()
                self.is_demo_mode = True
                self._initialized = True
                return
            
            # Real Firebase initialization
            print("🔥 Inicializando Firebase real...")
            if not firebase_admin._apps:
                # Try to load from service account key file first
                key_file = Path(settings.FIREBASE_SERVICE_ACCOUNT_FILE)
                
                if key_file.exists():
                    print("🔄 Usando arquivo de credenciais...")
                    try:
                        cred = credentials.Certificate(str(key_file))
                        firebase_admin.initialize_app(cred, {
                            'projectId': settings.FIREBASE_PROJECT_ID
                        })
                        print("✅ Firebase inicializado com arquivo de credenciais")
                    except Exception as e:
                        print(f"❌ Erro ao carregar arquivo de credenciais: {e}")
                        raise e
                else:
                    print("🔄 Usando variáveis de ambiente...")
                    # Validate required environment variables
                    if not all([
                        settings.FIREBASE_PRIVATE_KEY_ID,
                        settings.FIREBASE_PRIVATE_KEY,
                        settings.FIREBASE_CLIENT_EMAIL,
                        settings.FIREBASE_CLIENT_ID
                    ]):
                        raise ValueError("Credenciais Firebase incompletas nas variáveis de ambiente")
                    
                    # Initialize with environment variables
                    service_account_info = {
                        "type": "service_account",
                        "project_id": settings.FIREBASE_PROJECT_ID,
                        "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
                        "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                        "client_email": settings.FIREBASE_CLIENT_EMAIL,
                        "client_id": settings.FIREBASE_CLIENT_ID,
                        "auth_uri": settings.FIREBASE_AUTH_URI,
                        "token_uri": settings.FIREBASE_TOKEN_URI,
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.FIREBASE_CLIENT_EMAIL}"
                    }
                    
                    cred = credentials.Certificate(service_account_info)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase inicializado com variáveis de ambiente")
            
            # Get Firestore client
            print("🔄 Criando cliente Firestore...")
            self.db = firestore.client()
            print("✅ Firebase Firestore inicializado com sucesso")
            self._initialized = True
            
        except Exception as e:
            print(f"⚠️  Erro ao inicializar Firebase: {e}")
            print("🔥 Iniciando em modo DEMO")
            self.db = MockFirestore()
            self.is_demo_mode = True
            self._initialized = True
    
    def is_connected(self) -> bool:
        """Check if Firebase is connected"""
        self._ensure_initialized()
        return self.db is not None
    
    def query_collection(self, collection: str, filters: Optional[List[tuple]] = None, 
                        order_by: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Query a collection with optional filters"""
        try:
            self._ensure_initialized()
            
            if not self.is_connected():
                return {"success": False, "error": "Firebase not connected"}
            
            if self.is_demo_mode:
                return self.db.query_collection(collection, filters)
            
            # Real Firebase query logic here
            query = self.db.collection(collection)
            
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            if order_by:
                query = query.order_by(order_by)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            
            data = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                data.append(doc_data)
            
            return {"success": True, "data": data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_document(self, collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new document in a collection"""
        try:
            self._ensure_initialized()
            
            if not self.is_connected():
                return {"success": False, "error": "Firebase not connected"}
            
            if self.is_demo_mode:
                return self.db.create_document(collection, data)
            
            # Real Firebase creation logic
            data['created_at'] = datetime.now()
            data['updated_at'] = datetime.now()
            
            if doc_id:
                doc_ref = self.db.collection(collection).document(doc_id)
                doc_ref.set(data)
                return {"success": True, "id": doc_id, "data": data}
            else:
                doc_ref = self.db.collection(collection).add(data)
                return {"success": True, "id": doc_ref[1].id, "data": data}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_document(self, collection: str, doc_id: str) -> Dict[str, Any]:
        """Get a single document by ID"""
        try:
            self._ensure_initialized()
            
            if not self.is_connected():
                return {"success": False, "error": "Firebase not connected"}
            
            if self.is_demo_mode:
                return self.db.get_document(collection, doc_id)
            
            # Real Firebase get logic
            doc_ref = self.db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return {"success": True, "data": data}
            else:
                return {"success": False, "error": "Document not found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a document"""
        try:
            self._ensure_initialized()
            
            if not self.is_connected():
                return {"success": False, "error": "Firebase not connected"}
            
            if self.is_demo_mode:
                return self.db.update_document(collection, doc_id, data)
            
            # Real Firebase update logic
            data['updated_at'] = datetime.now()
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.update(data)
            
            return {"success": True, "id": doc_id}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_document(self, collection: str, doc_id: str) -> Dict[str, Any]:
        """Delete a document"""
        try:
            self._ensure_initialized()
            
            if not self.is_connected():
                return {"success": False, "error": "Firebase not connected"}
            
            if self.is_demo_mode:
                return self.db.delete_document(collection, doc_id)
            
            # Real Firebase delete logic
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.delete()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Create global instance
firebase_manager = FirebaseManager()
