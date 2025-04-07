import json
from typing import Any
import aiohttp
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request

# Import your existing modules (adjust the import path as needed)

from dotenv import load_dotenv
import os

load_dotenv()

# Initialize FastMCP server with SSE transport
mcp = FastMCP("conversation_server")

# Dictionary to store pending tasks and their results
pending_requests = {}

@mcp.tool()
async def process_conversation_turn(user_id: str, prompt: str) -> str:
    """
    Process a conversation turn for a user by calling an external API.

    Args:
        user_id: Unique identifier for the user
        prompt: The user's input message

    Returns:
        A string containing the assistant's response
    """
    
    # Start a background task to handle the API request
    task_id = f"{user_id}_{asyncio.get_event_loop().time()}"
    
    # Create the background task
    background_task = asyncio.create_task(
        process_api_request(prompt)
    )
    
    # Store the task
    pending_requests[task_id] = {
        "task": background_task,
        "result": None,
        "completed": False
    }
    
    # Return an immediate response that the request is being processed
    return f"Your request is being processed. Please check back in a moment with 'status:{task_id}'"

@mcp.tool()
async def check_request_status(task_id: str) -> str:
    """
    Check the status of a previously submitted conversation request.
    
    Args:
        task_id: The ID of the background task to check
        
    Returns:
        The assistant's response if ready, or a status message
    """
    if task_id not in pending_requests:
        return "Request not found. Please submit a new query."
    
    request_info = pending_requests[task_id]
    
    if request_info["completed"]:
        # Return the stored result and clean up
        result = request_info["result"]
        del pending_requests[task_id]
        return result
    
    # Check if the task is done
    if request_info["task"].done():
        try:
            # Get the result
            result = request_info["task"].result()
            request_info["result"] = result
            request_info["completed"] = True
            return result
        except Exception as e:
            request_info["result"] = f"Error processing request: {str(e)}"
            request_info["completed"] = True
            return request_info["result"]
    
    # Task is still running
    return "Your request is still being processed. Please check back in a moment."

async def process_api_request(prompt: str) -> str:
    """
    Process the API request in the background.
    """
    # API endpoint and headers
    url = "http://localhost:9020/api/v1/chat"
    headers = {
        "GBPI-API-Key": "gbpi_k4raTP9oHEAALEpUkKlUxkD2suzqM4NIZGGRpKxTufM",
        "Content-Type": "application/json"
    }
    
    # Prepare payload
    payload = {
        "prompt": prompt,
        "context": {}
    }
    
    # Process the API request
    try:
        # Create a simple session for the API call with a very generous timeout
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30) # 30 seconds timeout
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    assistant_response = f"Error from API: Status {response.status}, {text}"
                else:
                    result = await response.json()
                    # Extract the assistant's response from the result
                    assistant_response = result.get("response", "")
        
    except asyncio.TimeoutError:
        assistant_response = "Request timed out. Please try again later."
    except aiohttp.ClientError as e:
        assistant_response = f"Error calling the chat API: {str(e)}"
    except Exception as e:
        # Catch any other unexpected errors
        assistant_response = f"Unexpected error: {str(e)}"
    
    
    return assistant_response

# Set up the SSE transport for MCP communication.
sse = SseServerTransport("/messages/")

async def handle_sse(request: Request) -> None:
    _server = mcp._mcp_server
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await _server.run(reader, writer, _server.create_initialization_options())

# Create the Starlette app with two endpoints:
# - "/sse": for SSE connections from clients.
# - "/messages/": for handling incoming POST messages.
app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    # Use stdio transport instead to rule out transport issues
    uvicorn.run(app, host="0.0.0.0", port=8000)