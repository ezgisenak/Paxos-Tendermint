FROM prom/prometheus:latest

USER root

# Create the internal data directory Prometheus needs
RUN mkdir -p /prometheus

# Fix permissions for the TSDB data folder
RUN chown nobody:nogroup /prometheus

# Create config directory (safe)
RUN mkdir -p /etc/prometheus

# Copy your configuration file inside
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Set correct permissions
RUN chmod 644 /etc/prometheus/prometheus.yml

# Switch back to nobody user (security best practice)
USER nobody
