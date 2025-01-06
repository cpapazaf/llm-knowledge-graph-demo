from neo4j import GraphDatabase
import json

class KnowledgeGraph:
    def __init__(self, uri="neo4j://neo4j:7687", user="neo4j", password="password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
    
    def query_graph(self, cypher_query):
        with self.driver.session() as session:
            result = session.run(cypher_query)
            return [record.data() for record in result]
    
    def close(self):
        self.driver.close()
