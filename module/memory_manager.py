from datetime import datetime
from typing import Any, Dict, List

class MemoryManager:
    def __init__(self, llm=None):
        """
        A simplified memory manager that uses in-memory storage.
        
        Args:
            llm: Optional language model for summarization
        """
        self.llm = llm
        # In-memory storage for chat messages
        self.memory = {}

    def save_chat_message(self, user_id: str, role: str, content: str, metadata: dict = None) -> None:
        """
        Save a chat message to memory.
        
        Args:
            user_id: User identifier
            role: Role of the message sender (user/assistant)
            content: Message content
            metadata: Optional metadata for the message
        """
        # Create message object
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        
        if metadata:
            message.update(metadata)
        
        # Save to in-memory dictionary
        if user_id not in self.memory:
            self.memory[user_id] = []
            
        self.memory[user_id].append(message)

    def get_chat_history(self, user_id: str, limit: int = 500) -> List[Dict[str, str]]:
        """
        Retrieve chat history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of chat messages
        """
        if user_id not in self.memory:
            return []
            
        # Return the most recent messages up to the limit
        return self.memory[user_id][-limit:]

    def summarize_chat_history(self, user_id: str) -> str:
        """
        Summarize chat history using the LLM.
        """
        history = self.get_chat_history(user_id, limit=500)
        if not history:
            return "无历史记录。"

        # If no LLM is provided, return a simple summary
        if self.llm is None:
            return f"历史对话包含 {len(history)} 条消息。"

        history_text = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in history]
        )
        prompt = f"""
        以下是用户与助手的历史对话记录，请总结其中的主要信息：

        {history_text}

        请用简短的语言概括历史对话内容。
        """
        try:
            summary = self.llm.predict(prompt)
            return summary.strip()
        except Exception as e:
            print(f"Error summarizing chat history: {e}")
            return "无法生成总结。"
