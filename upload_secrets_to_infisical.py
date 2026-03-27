#!/usr/bin/env python3
"""
Helper script to upload secrets from .env file to Infisical.

Usage:
    python upload_secrets_to_infisical.py

Requirements:
    - .env file with INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET, INFISICAL_PROJECT_ID
    - infisicalsdk package installed
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from infisical_sdk import InfisicalSDKClient

# Load environment variables
load_dotenv()

# Secrets to upload
SECRETS_TO_UPLOAD = [
    # Voice & Speech Services
    "DEEPGRAM_API_KEY",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",

    # LiveKit
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",

    # OpenAI & Azure
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_MODEL",
    "OPENAI_API_TYPE",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_SPEECH_API_KEY",
    "AZURE_SPEECH_REGION",

    # Weaviate
    "WEAVIATE_URL",
    "WEAVIATE_API_KEY",

    # Langfuse
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",

    # Additional secrets from your .env
    "GOOGLE_API_KEY",
    "MURF_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "LIVEKIT_ROOM_NAME",
    "DEV",

    # ElevenLabs TTS parameters
    "ELEVENLABS_SPEED_EN",
    "ELEVENLABS_STABILITY_EN",
    "ELEVENLABS_SIMILARITY_BOOST_EN",
    "ELEVENLABS_STYLE_EN",
    "ELEVENLABS_SPEED_KO",
    "ELEVENLABS_STABILITY_KO",
    "ELEVENLABS_SIMILARITY_BOOST_KO",
    "ELEVENLABS_STYLE_KO"
]


def validate_infisical_config():
    """Validate that Infisical configuration is present."""
    required = ["INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET", "INFISICAL_PROJECT_ID"]
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print("❌ Error: Missing Infisical configuration!")
        print(f"   Please set the following in your .env file:")
        for var in missing:
            print(f"   - {var}")
        return False
    return True


def upload_secrets(dry_run=False):
    """Upload secrets from environment to Infisical."""

    # Validate configuration
    if not validate_infisical_config():
        return False

    # Get Infisical configuration
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    environment = os.getenv("INFISICAL_ENVIRONMENT", "dev")
    host = os.getenv("INFISICAL_HOST", "https://app.infisical.com")
    secret_path = os.getenv("INFISICAL_SECRET_PATH", "/")

    print("=" * 80)
    print("Infisical Secret Upload Script")
    print("=" * 80)
    print(f"Host:        {host}")
    print(f"Project ID:  {project_id}")
    print(f"Environment: {environment}")
    print(f"Path:        {secret_path}")
    print(f"Dry Run:     {dry_run}")
    print("=" * 80)
    print()

    # Initialize Infisical client
    try:
        print("🔐 Authenticating with Infisical...")
        client = InfisicalSDKClient(host=host)
        client.auth.universal_auth.login(
            client_id=client_id,
            client_secret=client_secret
        )
        print("✅ Successfully authenticated with Infisical")
        print()
    except Exception as e:
        print(f"❌ Failed to authenticate with Infisical: {e}")
        return False

    # Collect secrets to upload
    secrets_to_upload = {}
    missing_secrets = []

    for secret_name in SECRETS_TO_UPLOAD:
        value = os.getenv(secret_name)
        if value and value != f"your_{secret_name.lower()}":
            secrets_to_upload[secret_name] = value
        else:
            missing_secrets.append(secret_name)

    # Show summary
    print(f"📊 Summary:")
    print(f"   Secrets to upload: {len(secrets_to_upload)}")
    print(f"   Missing/skipped:   {len(missing_secrets)}")
    print()

    if missing_secrets:
        print("⚠️  Missing secrets (will be skipped):")
        for secret in missing_secrets:
            print(f"   - {secret}")
        print()

    if not secrets_to_upload:
        print("❌ No secrets found to upload. Please check your .env file.")
        return False

    # Ask for confirmation
    if not dry_run:
        print(f"⚠️  About to upload {len(secrets_to_upload)} secrets to Infisical.")
        response = input("   Continue? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("Aborted.")
            return False
        print()

    # Upload secrets
    print("📤 Uploading secrets to Infisical...")
    print()

    success_count = 0
    error_count = 0

    for secret_name, secret_value in secrets_to_upload.items():
        if dry_run:
            print(f"[DRY RUN] Would upload: {secret_name}")
            success_count += 1
            continue

        try:
            # Try to create the secret
            client.secrets.create_secret_by_name(
                secret_name=secret_name,
                secret_value=secret_value,
                project_id=project_id,
                environment_slug=environment,
                secret_path=secret_path
            )
            print(f"✅ Uploaded: {secret_name}")
            success_count += 1

        except Exception as create_error:
            # If creation fails, try to update
            error_msg = str(create_error)
            if "already exists" in error_msg.lower():
                try:
                    client.secrets.update_secret_by_name(
                        current_secret_name=secret_name,
                        secret_value=secret_value,
                        project_id=project_id,
                        environment_slug=environment,
                        secret_path=secret_path
                    )
                    print(f"✅ Updated: {secret_name}")
                    success_count += 1
                except Exception as update_error:
                    print(f"❌ Failed to update {secret_name}: {update_error}")
                    error_count += 1
            else:
                print(f"❌ Failed to upload {secret_name}: {create_error}")
                error_count += 1

    # Final summary
    print()
    print("=" * 80)
    print("📊 Upload Summary")
    print("=" * 80)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed:     {error_count}")
    print(f"⏭️  Skipped:    {len(missing_secrets)}")
    print("=" * 80)

    if error_count == 0 and success_count > 0:
        print()
        print("🎉 All secrets uploaded successfully!")
        print()
        print("Next steps:")
        print("1. Verify secrets in Infisical dashboard")
        print("2. Start your Docker containers: docker-compose up")
        print("3. Check logs to confirm Infisical connection")
        return True
    elif error_count > 0:
        print()
        print("⚠️  Some secrets failed to upload. Please check the errors above.")
        return False
    else:
        return True


def main():
    """Main entry point."""
    # Check if .env file exists
    if not Path(".env").exists():
        print("❌ Error: .env file not found!")
        print("   Please create a .env file with your secrets.")
        print("   You can copy from .env.example: cp .env.example .env")
        sys.exit(1)

    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("Running in DRY RUN mode (no changes will be made)")
        print()

    # Upload secrets
    success = upload_secrets(dry_run=dry_run)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
