import json
from typing import Any
from openai import OpenAI
# from langchain_core.messages import HumanMessage
# from langchain_openai import ChatOpenAI
from mcp.server.fastmcp import FastMCP

# Import your existing modules (adjust the import path as needed)
from module.memory_manager import MemoryManager
from module.handlers import TechnicalSupport
from dotenv import load_dotenv
import os

load_dotenv()

#setup openai
openai = OpenAI()

# Set OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")


# Initialize FastMCP server
mcp = FastMCP("conversation_server")

# Create global instances of the handlers
memory_manager = MemoryManager()
tech_support = TechnicalSupport()

@mcp.tool()
async def process_conversation_turn(user_id: str, prompt: str) -> str:
    """
    Process a conversation turn for a user.

    Args:
        user_id: Unique identifier for the user
        prompt: The user's input message

    Returns:
        A string containing the assistant's response
    """
    # Retrieve conversation history using the global memory_manager
    previous_messages = memory_manager.get_chat_history(user_id)
    chat_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in previous_messages
    ]

    # Classify the prompt: casual chat or technical query
    classify_prompt = f"""
        请判断以下用户输入是否为闲聊内容。
        如果是闲聊内容（如问候、日常对话等），返回"True"。
        如果是业务相关内容（如包装、设备、技术支持等），返回"False"。

        用户输入: {prompt}

        仅返回"True"或"False"，不要包含其他内容。
    """
    # Use direct OpenAI API call instead of LangChain
    classify_response = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[{"role": "user", "content": classify_prompt}]
    )
    is_casual_chat = classify_response.choices[0].message.content.strip() == "True"

    if is_casual_chat:
        # Handle casual chat with a friendly LLM response
        chat_prompt = f"""
        【系统角色】
        你是一名专业的企业知识助理助手。负责根据提供的内部参考资料，以清晰准确的方式回答
        员工问题。你的身份是 "广州标际包装设备有限公司" 的 AI 助手，回答全部体现专业性和
        权威性。

        【回答规则】
        1. 语言要求:
           - 使用专业规范的化表达 (根据用户身份动态调整)
           - 保持对话自然、亲切、专业
           - 复杂问题采用层级分解

        user:
        请以友好的方式回答用户的问题，保持对话自然、亲切、专业。
        用户输入：{prompt}
        """
        # Use direct OpenAI API call instead of LangChain
        response_message = openai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[{"role": "user", "content": chat_prompt}]
        )
        response = response_message.choices[0].message.content
    else:
        # Handle technical query with RAG using the global tech_support instance
        retriever = tech_support.retriever
        retrieved_docs = retriever.invoke({"input": prompt, "chat_history": chat_history})
        reference_text = ""
        for i, doc in enumerate(retrieved_docs, 1):
            reference_text += f"文档 {i}:\n内容: {doc.page_content}\n元数据: {doc.metadata}\n\n"

        technical_response = tech_support.query(prompt, chat_history)

        # Format the technical response
        formatting_prompt = f"""
        请将以下技术回答转换为更友好、专业的格式，遵循以下规则：
            1. 严格分级响应:
            - 当内容明确匹配知识库内容时:
                ① 直接引用原文条款 (标注来源章节)
                ② 用专业语言解释条款
                ③ 举例说明（如适用）
            - 当需要跨章节综合时:
                ① 先说明"根据多个相关条款"
                ② 分点列出不同条款要求
                ③ 指出条款间的关联关系
            - 当问题涉及边缘案例时:
                ① 说明"可能知识库未覆盖此问题"
                ② 提供最相关的3个已有条款
                ③ 建议咨询部门负责人 (给出联系方式)

            2. 语言要求:
            - 使用专业规范的化表达 (根据用户身份动态调整)
            - 关键数据必须精确引用且回应(精度要求)
            - 复杂问题采用层级分解 (使用"第一步、第二步"句式)

            3. 安全限制:
            - 涉及【新版】【权限】等敏感话题时:
                ① 先验证用户身份 (要求工号后四位)
                ② 通过验证后仅提供该员工权限范围内的信息
            - 遇到【敏感性检索】时:
                ① 说明"根据保密条款"
                ② 指出可能的变通路径
                ③ 建议联系系统部门

          【知识库说明】
            可用可参考的权威资料:
            <知识库>
            {reference_text}
            </知识库>

            【输出格式】
            "回答": "核心回答内容",
            "0-1置信度评分": "0-1置信度评分",
            "相关问题": ["相关延伸问题1", "问题2"]

        技术回答：
        {technical_response}

        请以如下格式输出：
        {{
            "回答": "转换后的回答内容",
            "0-1置信度评分": "基于回答准确度的评分",
            "相关问题": ["相关延伸问题1", "相关延伸问题2", "相关延伸问题3"]
        }}
        """
        formatted_response_message = openai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[{"role": "user", "content": formatting_prompt}]
        )
        formatted_response = formatted_response_message.choices[0].message.content

        try:
            response_dict = json.loads(formatted_response)
            response = (
                f"回答：{response_dict['回答']}\n\n"
                f"置信度：{response_dict['0-1置信度评分']}\n\n"
                f"相关问题：\n"
                f"- {response_dict['相关问题'][0]}\n"
                f"- {response_dict['相关问题'][1]}\n"
                f"- {response_dict['相关问题'][2]}"
            )
        except json.JSONDecodeError:
            response = formatted_response  # Fallback to raw response if JSON parsing fails

    # Save the conversation turn to memory using the global memory_manager
    memory_manager.save_chat_message(user_id, "user", prompt)
    memory_manager.save_chat_message(user_id, "assistant", response)

    return response

if __name__ == "__main__":
    mcp.run(transport='stdio')