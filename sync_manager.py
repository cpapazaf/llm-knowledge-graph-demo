import sqlite3
from neo4j import GraphDatabase
import pandas as pd
from datetime import datetime

class DataSyncManager:
    def __init__(self, sqlite_db="transactions.db", neo4j_uri="neo4j://neo4j:7687", 
                 neo4j_user="neo4j", neo4j_password="password"):
        self.sqlite_db = sqlite_db
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password), encrypted=False)
    
    def get_all_transactions(self):
        conn = sqlite3.connect(self.sqlite_db)
        query = "SELECT * FROM transactions"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def sync_transaction_to_neo4j(self, tx, row):
        # Create transaction node and link it to concepts
        query = """
        MATCH (cat:Category {name: $category})
        MERGE (trans:Transaction {
            sqlite_id: $sqlite_id,
            name: $name,
            amount: $amount,
            brand: $brand,
            transaction_time: $time,
            type: $type
        })
        MERGE (brand:Brand {name: $brand})
        WITH trans, cat, brand
        MERGE (trans)-[:HAS_CATEGORY]->(cat)
        MERGE (trans)-[:FROM_BRAND]->(brand)
        MERGE (type:Type {name: $type})
        MERGE (trans)-[:OF_TYPE]->(type)
        """
        tx.run(query, 
            sqlite_id=str(row['id']),
            name=row['name'],
            amount=float(row['amount']),
            brand=row['brand'],
            category=row['category'],
            time=row['transaction_time'],
            type=row['type']
        )
    
    def sync_all_data(self):
        df = self.get_all_transactions()
        
        with self.neo4j_driver.session() as session:
            # First, clear existing transaction nodes
            session.run("MATCH (t:Transaction) DETACH DELETE t")
            
            # Then create new transaction nodes
            for _, row in df.iterrows():
                session.write_transaction(self.sync_transaction_to_neo4j, row)
    
    def add_transaction(self, transaction_data):
        # Add to SQLite
        conn = sqlite3.connect(self.sqlite_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transactions (name, amount, brand, category, transaction_time, type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            transaction_data['name'],
            transaction_data['amount'],
            transaction_data['brand'],
            transaction_data['category'],
            transaction_data['transaction_time'],
            transaction_data['type']
        ))
        
        # Get the ID of the inserted row
        sqlite_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Sync this transaction to Neo4j
        with self.neo4j_driver.session() as session:
            session.write_transaction(
                self.sync_transaction_to_neo4j,
                {**transaction_data, 'id': sqlite_id}
            )
        
        return sqlite_id
    
    def close(self):
        self.neo4j_driver.close()