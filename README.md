# llm-knowledge-graph-demo
This demo showcases how knowledge graphs can be used with llms and existing databases



To run the application:

Create a .env file with your OpenAI API key:

```
OPENAI_API_KEY=your_key_here
```

Build and run with Docker Compose:

```
docker-compose up --build
```

Access the chat interface at http://localhost:8501
Access the Graph: http://localhost:7474/browser/