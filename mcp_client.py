import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
from dotenv import load_dotenv
import json
from typing import Dict, Any

load_dotenv()

client = OpenAI()


def send_message(message: str) -> None:
    """Send a message to the MCP server."""
    request = {
        "id": "1",
        "method": "process_conversation_turn",
        "params": {
            "user_id": "test_user_123",
            "prompt": message
        }
    }
    
    # Send the request to stdout (which the server reads from)
    print(json.dumps(request), flush=True)

def receive_response() -> Dict[str, Any]:
    """Receive a response from the MCP server."""
    response_text = input()
    return json.loads(response_text)

def main():
    print("MCP Client started. Type 'quit' to exit.")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            break
            
        # Send message to server
        send_message(user_input)
        
        # Receive response
        try:
            response = receive_response()
            if "result" in response:
                print(f"AI: {response['result']}")
            elif "error" in response:
                print(f"Error: {response['error']}")
            else:
                print(f"Unknown response: {response}")
        except Exception as e:
            print(f"Error receiving response: {e}")
    
    print("MCP Client terminated.")

if __name__ == "__main__":
    main()