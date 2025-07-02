# Grafana Loki Setup for Kurin Bot

This setup provides comprehensive logging and monitoring for the Kurin Telegram Bot using Grafana Loki stack.

## Components

### 1. **Loki** - Log Aggregation
- Collects and stores logs from all containers
- Accessible at: `http://localhost:3100`
- Configuration: `loki/local-config.yaml`

### 2. **Promtail** - Log Collection
- Collects logs from Docker containers
- Sends logs to Loki with proper labeling
- Configuration: `promtail/config.yml`

### 3. **Grafana** - Visualization
- Web interface for viewing logs and dashboards
- Accessible at: `http://localhost:3000`
- Default credentials: `admin / admin123` (changeable via environment)

## Quick Start

1. **Set Grafana Password** (optional):
   ```bash
   echo "GRAFANA_ADMIN_PASSWORD=your_secure_password" >> .env
   ```

2. **Start the Services**:
   ```bash
   docker-compose up -d
   ```

3. **Access Grafana**:
   - Open: http://localhost:3000
   - Login: admin / admin123 (or your custom password)
   - The "Kurin Bot Monitoring Dashboard" will be auto-loaded

## Dashboard Features

### Log Levels Summary
- Overview of INFO, ERROR, WARNING, DEBUG log counts
- Quick identification of error patterns

### Log Rate by Level
- Real-time visualization of log rates over time
- Monitor system activity and identify spikes

### Recent Errors
- Real-time view of error logs
- Detailed error messages with timestamps

### User Registration Rate
- Track new user registrations over time
- Monitor bot adoption

### Book Booking Rate
- Monitor book booking activity
- Track library usage patterns

### System Events
- Key system events (startup, shutdown, successes, failures)
- System health monitoring

## Log Queries

### Useful LogQL Queries

**All bot logs:**
```logql
{container="kurin-telegram-bot"}
```

**Only errors:**
```logql
{container="kurin-telegram-bot"} |~ "ERROR"
```

**User activity:**
```logql
{container="kurin-telegram-bot"} |~ "User [0-9]+"
```

**Book operations:**
```logql
{container="kurin-telegram-bot"} |~ "Book.*booked|Book.*returned"
```

**Database operations:**
```logql
{container="kurin-telegram-bot"} |~ "Database|MySQL"
```

**Google Sheets operations:**
```logql
{container="kurin-telegram-bot"} |~ "Google Sheets|Sheet"
```

## Configuration

### Environment Variables

Add to your `.env` file:
```bash
# Grafana Configuration
GRAFANA_ADMIN_PASSWORD=your_secure_password_here
```

### Loki Configuration
- **Storage**: Uses local filesystem storage
- **Retention**: Default retention policies apply
- **Performance**: Optimized for single-node deployment

### Promtail Configuration
- **Discovery**: Automatically discovers Docker containers
- **Labeling**: Adds service and application labels
- **Filtering**: Extracts log levels from Python logs

## Ports

- **Grafana**: 3000
- **Loki**: 3100
- **Promtail**: 9080 (internal)

## Data Persistence

All data is persisted in Docker volumes:
- `loki_data`: Loki logs and indices
- `grafana_data`: Grafana dashboards and settings
- `mysql_data`: Bot database (existing)

## Troubleshooting

### Check Service Health
```bash
docker-compose ps
```

### View Service Logs
```bash
# Loki logs
docker-compose logs loki

# Promtail logs
docker-compose logs promtail  

# Grafana logs
docker-compose logs grafana
```

### Test Loki API
```bash
curl http://localhost:3100/ready
```

### Access Promtail Metrics
```bash
curl http://localhost:9080/metrics
```

## Maintenance

### Restart Services
```bash
docker-compose restart loki promtail grafana
```

### Clean Up Logs (if needed)
```bash
docker-compose down
docker volume rm telegram-bot_loki_data
docker-compose up -d
```

### Update Configuration
After changing config files:
```bash
docker-compose restart loki promtail
```

## Security Considerations

1. **Change Default Password**: Set `GRAFANA_ADMIN_PASSWORD` in your `.env`
2. **Network Access**: Consider restricting port access in production
3. **Log Retention**: Configure appropriate retention policies for your needs
4. **Backup**: Regular backup of volumes in production

## Advanced Usage

### Custom Dashboards
- Create custom dashboards in Grafana UI
- Export and save to `grafana/dashboards/` for persistence

### Alerting
- Configure Grafana alerts for error rates
- Set up notification channels (email, Slack, etc.)

### Log Shipping
- For production, consider shipping logs to external Loki instance
- Modify `promtail/config.yml` to point to remote Loki

## Performance Tuning

For high-volume deployments:

1. **Loki Configuration**: Increase memory limits in `loki/local-config.yaml`
2. **Log Rotation**: Adjust Docker logging options in `docker-compose.yml`
3. **Retention**: Configure log retention policies based on storage capacity

---

*This setup is optimized for development and small production deployments. For large-scale deployments, consider using Loki in clustered mode with object storage.* 