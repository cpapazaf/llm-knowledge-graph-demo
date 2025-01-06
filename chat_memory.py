class ChatMemory:
    def __init__(self):
        self.messages = []
    
    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        # Keep last 10 messages for context
        if len(self.messages) > 10:
            self.messages = self.messages[-10:]
    
    def get_messages(self):
        return self.messages
    
    def clear(self):
        self.messages = []
