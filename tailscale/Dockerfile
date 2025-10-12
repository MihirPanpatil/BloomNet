FROM tailscale/tailscale:latest

# Install curl for health checks and setup
RUN apk add --no-cache curl

# Create necessary directories
RUN mkdir -p /var/run/tailscale

# Copy setup script
COPY setup.sh /usr/local/bin/setup-tailscale.sh
RUN chmod +x /usr/local/bin/setup-tailscale.sh

# Set up volumes for tailscale state
VOLUME ["/var/lib/tailscale"]

# Run setup script
ENTRYPOINT []
CMD ["/bin/sh", "-c", "/usr/local/bin/setup-tailscale.sh"]