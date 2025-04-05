from typing import Dict, List

class TechnicalSupport:
    """
    Simplified mock implementation of technical support handler
    """
    
    def __init__(self):
        """Initialize a simplified technical support handler with mock data"""
        # Mock documents for demonstration
        self.mock_docs = [
            {"page_content": "这是一个示例文档1。包含有关包装技术的信息。", "metadata": {"source": "技术手册", "section": "包装技术"}},
            {"page_content": "这是一个示例文档2。包含有关设备维护的信息。", "metadata": {"source": "维护手册", "section": "设备维护"}},
            {"page_content": "这是一个示例文档3。包含有关故障排除的信息。", "metadata": {"source": "故障排除指南", "section": "常见问题"}},
        ]
        
        # Mock retriever that will return stored documents
        self.retriever = self._create_mock_retriever()
        
    def _create_mock_retriever(self):
        """Create a mock retriever that returns stored documents"""
        class MockRetriever:
            def __init__(self, docs):
                self.docs = docs
                
            def invoke(self, query):
                # Just return all docs for simplicity
                return self.docs
                
        return MockRetriever(self.mock_docs)
        
    def query(self, question: str, chat_history=None) -> str:
        """
        Process a query and return a response based on retrieved documents.
        
        Args:
            question: The user's question
            chat_history: Optional chat history
            
        Returns:
            A string response
        """
        # In a real implementation, this would use the retriever and LLM to generate an answer
        # For simplicity, we'll just return a fixed response with the question
        return f"针对您的问题「{question}」，我们建议参考技术手册中的相关章节。您可以在设备维护手册第3章找到详细说明。" 