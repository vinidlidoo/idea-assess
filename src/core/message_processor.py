"""Message processing utilities for Claude SDK interactions."""

import re
from typing import Optional, Any
from dataclasses import dataclass
from ..utils.improved_logging import StructuredLogger
from ..core.constants import MAX_CONTENT_SIZE

# Try to import SDK message types
try:
    from claude_code_sdk import SystemMessage, ResultMessage, UserMessage, AssistantMessage
    HAS_SDK_TYPES = True
except ImportError:
    # Fallback if SDK doesn't export these types
    HAS_SDK_TYPES = False
    SystemMessage = type('SystemMessage', (), {})
    ResultMessage = type('ResultMessage', (), {})
    UserMessage = type('UserMessage', (), {})
    AssistantMessage = type('AssistantMessage', (), {})


@dataclass
class ProcessedMessage:
    """Container for processed message data."""
    message_type: str
    content: list[str]
    search_queries: list[str]
    metadata: dict[str, Any]


class MessageProcessor:
    """Handles processing of Claude SDK messages."""
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize the message processor.
        
        Args:
            logger: Optional structured logger
        """
        self.logger = logger
        self.message_count = 0
        self.search_count = 0
        self.result_text: list[str] = []
    
    def extract_session_id(self, message: Any) -> Optional[str]:
        """
        Extract session ID from a SystemMessage.
        
        Args:
            message: The message object to extract from
            
        Returns:
            Session ID if found, None otherwise
        """
        # Use isinstance check if SDK types are available
        if HAS_SDK_TYPES:
            is_system_message = isinstance(message, SystemMessage)
        else:
            is_system_message = type(message).__name__ == "SystemMessage"
        
        if is_system_message and hasattr(message, 'data'):
            data_str = str(getattr(message, 'data', ''))
            match = re.search(r"'session_id':\s*'([^']+)'", data_str)
            if match:
                return match.group(1)
        return None
    
    def process_message(self, message: Any) -> ProcessedMessage:
        """
        Process a single message from Claude SDK.
        
        Args:
            message: The message to process
            
        Returns:
            ProcessedMessage with extracted data
        """
        self.message_count += 1
        
        message_type = self._get_message_type(message)
        
        content = []
        search_queries = []
        metadata = {'message_number': self.message_count}
        
        # Extract session ID if available
        session_id = self.extract_session_id(message)
        if session_id:
            metadata['session_id'] = session_id
        
        # Process different message types
        if hasattr(message, 'content'):
            content, search_queries = self._extract_content(message.content)
            
        # Handle ResultMessage specially
        if self._is_result_message(message):
            if hasattr(message, 'result') and message.result:
                content = [str(message.result)]
            if hasattr(message, 'total_cost_usd') and message.total_cost_usd:
                metadata['cost_usd'] = message.total_cost_usd
        
        # Log if logger is available
        if self.logger:
            self._log_message(message_type, content, search_queries, metadata)
        
        result = ProcessedMessage(
            message_type=message_type,
            content=content,
            search_queries=search_queries,
            metadata=metadata
        )
        return result
    
    def _extract_content(self, msg_content: Any) -> tuple[list[str], list[str]]:
        """
        Extract text content and search queries from message content.
        
        Args:
            msg_content: The content to extract from
            
        Returns:
            Tuple of (text_content, search_queries)
        """
        text_content = []
        search_queries = []
        
        if isinstance(msg_content, str):
            text_content.append(msg_content)
        elif isinstance(msg_content, list):
            for block in msg_content:
                # Check for WebSearch tool usage
                if hasattr(block, 'name') and block.name == "WebSearch":
                    self.search_count += 1
                    query = getattr(block, 'input', {}).get('query', 'unknown')
                    search_queries.append(query)
                    import sys
                    print(f"  🔍 Search #{self.search_count}: {query} (may take 30-120s)...", file=sys.stderr, flush=True)
                    if self.logger:
                        self.logger.log_event("websearch_query", "MessageProcessor", {
                            "search_number": self.search_count,
                            "query": query
                        })
                
                # Extract text content
                elif hasattr(block, 'text'):
                    text = block.text
                    text_content.append(text)
                    
                    # Check memory limit before appending
                    current_size = sum(len(t) for t in self.result_text)
                    if current_size + len(text) > MAX_CONTENT_SIZE:
                        print(f"⚠️  Warning: Content size limit ({MAX_CONTENT_SIZE} bytes) reached")
                        # Truncate text to fit within limit
                        remaining = MAX_CONTENT_SIZE - current_size
                        if remaining > 0:
                            self.result_text.append(text[:remaining])
                    else:
                        self.result_text.append(text)
                
                # Handle tool result blocks
                elif hasattr(block, 'content'):
                    block_content = block.content
                    if isinstance(block_content, str):
                        # Extract search query from result
                        query_match = re.search(r'query:\s*["\']([^"\']+)["\']', block_content)
                        if query_match:
                            search_queries.append(f"Result: {query_match.group(1)}")
        
        return text_content, search_queries
    
    def _log_message(self, message_type: str, content: list[str], 
                     search_queries: list[str], metadata: dict[str, Any]) -> None:
        """Log message details using StructuredLogger."""
        msg_data = {
            "number": self.message_count,
            "type": message_type,
            **metadata
        }
        
        if content:
            # Add preview of first 200 chars
            preview = content[0][:200] + "..." if len(content[0]) > 200 else content[0]
            msg_data["content_preview"] = preview.replace('\n', ' ')
        
        if search_queries:
            msg_data["search_queries"] = search_queries
        
        if self.logger:
            self.logger.log_event(
                f"sdk_message_{message_type.lower()}",
                "MessageProcessor",
                msg_data
            )
    
    def get_final_content(self) -> str:
        """
        Get the final aggregated content.
        
        Returns:
            Combined text content from all messages
        """
        return "".join(self.result_text)
    
    def _get_message_type(self, message: Any) -> str:
        """
        Get the type name of a message using isinstance checks when possible.
        
        Args:
            message: The message to check
            
        Returns:
            String name of the message type
        """
        if HAS_SDK_TYPES:
            if isinstance(message, SystemMessage):
                return "SystemMessage"
            elif isinstance(message, ResultMessage):
                return "ResultMessage"
            elif isinstance(message, UserMessage):
                return "UserMessage"
            elif isinstance(message, AssistantMessage):
                return "AssistantMessage"
        
        # Fallback to string comparison
        return type(message).__name__
    
    def _is_result_message(self, message: Any) -> bool:
        """
        Check if a message is a ResultMessage.
        
        Args:
            message: The message to check
            
        Returns:
            True if it's a ResultMessage, False otherwise
        """
        if HAS_SDK_TYPES:
            return isinstance(message, ResultMessage)
        return type(message).__name__ == "ResultMessage"
    
    def get_statistics(self) -> dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with message and search counts
        """
        return {
            'message_count': self.message_count,
            'search_count': self.search_count
        }