#!/usr/bin/env python3
"""
Load Generator para PostgreSQL Multi-tenant
============================================
Simula actividad en las tablas de clientes para visualizar métricas en Grafana.

Uso:
    python load_generator.py --mode light      # Carga ligera (default)
    python load_generator.py --mode medium     # Carga media
    python load_generator.py --mode heavy      # Carga pesada
    python load_generator.py --mode spike      # Picos de carga
    python load_generator.py --mode chaos      # Carga caótica (mezcla todo)
"""

import os
import sys
import time
import random
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import psycopg2
from psycopg2 import pool

# Configuración desde variables de entorno
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'user': os.getenv('POSTGRES_USER', 'monitor_admin'),
    'password': os.getenv('POSTGRES_PASSWORD', 'monitor_pass_2024'),
    'database': os.getenv('POSTGRES_DB', 'production_db')
}

# Clientes simulados
CLIENTS = [
    'acme_corp', 'tech_solutions', 'global_services', 'innovatech',
    'dataflow_inc', 'cloud_systems', 'netwise', 'securepay',
    'fasttrack_logistics', 'greentech_energy'
]

CATEGORIES = ['sales', 'refund', 'subscription', 'service', 'product', 'consulting']
STATUSES = ['pending', 'completed', 'failed', 'processing', 'cancelled']


class LoadGenerator:
    def __init__(self, mode='light'):
        self.mode = mode
        self.running = True
        self.stats = {'inserts': 0, 'updates': 0, 'selects': 0, 'deletes': 0}
        
        # Pool de conexiones
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=5,
            maxconn=20,
            **DB_CONFIG
        )
        
        # Configuración por modo
        self.configs = {
            'light': {'workers': 2, 'delay': 1.0, 'batch_size': 10},
            'medium': {'workers': 5, 'delay': 0.5, 'batch_size': 50},
            'heavy': {'workers': 10, 'delay': 0.1, 'batch_size': 100},
            'spike': {'workers': 15, 'delay': 0.05, 'batch_size': 200},
            'chaos': {'workers': 8, 'delay': 'random', 'batch_size': 'random'}
        }
    
    def get_connection(self):
        return self.pool.getconn()
    
    def release_connection(self, conn):
        self.pool.putconn(conn)
    
    def insert_records(self, client):
        """Insertar registros nuevos"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                config = self.configs[self.mode]
                batch = config['batch_size'] if config['batch_size'] != 'random' else random.randint(10, 200)
                
                cur.execute(f"""
                    INSERT INTO clients.{client} (amount, status, category, description, metadata)
                    SELECT 
                        (random() * 10000)::numeric(12,2),
                        (ARRAY['pending', 'completed', 'failed', 'processing'])[1 + floor(random() * 4)::int],
                        (ARRAY['sales', 'refund', 'subscription', 'service'])[1 + floor(random() * 4)::int],
                        'Generated at ' || NOW(),
                        jsonb_build_object('source', 'load_generator', 'batch_id', {random.randint(1000, 9999)})
                    FROM generate_series(1, {batch})
                """)
                conn.commit()
                self.stats['inserts'] += batch
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Insert failed for {client}: {e}")
        finally:
            self.release_connection(conn)
    
    def update_records(self, client):
        """Actualizar registros existentes"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                new_status = random.choice(STATUSES)
                cur.execute(f"""
                    UPDATE clients.{client}
                    SET status = %s, updated_at = NOW()
                    WHERE id IN (
                        SELECT id FROM clients.{client}
                        WHERE status = 'pending'
                        ORDER BY random()
                        LIMIT 50
                    )
                """, (new_status,))
                updated = cur.rowcount
                conn.commit()
                self.stats['updates'] += updated
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Update failed for {client}: {e}")
        finally:
            self.release_connection(conn)
    
    def select_records(self, client):
        """Queries de lectura (simula reportes)"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Query con agregaciones (genera carga de CPU)
                cur.execute(f"""
                    SELECT 
                        category,
                        status,
                        COUNT(*) as count,
                        AVG(amount) as avg_amount,
                        SUM(amount) as total_amount
                    FROM clients.{client}
                    GROUP BY category, status
                    ORDER BY total_amount DESC
                """)
                cur.fetchall()
                self.stats['selects'] += 1
                
                # Query con JOIN (más pesado)
                if random.random() > 0.7:
                    cur.execute(f"""
                        SELECT t1.*, t2.category as related_category
                        FROM clients.{client} t1
                        CROSS JOIN LATERAL (
                            SELECT category FROM clients.{client} 
                            WHERE id != t1.id 
                            ORDER BY random() 
                            LIMIT 1
                        ) t2
                        LIMIT 100
                    """)
                    cur.fetchall()
                    self.stats['selects'] += 1
        except Exception as e:
            print(f"[ERROR] Select failed for {client}: {e}")
        finally:
            self.release_connection(conn)
    
    def delete_records(self, client):
        """Eliminar registros antiguos"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    DELETE FROM clients.{client}
                    WHERE id IN (
                        SELECT id FROM clients.{client}
                        WHERE status IN ('cancelled', 'failed')
                        AND created_at < NOW() - interval '30 days'
                        ORDER BY random()
                        LIMIT 20
                    )
                """)
                deleted = cur.rowcount
                conn.commit()
                self.stats['deletes'] += deleted
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Delete failed for {client}: {e}")
        finally:
            self.release_connection(conn)
    
    def worker(self, worker_id):
        """Worker que ejecuta operaciones aleatorias"""
        config = self.configs[self.mode]
        
        while self.running:
            client = random.choice(CLIENTS)
            operation = random.choices(
                ['insert', 'update', 'select', 'delete'],
                weights=[40, 25, 30, 5]  # Más inserts y selects
            )[0]
            
            if operation == 'insert':
                self.insert_records(client)
            elif operation == 'update':
                self.update_records(client)
            elif operation == 'select':
                self.select_records(client)
            elif operation == 'delete':
                self.delete_records(client)
            
            # Delay entre operaciones
            delay = config['delay']
            if delay == 'random':
                delay = random.uniform(0.1, 2.0)
            time.sleep(delay)
    
    def print_stats(self):
        """Imprimir estadísticas periódicamente"""
        while self.running:
            time.sleep(10)
            total = sum(self.stats.values())
            print(f"\n[STATS] Mode: {self.mode} | Total ops: {total}")
            print(f"        Inserts: {self.stats['inserts']} | Updates: {self.stats['updates']}")
            print(f"        Selects: {self.stats['selects']} | Deletes: {self.stats['deletes']}")
    
    def run(self):
        """Iniciar generador de carga"""
        config = self.configs[self.mode]
        workers = config['workers']
        
        print(f"=" * 60)
        print(f"  Load Generator - Mode: {self.mode.upper()}")
        print(f"  Workers: {workers} | Delay: {config['delay']}s | Batch: {config['batch_size']}")
        print(f"  Target DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        print(f"  Press Ctrl+C to stop")
        print(f"=" * 60)
        
        # Thread para estadísticas
        stats_thread = threading.Thread(target=self.print_stats, daemon=True)
        stats_thread.start()
        
        # Pool de workers
        with ThreadPoolExecutor(max_workers=workers) as executor:
            try:
                futures = [executor.submit(self.worker, i) for i in range(workers)]
                # Mantener vivo hasta Ctrl+C
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n[INFO] Stopping load generator...")
                self.running = False
        
        # Estadísticas finales
        print(f"\n{'=' * 60}")
        print(f"  FINAL STATS")
        print(f"  Total operations: {sum(self.stats.values())}")
        print(f"  Inserts: {self.stats['inserts']}")
        print(f"  Updates: {self.stats['updates']}")
        print(f"  Selects: {self.stats['selects']}")
        print(f"  Deletes: {self.stats['deletes']}")
        print(f"{'=' * 60}")
        
        self.pool.closeall()


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL Load Generator')
    parser.add_argument(
        '--mode', '-m',
        choices=['light', 'medium', 'heavy', 'spike', 'chaos'],
        default='light',
        help='Load intensity mode'
    )
    args = parser.parse_args()
    
    generator = LoadGenerator(mode=args.mode)
    generator.run()


if __name__ == '__main__':
    main()
