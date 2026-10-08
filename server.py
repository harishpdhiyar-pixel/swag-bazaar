import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from waitress import serve
from app import app, init_db

if __name__ == '__main__':
    init_db()
    
    port = int(os.environ.get('PORT', 5000))
    threads = int(os.environ.get('THREADS', 8))
    
    print("=" * 60)
    print("🛡️  SWAG BAZAAR - PRODUCTION SERVER STARTED (WAITRESS)")
    print("=" * 60)
    print(f"🔒 सुरक्षा: Brute-Force Defense + Cryptographic PIN Hash + Headers")
    print(f"⚡ थ्रेड्स: {threads} Concurrent Workers (High Traffic Ready)")
    print(f"👉 स्टोर लाइव URL: http://127.0.0.1:{port}")
    print(f"👉 एडमिन पोर्टल:   http://127.0.0.1:{port}/admin")
    print("=" * 60)
    
    # Run multi-threaded production server
    serve(app, host='0.0.0.0', port=port, threads=threads, channel_timeout=30)
