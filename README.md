# Monitoring Stack - Prometheus + Grafana

Stack de monitoreo para hardware y PostgreSQL multi-tenant usando Docker.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              MONITORING STACK                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐     ┌─────────────────────┐                       │
│  │    PostgreSQL    │────▶│  postgres_exporter  │──┐                    │
│  │  (Multi-tenant)  │     │       :9187         │  │                    │
│  │      :5432       │     └─────────────────────┘  │    ┌────────────┐  │
│  └──────────────────┘                              ├───▶│ Prometheus │  │
│                                                    │    │   :9090    │  │
│  ┌──────────────────┐     ┌─────────────────────┐  │    └─────┬──────┘  │
│  │     Host OS      │────▶│   node_exporter     │──┘          │         │
│  │ (CPU/RAM/Disk)   │     │       :9100         │             ▼         │
│  └──────────────────┘     └─────────────────────┘      ┌────────────┐   │
│                                                        │  Grafana   │   │
│  ┌──────────────────┐                                  │   :3000    │   │
│  │  Load Generator  │ ─ ─ ─▶ (simula carga)           └────────────┘   │
│  └──────────────────┘                                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM mínimo

## Quick Start

```bash
# 1. Clonar repositorio
git clone <tu-repo>
cd monitoring-stack

# 2. Levantar stack
docker-compose up -d

# 3. Verificar servicios
docker-compose ps

# 4. Acceder a interfaces
# Grafana:    http://localhost:3000 (admin / grafana_admin_2024)
# Prometheus: http://localhost:9090
```

## Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| Grafana | 3000 | Dashboards y visualización |
| Prometheus | 9090 | Recolección y almacenamiento de métricas |
| PostgreSQL | 5432 | Base de datos multi-tenant |
| postgres_exporter | 9187 | Métricas de PostgreSQL |
| node_exporter | 9100 | Métricas de hardware |

## Credenciales

| Servicio | Usuario | Password |
|----------|---------|----------|
| Grafana | admin | grafana_admin_2024 |
| PostgreSQL | monitor_admin | monitor_pass_2024 |
| PostgreSQL (readonly) | monitor_reader | reader_pass_2024 |

## Dashboards incluidos

### 1. Hardware Monitor
- CPU usage y modos (user, system, idle, iowait)
- Memoria RAM (used, buffers, cached, free)
- Disco (uso por mount, I/O read/write)
- Red (traffic, errores, drops)

### 2. PostgreSQL Multi-tenant
- Conexiones activas y cache hit ratio
- Transacciones por segundo
- **Métricas por cliente:**
  - Inserts/Updates/Deletes por tabla
  - Tamaño de tabla
  - Cantidad de filas
  - Sequential vs Index scans
  - Dead rows (necesitan VACUUM)
- Locks activos

## Generador de carga

Para simular actividad y ver las métricas en acción:

```bash
# Carga ligera (2 workers, 1 op/seg)
docker-compose run --rm load_generator python load_generator.py --mode light

# Carga media (5 workers, 2 ops/seg)
docker-compose run --rm load_generator python load_generator.py --mode medium

# Carga pesada (10 workers, 10 ops/seg)
docker-compose run --rm load_generator python load_generator.py --mode heavy

# Picos de carga (15 workers, 20 ops/seg)
docker-compose run --rm load_generator python load_generator.py --mode spike

# Carga caótica (aleatorio)
docker-compose run --rm load_generator python load_generator.py --mode chaos
```

Mientras el generador corre, observa los dashboards en Grafana para ver:
- Incremento en transacciones/segundo
- Cambios en tamaño de tablas por cliente
- Variación en conexiones activas
- Aumento de dead rows

## Clientes simulados

La base de datos incluye 10 clientes de prueba:

| Cliente | Datos iniciales |
|---------|-----------------|
| acme_corp | 5,000 filas |
| tech_solutions | 3,500 filas |
| global_services | 8,000 filas |
| innovatech | 2,000 filas |
| dataflow_inc | 6,000 filas |
| cloud_systems | 4,500 filas |
| netwise | 1,500 filas |
| securepay | 7,000 filas |
| fasttrack_logistics | 3,000 filas |
| greentech_energy | 2,500 filas |

## Estructura del proyecto

```
monitoring-stack/
├── docker-compose.yml          # Orquestador de servicios
├── prometheus/
│   ├── prometheus.yml          # Configuración de scraping
│   └── queries.yml             # Custom queries multi-tenant
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/        # Datasource Prometheus auto-config
│   │   └── dashboards/         # Config de provisioning
│   └── dashboards/             # Dashboards JSON
├── postgres/
│   └── init/
│       └── 01-init.sql         # Inicialización multi-tenant
├── scripts/
│   ├── load_generator.py       # Generador de carga
│   └── Dockerfile              # Imagen del generador
└── README.md
```

## Comandos útiles

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f postgres

# Reiniciar un servicio
docker-compose restart grafana

# Detener todo
docker-compose down

# Detener y eliminar datos (reset completo)
docker-compose down -v

# Conectar a PostgreSQL
docker exec -it monitoring_postgres psql -U monitor_admin -d production_db

# Ver estadísticas por cliente
docker exec -it monitoring_postgres psql -U monitor_admin -d production_db -c "SELECT * FROM client_stats;"

# Recargar configuración de Prometheus
curl -X POST http://localhost:9090/-/reload
```

## Queries PromQL útiles

### Hardware
```promql
# CPU usado
100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# RAM usada (%)
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disco usado
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100
```

### PostgreSQL
```promql
# Inserts por segundo por cliente
rate(pg_client_tables_inserts_total[5m])

# Top 5 tablas más grandes
topk(5, pg_client_table_size_total_bytes)

# Tablas con más dead rows
topk(5, pg_client_tables_dead_rows)

# Cache hit ratio (debe ser > 0.99)
pg_database_stats_cache_hit_ratio
```

## Despliegue en servidor

1. Clonar repo en el servidor:
   ```bash
   git clone <tu-repo>
   cd monitoring-stack
   ```

2. Ajustar credenciales en `docker-compose.yml` para producción

3. Ajustar `prometheus/queries.yml` si el schema es diferente

4. Levantar:
   ```bash
   docker-compose up -d
   ```

## Notas para Windows Server

- node_exporter no funciona en Windows nativo
- Usar [windows_exporter](https://github.com/prometheus-community/windows_exporter) en su lugar
- El resto del stack funciona igual con Docker Desktop o Docker en WSL2

---

**Desarrollado para monitoreo de infraestructura y bases de datos multi-tenant.**
