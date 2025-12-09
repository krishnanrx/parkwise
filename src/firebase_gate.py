"""
Firebase Realtime Database integration for boom barrier control
Controls gate1 (entry) and gate2 (exit) based on ANPR detection
"""
import os
import json
import time
from datetime import datetime
from typing import Dict, Any
import logging

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None
    db = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirebaseGateControl:
    def __init__(self):
        """Initialize Firebase connection for gate control"""
        self.app = None
        self.connected = False
        self.gate1_ref = None
        self.gate2_ref = None
        self.connect()
    
    def connect(self):
        """Connect to Firebase Realtime Database"""
        try:
            if firebase_admin is None:
                logger.error("Firebase Admin SDK not installed. Run: pip install firebase-admin")
                return False
            
            # Load from environment variables or .env file
            # Try to load from .env file in project root if it exists
            project_root = os.path.dirname(os.path.dirname(__file__))
            env_path = os.path.join(project_root, ".env")
            env_vars = {}
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            # Handle both KEY=value and KEY="value" formats
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Remove quotes if present
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            # Replace \n with actual newlines
                            value = value.replace('\\n', '\n')
                            env_vars[key] = value
            
            # Get Firebase credentials from environment or .env file
            def get_env(key, default=''):
                # First check environment, then .env file
                return os.getenv(key, env_vars.get(key, default))
            
            # Firebase configuration
            private_key = get_env('FIREBASE_PRIVATE_KEY', '')
            # Ensure private key has proper newlines (already handled in parsing, but double-check)
            if private_key and '\\n' in private_key:
                private_key = private_key.replace('\\n', '\n')
            
            firebase_config = {
                "type": "service_account",
                "project_id": "agrovate-e981b",
                "private_key_id": get_env('FIREBASE_PRIVATE_KEY_ID'),
                "private_key": private_key,
                "client_email": get_env('FIREBASE_CLIENT_EMAIL'),
                "client_id": get_env('FIREBASE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": get_env('FIREBASE_CLIENT_CERT_URL')
            }
            
            # Check if credentials are available
            if not firebase_config.get('private_key') or not firebase_config.get('client_email'):
                logger.warning("Firebase credentials not found in environment. Gate control will be disabled.")
                return False
            
            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:
                cred = credentials.Certificate(firebase_config)
                self.app = firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://agrovate-e981b-default-rtdb.asia-southeast1.firebasedatabase.app/'
                })
            
            # Get database references
            self.gate1_ref = db.reference('/gate1')
            self.gate2_ref = db.reference('/gate2')
            
            self.connected = True
            logger.info("✅ Firebase connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Firebase connection failed: {e}")
            self.connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if Firebase is connected"""
        return self.connected and self.gate1_ref is not None and self.gate2_ref is not None
    
    def open_entry_gate(self) -> bool:
        """Open entry gate (gate1)"""
        if not self.is_connected():
            logger.error("Firebase not connected")
            return False
        
        try:
            self.gate1_ref.set(True)
            logger.info("🚪 Entry gate opened (gate1: true)")
            return True
        except Exception as e:
            logger.error(f"Failed to open entry gate: {e}")
            return False
    
    def close_entry_gate(self) -> bool:
        """Close entry gate (gate1)"""
        if not self.is_connected():
            logger.error("Firebase not connected")
            return False
        
        try:
            self.gate1_ref.set(False)
            logger.info("🚪 Entry gate closed (gate1: false)")
            return True
        except Exception as e:
            logger.error(f"Failed to close entry gate: {e}")
            return False
    
    def open_exit_gate(self) -> bool:
        """Open exit gate (gate2)"""
        if not self.is_connected():
            logger.error("Firebase not connected")
            return False
        
        try:
            self.gate2_ref.set(True)
            logger.info("🚪 Exit gate opened (gate2: true)")
            return True
        except Exception as e:
            logger.error(f"Failed to open exit gate: {e}")
            return False
    
    def close_exit_gate(self) -> bool:
        """Close exit gate (gate2)"""
        if not self.is_connected():
            logger.error("Firebase not connected")
            return False
        
        try:
            self.gate2_ref.set(False)
            logger.info("🚪 Exit gate closed (gate2: false)")
            return True
        except Exception as e:
            logger.error(f"Failed to close exit gate: {e}")
            return False
    
    def get_gate_status(self) -> Dict[str, bool]:
        """Get current gate status"""
        if not self.is_connected():
            return {"gate1": False, "gate2": False}
        
        try:
            gate1_status = self.gate1_ref.get() or False
            gate2_status = self.gate2_ref.get() or False
            return {"gate1": gate1_status, "gate2": gate2_status}
        except Exception as e:
            logger.error(f"Failed to get gate status: {e}")
            return {"gate1": False, "gate2": False}
    
    def process_gate_control(self, vehicle_number: str, camera_type: str, matched: bool) -> bool:
        """
        Process gate control based on detection result
        
        Args:
            vehicle_number: Detected license plate
            camera_type: "in" or "out" (entry/exit)
            matched: True if plate matched in database
            
        Returns:
            True if gate control successful
        """
        if not matched:
            logger.debug(f"Gate not opened for {vehicle_number} - Plate not in database")
            return False
        
        camera_type_lower = camera_type.lower()
        if camera_type_lower in ('in', 'entry'):
            return self.open_entry_gate()
        elif camera_type_lower in ('out', 'exit'):
            return self.open_exit_gate()
        else:
            logger.warning(f"Unknown camera type: {camera_type}. Use 'in' or 'out'")
            return False


# Global Firebase instance (lazy initialization)
_firebase_control = None


def get_firebase_control() -> FirebaseGateControl:
    """Get or create Firebase gate control instance"""
    global _firebase_control
    if _firebase_control is None:
        _firebase_control = FirebaseGateControl()
    return _firebase_control


def control_gate(vehicle_number: str, camera_type: str, matched: bool) -> bool:
    """
    Convenience function to control gates
    
    Args:
        vehicle_number: Detected license plate
        camera_type: "in" or "out" (entry/exit)
        matched: True if plate matched in database
        
    Returns:
        True if gate control successful
    """
    firebase = get_firebase_control()
    return firebase.process_gate_control(vehicle_number, camera_type, matched)


def get_gate_status() -> Dict[str, bool]:
    """Get current gate status"""
    firebase = get_firebase_control()
    return firebase.get_gate_status()

