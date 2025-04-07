import asyncio
import sys
import json
import time
import re
import traceback
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.sse import sse_client

def extract_text_from_response(response):
    """Extract plain text from a structured response.
    
    The response might be:
    1. A simple string
    2. A structured object with content and metadata
    3. A TextContent object
    """
    if isinstance(response, str):
        return response
    
    # Handle dict-like responses with content field
    if hasattr(response, 'content') and response.content:
        content = response.content
        if isinstance(content, list):
            # Extract text from all text content items
            texts = []
            for item in content:
                if hasattr(item, 'type') and item.type == 'text':
                    texts.append(item.text)
            return ' '.join(texts)
        return str(content)
    
    # Handle other structured responses
    if hasattr(response, 'text'):
        return response.text
    
    # Fallback
    return str(response)

def extract_task_id(text):
    """Extract task ID from a response text."""
    if "status:" in text:
        # Find everything after "status:" until the end or a quote/whitespace
        match = re.search(r"status:([^\s'\"]+)", text)
        if match:
            return match.group(1)
    return None

async def check_request_status(session, task_id):
    """Poll for the result of a background task."""
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        if retry_count > 0:
            print(f"Still processing... (attempt {retry_count}/{max_retries})", end="\r")
        
        try:
            status_response = await session.call_tool(
                "check_request_status",
                arguments={"task_id": task_id}
            )
            
            # Extract text from the response
            status_text = extract_text_from_response(status_response)
            
            if "still being processed" not in status_text:
                # Clear the status line
                if retry_count > 0:
                    print(" " * 60, end="\r")
                # Got the final result
                return status_text
        except Exception as e:
            print(f"\nError checking status: {str(e)}")
        
        retry_count += 1
        await asyncio.sleep(2)
    
    return "Request timed out after multiple retries."

async def chat_session(session):
    """Run an interactive chat session with the MCP server."""
    print("\nChat session started. Type 'quit' to exit.")
    user_id = f"user_{int(time.time())}"
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            break
        
        try:
            # Show a waiting indicator
            print("Processing...", end="\r")
            
            # Call the process_conversation_turn tool
            response = await session.call_tool(
                "process_conversation_turn",
                arguments={"user_id": user_id, "prompt": user_input}
            )
            
            # Extract text from the response
            response_text = extract_text_from_response(response)
            
            # Clear the processing indicator
            print(" " * 20, end="\r")
            
            # Check if we need to poll for status
            task_id = extract_task_id(response_text)
            
            if task_id:
                # Automatically poll for the result
                print("Processing your request...", end="\r")
                final_response = await check_request_status(session, task_id)
                print(" " * 30, end="\r")  # Clear the status line
                print(f"AI: {final_response}")
            else:
                print(f"AI: {response_text}")
                
        except Exception as e:
            print(f"Error: {str(e)}")
            traceback.print_exception(type(e), e, e.__traceback__)

async def main(server_url):
    """Connect to the MCP server and start a chat session."""
    if urlparse(server_url).scheme not in ("http", "https"):
        print("Error: Server URL must start with http:// or https://")
        sys.exit(1)

    try:
        print(f"Connecting to MCP server at {server_url}...")
        async with sse_client(server_url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                print("Connected successfully!")
                
                # List available tools
                tools = await session.list_tools()
                print("\nAvailable tools:")
                for tool in tools.tools:
                    print(f" * {tool}")
                
                # Start the chat session
                await chat_session(session)
                
    except Exception as e:
        print(f"Error connecting to server: {e}")
        traceback.print_exception(type(e), e, e.__traceback__)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default server URL if not provided
        server_url = "http://127.0.0.1:8000/sse"
        print(f"Using default server URL: {server_url}")
        print("You can specify a different URL: python mcp_client.py <server_url>")
    else:
        server_url = sys.argv[1]
    
    asyncio.run(main(server_url))