import sqlite3
import datetime
from neo4j import GraphDatabase
import pandas as pd

def init_sqlite():
    conn = sqlite3.connect('transactions.db')
    c = conn.cursor()
    
    # Create transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         name TEXT,
         amount REAL,
         brand TEXT,
         category TEXT,
         transaction_time DATETIME,
         type TEXT)
    ''')
    
    # Sample data
    three_months_ago = datetime.datetime.now() - datetime.timedelta(days=90)
    sample_data = [
        ("Grocery Shopping", 150.50, "Walmart", "Groceries", three_months_ago, "out"),
        ("Salary", 5000.00, "Tech Corp", "Income", three_months_ago + datetime.timedelta(days=15), "in"),
        ("Restaurant", 45.75, "McDonalds", "Food", three_months_ago + datetime.timedelta(days=30), "out"),
        # Add more sample transactions...
    ]
    
    c.executemany('''
        INSERT INTO transactions (name, amount, brand, category, transaction_time, type)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_data)
    
    conn.commit()
    conn.close()

def init_neo4j():
    uri = "neo4j://neo4j:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "password"), encrypted=False)
    
    def create_ontology(tx):
        # Create ontology nodes and relationships
        tx.run("""
            CREATE (fin:Domain {name: 'Finance'})
            
            CREATE (trans:Category {name: 'Transaction'})
            CREATE (income:Type {name: 'Income'})
            CREATE (expense:Type {name: 'Expense'})
            
            CREATE (food:Category {name: 'Food'})
            CREATE (groceries:Subcategory {name: 'Groceries'})
            CREATE (restaurant:Subcategory {name: 'Restaurant'})
            
            CREATE (fin)-[:HAS_CATEGORY]->(trans)
            CREATE (trans)-[:HAS_TYPE]->(income)
            CREATE (trans)-[:HAS_TYPE]->(expense)
            CREATE (trans)-[:HAS_CATEGORY]->(food)
            CREATE (food)-[:HAS_SUBCATEGORY]->(groceries)
            CREATE (food)-[:HAS_SUBCATEGORY]->(restaurant)
        """)
    
    with driver.session() as session:
        session.write_transaction(create_ontology)
    
    driver.close()