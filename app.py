# app.py
import streamlit as st
from openai import OpenAI
from knowledge_graph import KnowledgeGraph
from chat_memory import ChatMemory
from sync_manager import DataSyncManager
import os
from dotenv import load_dotenv
import json
from time import sleep
import pandas as pd


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Knowledge Graph
kg = KnowledgeGraph()

# Initialize DataSyncManager in session state
if 'sync_manager' not in st.session_state:
    st.session_state.sync_manager = DataSyncManager()

# Initialize session state for chat memory
if 'chat_memory' not in st.session_state:
    st.session_state.chat_memory = ChatMemory()

# Initialize databases and sync data if needed
if not st.session_state.get('initialized', False):
    from data_init import init_sqlite, init_neo4j
    init_sqlite()
    init_neo4j()
    # Perform initial sync
    st.session_state.sync_manager.sync_all_data()
    st.session_state.initialized = True

def get_graph_query_function():
    return {
        "name": "query_knowledge_graph",
        "description": "Query the financial knowledge graph using Cypher",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The Cypher query to execute"
                }
            },
            "required": ["query"]
        }
    }

def query_knowledge_graph(query):
    try:
        results = kg.query_graph(query)
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error executing query: {str(e)}"

def process_user_query(user_question):
    # Add user message to memory
    st.session_state.chat_memory.add_message("user", user_question)
    
    # System message with context about the knowledge graph
    system_message = """You are a financial assistant with access to a knowledge graph containing financial data and relationships.
    The graph contains concepts like Transaction Categories, Types (Income/Expense), and their relationships.
    When querying the graph, use Cypher to extract relevant information.
    Always explain your reasoning and the insights from the data in a clear, conversational manner."""
    
    messages = [{"role": "system", "content": system_message}]
    messages.extend(st.session_state.chat_memory.get_messages())
    
    # Call OpenAI with function calling using the new client format
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=[{
            "type": "function",
            "function": get_graph_query_function()
        }],
        tool_choice="auto"
    )
    
    assistant_message = response.choices[0].message
    
    # Check if the model wants to call the function
    if assistant_message.tool_calls:
        # Get the function call details
        tool_call = assistant_message.tool_calls[0]
        function_args = json.loads(tool_call.function.arguments)
        query_result = query_knowledge_graph(function_args["query"])
        
        # Add function result to messages and get final response
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }
            ]
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": "query_knowledge_graph",
            "content": query_result
        })
        
        final_response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        
        final_answer = final_response.choices[0].message.content
    else:
        final_answer = assistant_message.content
    
    # Add assistant's response to memory
    st.session_state.chat_memory.add_message("assistant", final_answer)
    
    return final_answer

def show_transaction_form():
    st.header("Add New Transaction")
    
    with st.form("transaction_form"):
        name = st.text_input("Transaction Name")
        amount = st.number_input("Amount", min_value=0.0)
        brand = st.text_input("Brand/Company")
        category = st.selectbox("Category", [
            "Groceries", "Food", "Transportation", "Entertainment", 
            "Utilities", "Salary", "Investment", "Other"
        ])
        transaction_type = st.selectbox("Type", ["in", "out"])
        transaction_time = st.date_input("Transaction Date")
        
        submitted = st.form_submit_button("Add Transaction")
        
        if submitted and name and amount and brand:
            transaction_data = {
                'name': name,
                'amount': amount,
                'brand': brand,
                'category': category,
                'transaction_time': transaction_time.strftime('%Y-%m-%d'),
                'type': transaction_type
            }
            
            # Add transaction and sync to Neo4j
            sqlite_id = st.session_state.sync_manager.add_transaction(transaction_data)
            st.success(f"Transaction added successfully! ID: {sqlite_id}")
            
            # Optionally refresh the page or clear the form
            st.experimental_rerun()

def show_recent_transactions():
    st.header("Recent Transactions")
    
    # Get transactions from SQLite
    df = st.session_state.sync_manager.get_all_transactions()
    df['transaction_time'] = pd.to_datetime(df['transaction_time'])
    df = df.sort_values('transaction_time', ascending=False).head(5)
    
    for _, row in df.iterrows():
        with st.expander(f"{row['name']} - {row['transaction_time'].strftime('%Y-%m-%d')}"):
            st.write(f"Amount: ${row['amount']:.2f}")
            st.write(f"Category: {row['category']}")
            st.write(f"Brand: {row['brand']}")
            st.write(f"Type: {row['type']}")

# Rest of the Streamlit UI code remains the same
st.title("Financial Knowledge Graph Chat")

# Add tabs for different functions
tab1, tab2, tab3 = st.tabs(["Chat", "Add Transaction", "Recent Transactions"])

with tab1:
    # Chat interface
    st.write("Ask questions about your financial data:")
    
    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state.chat_memory.clear()
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.chat_memory.get_messages():
        if message["role"] == "user":
            st.write("You: " + message["content"])
        elif message["role"] == "assistant":
            st.write("Assistant: " + message["content"])
    
    # User input
    user_question = st.text_input("Your question:")
    if user_question:
        response = process_user_query(user_question)
        
        # Auto-scroll to the bottom
        js = f"""
        <script>
            function scroll() {{
                var elem = document.getElementById('chat-bottom');
                elem.scrollIntoView();
            }}
            scroll();
        </script>
        """
        st.components.v1.html(js)
    
with tab2:
    show_transaction_form()

with tab3:
    show_recent_transactions()

# Add a hidden div for auto-scroll
st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)

# Cleanup on session end
def cleanup():
    if 'sync_manager' in st.session_state:
        st.session_state.sync_manager.close()

# Register cleanup
import atexit
atexit.register(cleanup)