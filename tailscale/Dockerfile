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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run setup script
ENTRYPOINT []
CMD ["/bin/sh", "-c", "/usr/local/bin/setup-tailscale.sh"]