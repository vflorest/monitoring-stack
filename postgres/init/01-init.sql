-- =============================================================================
-- INICIALIZACIÓN DE BASE DE DATOS MULTI-TENANT
-- =============================================================================
-- Simula un escenario real donde cada cliente tiene su propia tabla.
-- Esto permite monitorear métricas por cliente en Grafana.
-- =============================================================================

-- Crear schema para organización
CREATE SCHEMA IF NOT EXISTS clients;

-- =============================================================================
-- FUNCIÓN PARA CREAR TABLAS DE CLIENTES
-- =============================================================================
CREATE OR REPLACE FUNCTION create_client_table(client_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS clients.%I (
            id SERIAL PRIMARY KEY,
            transaction_id UUID DEFAULT gen_random_uuid(),
            amount NUMERIC(12,2) NOT NULL,
            status VARCHAR(20) DEFAULT ''pending'',
            category VARCHAR(50),
            description TEXT,
            metadata JSONB DEFAULT ''{}'',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )', client_name);
    
    -- Crear índices para mejor performance
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_status ON clients.%I(status)', client_name, client_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_created ON clients.%I(created_at)', client_name, client_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_category ON clients.%I(category)', client_name, client_name);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- CREAR TABLAS PARA 10 CLIENTES SIMULADOS
-- =============================================================================
SELECT create_client_table('acme_corp');
SELECT create_client_table('tech_solutions');
SELECT create_client_table('global_services');
SELECT create_client_table('innovatech');
SELECT create_client_table('dataflow_inc');
SELECT create_client_table('cloud_systems');
SELECT create_client_table('netwise');
SELECT create_client_table('securepay');
SELECT create_client_table('fasttrack_logistics');
SELECT create_client_table('greentech_energy');

-- =============================================================================
-- FUNCIÓN PARA INSERTAR DATOS DE PRUEBA
-- =============================================================================
CREATE OR REPLACE FUNCTION populate_client_data(client_name TEXT, num_records INT)
RETURNS VOID AS $$
DECLARE
    categories TEXT[] := ARRAY['sales', 'refund', 'subscription', 'service', 'product', 'consulting'];
    statuses TEXT[] := ARRAY['pending', 'completed', 'failed', 'processing', 'cancelled'];
BEGIN
    EXECUTE format('
        INSERT INTO clients.%I (amount, status, category, description, metadata, created_at)
        SELECT 
            (random() * 10000)::numeric(12,2),
            ($1)[1 + floor(random() * array_length($1, 1))::int],
            ($2)[1 + floor(random() * array_length($2, 1))::int],
            ''Transaction '' || generate_series || '' for %I'',
            jsonb_build_object(
                ''source'', CASE WHEN random() > 0.5 THEN ''web'' ELSE ''api'' END,
                ''region'', (ARRAY[''us-east'', ''us-west'', ''eu-central'', ''ap-south''])[1 + floor(random() * 4)::int]
            ),
            NOW() - (random() * interval ''90 days'')
        FROM generate_series(1, $3)
    ', client_name, client_name)
    USING statuses, categories, num_records;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- POBLAR DATOS INICIALES (diferentes volúmenes por cliente)
-- =============================================================================
-- Simula que algunos clientes tienen más actividad que otros
SELECT populate_client_data('acme_corp', 5000);
SELECT populate_client_data('tech_solutions', 3500);
SELECT populate_client_data('global_services', 8000);
SELECT populate_client_data('innovatech', 2000);
SELECT populate_client_data('dataflow_inc', 6000);
SELECT populate_client_data('cloud_systems', 4500);
SELECT populate_client_data('netwise', 1500);
SELECT populate_client_data('securepay', 7000);
SELECT populate_client_data('fasttrack_logistics', 3000);
SELECT populate_client_data('greentech_energy', 2500);

-- =============================================================================
-- CREAR USUARIO DE SOLO LECTURA PARA MONITOREO
-- =============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'monitor_reader') THEN
        CREATE ROLE monitor_reader WITH LOGIN PASSWORD 'reader_pass_2024';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE production_db TO monitor_reader;
GRANT USAGE ON SCHEMA clients TO monitor_reader;
GRANT USAGE ON SCHEMA public TO monitor_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA clients TO monitor_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitor_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA clients GRANT SELECT ON TABLES TO monitor_reader;

-- =============================================================================
-- VISTAS ÚTILES PARA MONITOREO
-- =============================================================================

-- Vista consolidada de estadísticas por cliente
CREATE OR REPLACE VIEW public.client_stats AS
SELECT 
    relname as client_table,
    n_live_tup as row_count,
    n_dead_tup as dead_rows,
    seq_scan as sequential_scans,
    idx_scan as index_scans,
    n_tup_ins as total_inserts,
    n_tup_upd as total_updates,
    n_tup_del as total_deletes
FROM pg_stat_user_tables
WHERE schemaname = 'clients'
ORDER BY n_live_tup DESC;

-- Vista de tamaño por cliente
CREATE OR REPLACE VIEW public.client_sizes AS
SELECT 
    relname as client_table,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size,
    pg_total_relation_size(relid) as size_bytes
FROM pg_stat_user_tables
WHERE schemaname = 'clients'
ORDER BY pg_total_relation_size(relid) DESC;

GRANT SELECT ON public.client_stats TO monitor_reader;
GRANT SELECT ON public.client_sizes TO monitor_reader;

-- =============================================================================
-- MENSAJE DE CONFIRMACIÓN
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✓ Base de datos multi-tenant inicializada correctamente';
    RAISE NOTICE '✓ 10 clientes creados con datos de prueba';
    RAISE NOTICE '✓ Usuario monitor_reader creado para monitoreo';
END
$$;
