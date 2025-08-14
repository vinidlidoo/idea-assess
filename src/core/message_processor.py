"""Message processing utilities for Claude SDK interactions."""

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from ..utils.debug_logging import DebugLogger


@dataclass
class ProcessedMessage:
    """Container for processed message data."""
    message_type: str
    content: List[str]
    search_queries: List[str]
    metadata: Dict[str, Any]


class MessageProcessor:
    """Handles processing of Claude SDK messages."""
    
    def __init__(self, logger: Optional[DebugLogger] = None):
        """
        Initialize the message processor.
        
        Args:
            logger: Optional debug logger
        """
        self.logger = logger or DebugLogger()
        self.message_count = 0
        self.search_count = 0
        self.result_text: List[str] = []
    
    def extract_session_id(self, message: Any) -> Optional[str]:
        """
        Extract session ID from a SystemMessage.
        
        Args:
            message: The message object to extract from
            
        Returns:
            Session ID if found, None otherwise
        """
        message_type = type(message).__name__
        if message_type == "SystemMessage" and hasattr(message, 'data'):
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
        message_type = type(message).__name__
        content = []
        search_queries = []
        metadata = {'message_number': self.message_count}
        
        # Extract session ID if available
        session_id = self.extract_session_id(message)
        if session_id:
            metadata['session_id'] = session_id
            if self.logger.enabled:
                self.logger.data["session_id"] = session_id
        
        # Process different message types
        if hasattr(message, 'content'):
            content, search_queries = self._extract_content(message.content)
            
        # Handle ResultMessage specially
        if message_type == "ResultMessage":
            if hasattr(message, 'result') and message.result:
                content = [str(message.result)]
            if hasattr(message, 'total_cost_usd') and message.total_cost_usd:
                metadata['cost_usd'] = message.total_cost_usd
        
        # Log if debug enabled
        if self.logger.enabled:
            self._log_message(message_type, content, search_queries, metadata)
        
        return ProcessedMessage(
            message_type=message_type,
            content=content,
            search_queries=search_queries,
            metadata=metadata
        )
    
    def _extract_content(self, msg_content: Any) -> Tuple[List[str], List[str]]:
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
                    print(f"  🔍 Search #{self.search_count}: {query} (may take 30-120s)...")
                    if self.logger.enabled:
                        self.logger.log_event(f"WebSearch #{self.search_count}: {query}")
                
                # Extract text content
                elif hasattr(block, 'text'):
                    text = block.text
                    text_content.append(text)
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
    
    def _log_message(self, message_type: str, content: List[str], 
                     search_queries: List[str], metadata: Dict[str, Any]) -> None:
        """Log message details for debugging."""
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
        
        self.logger.log_event(f"Message {self.message_count}: {message_type}", msg_data)
    
    def get_final_content(self) -> str:
        """
        Get the final aggregated content.
        
        Returns:
            Combined text content from all messages
        """
        return "".join(self.result_text)
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with message and search counts
        """
        return {
            'message_count': self.message_count,
            'search_count': self.search_count
        }