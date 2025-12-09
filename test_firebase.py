"""
Test Firebase connection and gate control
Run this to verify Firebase credentials are working
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.firebase_gate import get_firebase_control
import time

def test_firebase():
    print("Testing Firebase connection...")
    print(f"Looking for .env file at: {os.path.join(os.path.dirname(__file__), '.env')}")
    print(f".env file exists: {os.path.exists(os.path.join(os.path.dirname(__file__), '.env'))}\n")
    
    firebase = get_firebase_control()
    
    if not firebase.is_connected():
        print("❌ Firebase connection failed!")
        print("\nTroubleshooting:")
        print("1. Check .env file exists in project root")
        print("2. Verify all Firebase credentials are correct")
        print("3. Check private key format (should have \\n for newlines)")
        print("4. Verify service account has database permissions")
        return False
    
    print("✅ Firebase connected successfully!\n")
    
    # Test gate control
    print("Testing gate control...")
    
    print("\n1. Testing entry gate (gate1)...")
    if firebase.open_entry_gate():
        print("   ✅ Entry gate opened")
        time.sleep(2)
        if firebase.close_entry_gate():
            print("   ✅ Entry gate closed")
    
    print("\n2. Testing exit gate (gate2)...")
    if firebase.open_exit_gate():
        print("   ✅ Exit gate opened")
        time.sleep(2)
        if firebase.close_exit_gate():
            print("   ✅ Exit gate closed")
    
    # Get gate status
    print("\n3. Getting gate status...")
    status = firebase.get_gate_status()
    print(f"   Gate1 (entry): {status['gate1']}")
    print(f"   Gate2 (exit): {status['gate2']}")
    
    print("\n✅ All Firebase tests passed!")
    return True

if __name__ == "__main__":
    test_firebase()

