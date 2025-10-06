#!/bin/sh
# Tailscale setup script for Bloom containers

# Exit on error
set -e

# Install Tailscale if not present
if ! command -v tailscale >/dev/null; then
    echo "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

# Ensure the runtime directory exists
mkdir -p /var/run/tailscale

# Start tailscaled in the background
echo "Starting Tailscale daemon..."
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
tailscaled_pid=$!

# Wait for tailscaled to be ready
echo "Waiting for Tailscale daemon to start..."
sleep 5

# Check if we have an auth key
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    echo "ERROR: TAILSCALE_AUTHKEY environment variable is not set"
    echo "Please set it in your .env file and restart the container"
    exit 1
fi

# Join the tailnet
echo "Authenticating with Tailscale..."
tailscale up \
    --authkey="$TAILSCALE_AUTHKEY" \
    --hostname="bloom-$(hostname)" \
    --accept-routes=true \
    --accept-dns=false

# Show status
echo "Tailscale status:"
tailscale status

# Keep the container running
echo "Tailscale setup complete!"
wait $tailscaled_pid