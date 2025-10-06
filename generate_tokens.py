#!/usr/bin/env python3
"""
BloomNet Token Generator
Generates JWT tokens for all services and updates the .env file
"""

import os
import sys
import jwt
import secrets
from datetime import datetime, timedelta
from pathlib import Path

def generate_jwt_token(node_id: str, role: str, secret: str, expiration_days: int = 30):
    """Generate a JWT token for a specific node/role"""
    payload = {
        'sub': f'node:{node_id}',
        'role': role,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=expiration_days)
    }

    token = jwt.encode(payload, secret, algorithm='HS256')
    return token

def main():
    """Main function to generate all tokens"""

    # Load environment file
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ Error: .env file not found!")
        print("Please create a .env file with at least KERNEL_JWT_SECRET")
        sys.exit(1)

    # Read existing .env content
    with open(env_path, 'r') as f:
        env_content = f.read()

    # Get or generate kernel secret
    if 'KERNEL_JWT_SECRET=' in env_content:
        # Extract existing secret
        for line in env_content.split('\n'):
            if line.startswith('KERNEL_JWT_SECRET='):
                kernel_secret = line.split('=', 1)[1].strip('"\'')
                break
        else:
            kernel_secret = secrets.token_hex(32)
    else:
        kernel_secret = secrets.token_hex(32)
        print(f"⚠️  KERNEL_JWT_SECRET not found in .env, generated new one: {kernel_secret}")

    print("🔐 BloomNet Token Generator")
    print("==========================")
    print(f"Using Kernel Secret: {kernel_secret[:16]}...")
    print("")

    # Define all services that need tokens
    services = [
        # Kernels
        ('kernel1', 'kernel'),
        ('kernel2', 'kernel'),
        ('kernel3', 'kernel'),

        # Photos Mart
        ('photos-parent', 'node'),
        ('photos-child-a', 'node'),
        ('photos-child-b', 'node'),

        # Research Mart
        ('research-parent', 'node'),
        ('research-child-a', 'node'),
        ('research-child-b', 'node'),

        # Clients Mart
        ('clients-parent', 'node'),
        ('clients-child-a', 'node'),
        ('clients-child-b', 'node'),

        # Portal
        ('bloom-portal', 'portal'),
    ]

    # Generate tokens for each service
    generated_tokens = {}
    for node_id, role in services:
        token_key = f"{node_id.upper().replace('-', '_')}_TOKEN"
        token = generate_jwt_token(node_id, role, kernel_secret)
        generated_tokens[token_key] = token
        print(f"✅ Generated {token_key}: {token[:32]}...")

    print(f"\n🎉 Generated {len(services)} tokens successfully!")
    print("")

    # Update .env file
    print("📝 Updating .env file...")

    # Remove existing token lines
    lines = env_content.split('\n')
    filtered_lines = []
    for line in lines:
        if not any(line.startswith(f"{service.upper().replace('-', '_')}_TOKEN=") for service, _ in services):
            filtered_lines.append(line)

    # Add new tokens
    for token_key, token in generated_tokens.items():
        filtered_lines.append(f'{token_key}={token}')

    # Write back to .env
    with open(env_path, 'w') as f:
        f.write('\n'.join(filtered_lines))

    print("✅ .env file updated with new tokens!")
    print("")
    print("🚀 Next steps:")
    print("   1. Review the generated tokens in .env")
    print("   2. Start the services: docker compose up --build -d")
    print("   3. Test the system: ./test_system.sh")
    print("   4. Ingest sample data: ./ingest_all.sh")

if __name__ == "__main__":
    main()
