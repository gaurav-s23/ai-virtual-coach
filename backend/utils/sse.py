"""
Server-Sent Events (SSE) utility for streaming responses
Supports real-time streaming for English drills, interviews, and mock tests
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.responses import Response

logger = logging.getLogger(__name__)

class SSEEvent:
    """SSE event wrapper"""
    
    def __init__(self, data: Any, event_type: str = "message", event_id: Optional[str] = None):
        self.data = data
        self.event_type = event_type
        self.event_id = event_id

    def format_sse(self) -> str:
        """Format event as SSE string"""
        lines = []
        
        if self.event_id:
            lines.append(f"id: {self.event_id}")
        
        if self.event_type:
            lines.append(f"event: {self.event_type}")
        
        # Handle different data types
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data)
        else:
            data_str = str(self.data)
        
        # Split multi-line data
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
        
        lines.append("")  # Empty line to end the event
        lines.append("")  # Extra empty line for safety
        
        return "\n".join(lines)

class SSEStreamer:
    """SSE streaming utility"""
    
    def __init__(self):
        self.active_connections: Dict[str, asyncio.Queue] = {}
    
    async def create_stream(self, stream_id: str) -> AsyncGenerator[str, None]:
        """Create a new SSE stream"""
        queue = asyncio.Queue()
        self.active_connections[stream_id] = queue
        
        try:
            # Send initial connection event
            yield SSEEvent(
                data={"status": "connected", "stream_id": stream_id},
                event_type="connection"
            ).format_sse()
            
            # Stream events from queue
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event.format_sse()
                except asyncio.TimeoutError:
                    # Send keep-alive event
                    yield SSEEvent(
                        data={"type": "keepalive"},
                        event_type="ping"
                    ).format_sse()
        except Exception as e:
            logger.error(f"Stream error for {stream_id}: {e}")
            yield SSEEvent(
                data={"error": str(e), "stream_id": stream_id},
                event_type="error"
            ).format_sse()
        finally:
            # Clean up connection
            self.active_connections.pop(stream_id, None)
            yield SSEEvent(
                data={"status": "disconnected", "stream_id": stream_id},
                event_type="disconnect"
            ).format_sse()
    
    async def send_event(self, stream_id: str, event: SSEEvent):
        """Send an event to a specific stream"""
        if stream_id in self.active_connections:
            try:
                await self.active_connections[stream_id].put(event.format_sse())
            except Exception as e:
                logger.error(f"Failed to send event to {stream_id}: {e}")
                # Clean up broken connection
                self.active_connections.pop(stream_id, None)
    
    async def send_data(self, stream_id: str, data: Any, event_type: str = "message"):
        """Send data to a specific stream"""
        event = SSEEvent(data=data, event_type=event_type)
        await self.send_event(stream_id, event)
    
    async def broadcast(self, data: Any, event_type: str = "broadcast"):
        """Broadcast to all active connections"""
        event = SSEEvent(data=data, event_type=event_type)
        for stream_id in list(self.active_connections.keys()):
            await self.send_event(stream_id, event)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

# Global SSE streamer instance
sse_streamer = SSEStreamer()

def create_sse_response(stream_generator: AsyncGenerator[str, None]) -> StreamingResponse:
    """Create FastAPI SSE response"""
    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
        }
    )

async def stream_llm_response(
    stream_id: str,
    llm_generator: AsyncGenerator[str, None],
    event_type: str = "message"
):
    """Stream LLM response via SSE"""
    try:
        async for chunk in llm_generator:
            await sse_streamer.send_data(
                stream_id=stream_id,
                data={"chunk": chunk, "type": "content"},
                event_type=event_type
            )
        
        # Send completion event
        await sse_streamer.send_data(
            stream_id=stream_id,
            data={"type": "complete"},
            event_type="complete"
        )
        
    except Exception as e:
        logger.error(f"Error streaming LLM response: {e}")
        await sse_streamer.send_data(
            stream_id=stream_id,
            data={"error": str(e), "type": "error"},
            event_type="error"
        )

async def stream_mock_test_response(
    stream_id: str,
    question_generator: AsyncGenerator[str, None]
):
    """Stream mock test questions via SSE"""
    await stream_llm_response(
        stream_id=stream_id,
        llm_generator=question_generator,
        event_type="mock_question"
    )

async def stream_interview_response(
    stream_id: str,
    response_generator: AsyncGenerator[str, None]
):
    """Stream interview responses via SSE"""
    await stream_llm_response(
        stream_id=stream_id,
        llm_generator=response_generator,
        event_type="interview_response"
    )

async def stream_english_drill_response(
    stream_id: str,
    drill_generator: AsyncGenerator[str, None]
):
    """Stream English drill responses via SSE"""
    await stream_llm_response(
        stream_id=stream_id,
        llm_generator=drill_generator,
        event_type="english_drill"
    )

# Helper functions for different streaming scenarios
async def create_mock_test_stream(
    stream_id: str,
    messages: list,
    context: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """Create mock test streaming response"""
    from services.llm_client import generate_mock_test_response
    
    try:
        response = await generate_mock_test_response(
            messages=messages,
            context=context,
            **kwargs
        )
        
        # Stream the response content
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            for word in content.split():
                yield word + " "
                await asyncio.sleep(0.05)  # Simulate streaming delay
        else:
            yield str(response)
            
    except Exception as e:
        logger.error(f"Mock test stream error: {e}")
        yield f"Error: {str(e)}"

async def create_interview_stream(
    stream_id: str,
    messages: list,
    context: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """Create interview streaming response"""
    from ..services.llm_client import generate_interview_response
    
    try:
        response = await generate_interview_response(
            messages=messages,
            context=context,
            **kwargs
        )
        
        # Stream the response content
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            for word in content.split():
                yield word + " "
                await asyncio.sleep(0.03)  # Simulate streaming delay
        else:
            yield str(response)
            
    except Exception as e:
        logger.error(f"Interview stream error: {e}")
        yield f"Error: {str(e)}"

async def create_english_drill_stream(
    stream_id: str,
    messages: list,
    context: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """Create English drill streaming response"""
    from ..services.llm_client import generate_english_response
    
    try:
        response_generator = await generate_english_response(
            messages=messages,
            context=context,
            stream=True,
            **kwargs
        )
        
        async for chunk in response_generator:
            yield chunk
            
    except Exception as e:
        logger.error(f"English drill stream error: {e}")
        yield f"Error: {str(e)}"
