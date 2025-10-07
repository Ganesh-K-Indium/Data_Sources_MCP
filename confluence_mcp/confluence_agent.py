"""
LangGraph + GPT-4.1 Agent using Confluence MCP HTTP Streaming Server
-------------------------------------------------------------------
Connects to FastMCP Confluence Operations server using streamable HTTP transport.
"""

import asyncio
import aiohttp
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from dotenv import load_dotenv
import os, json
from datetime import datetime

load_dotenv()


async def wait_for_server(url: str, timeout: int = 10):
    """Wait until the MCP server is ready to accept connections."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status in (200, 404):  # 404 is fine, stream endpoint doesn't return JSON
                        print(f"✅ MCP server is up at {url}")
                        return True
        except aiohttp.ClientConnectionError:
            await asyncio.sleep(1)
    raise TimeoutError(f"MCP server at {url} did not respond within {timeout} seconds")


async def main():
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    MCP_HTTP_STREAM_URL = "http://localhost:8001/mcp"

    async with streamablehttp_client(MCP_HTTP_STREAM_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("✅ MCP Client Session initialized")
            tools = await load_mcp_tools(session)
            print(f"✅ Loaded {len(tools)} Confluence MCP tools via HTTP stream")
            agent = create_react_agent(
                model=model,
                tools=tools,
                name="ConfluenceLangGraphAgent"
            )
            
            # Example prompts - you can modify these
            user_prompt = "list attachments from space test"
            
            print(f"\n🧠 Running agent with prompt:\n{user_prompt}\n")

            response = await agent.ainvoke({"messages": user_prompt})
            print("\n🤖 Agent Response:\n", response)

            def serialize_response(obj):
                if isinstance(obj, dict):
                    return {k: serialize_response(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_response(item) for item in obj]
                elif hasattr(obj, 'dict'):
                    return obj.dict()
                else:
                    return str(obj)
            
            responses_dir = os.path.join(os.path.dirname(__file__), "responses")
            os.makedirs(responses_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"response_{timestamp}.json"
            filepath = os.path.join(responses_dir, filename)
            with open(filepath, "w") as f:
                json.dump(serialize_response(response), f, indent=4)
            print(f"📁 Response saved to {filepath}")

if __name__ == "__main__":
    asyncio.run(main())