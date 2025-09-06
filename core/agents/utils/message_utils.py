"""
Message utilities for managing debate turns and preventing content duplication.
Follows Linus Torvalds' principle: "Good programmers worry about data structures"
"""

from typing import List, Optional, Dict
from datetime import datetime
from core.agents.utils.agent_states import DebateTurn
import re
import hashlib

# 导入日志模块
from core.utils.logging_init import get_logger
logger = get_logger("agents")


def get_relevant_context(
    debate_turns: List[DebateTurn],
    current_speaker: str,
    max_context: int = 3
) -> List[DebateTurn]:
    """
    Get relevant context for a speaker (Linus: eliminate special cases).
    
    Args:
        debate_turns: All debate turns
        current_speaker: The speaker who needs context
        max_context: Maximum number of recent turns to include
        
    Returns:
        List of relevant recent turns (excluding current speaker's own history)
    """
    if not debate_turns:
        return []
    
    # Get the most recent turns
    recent_turns = debate_turns[-max_context:] if len(debate_turns) > max_context else debate_turns
    
    # Filter out the current speaker's own previous turns
    # This prevents self-referencing and reduces repetition
    relevant_turns = [
        turn for turn in recent_turns 
        if turn.get("speaker", "").lower() != current_speaker.lower()
    ]
    
    return relevant_turns


def add_debate_turn(
    debate_turns: List[DebateTurn],
    speaker: str,
    content: str,
    turn: Optional[int] = None
) -> List[DebateTurn]:
    """
    Add a new debate turn with deduplication (Linus: keep it simple).
    
    Args:
        debate_turns: Existing debate turns
        speaker: Speaker name
        content: Content to add
        turn: Turn number (auto-increment if not provided)
        
    Returns:
        Updated list of debate turns
    """
    # Clean the content
    cleaned_content = clean_content(content)
    
    # Check for duplicate content
    if is_duplicate_content(debate_turns, cleaned_content):
        logger.warning(f"Duplicate content detected for {speaker}, skipping")
        return debate_turns
    
    # Auto-increment turn number if not provided
    if turn is None:
        turn = len(debate_turns) + 1
    
    # Create new turn
    new_turn = DebateTurn(
        speaker=speaker,
        content=cleaned_content,
        turn=turn,
        timestamp=datetime.now()
    )
    
    # Return new list (immutable update)
    return debate_turns + [new_turn]


def clean_content(content: str) -> str:
    """
    Clean content by removing UI elements and formatting issues.
    
    Args:
        content: Raw content
        
    Returns:
        Cleaned content
    """
    if not content:
        return ""
    
    # Remove UI elements
    ui_patterns = [
        r'收起|展开',  # Chinese UI elements
        r'Continue',  # Placeholder text
        r'\[Msg Clear.*?\]',  # Debug messages
        r'^\s*$',  # Empty lines
    ]
    
    cleaned = content
    for pattern in ui_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned


def is_duplicate_content(
    debate_turns: List[DebateTurn],
    content: str,
    similarity_threshold: float = 0.85
) -> bool:
    """
    Check if content is duplicate using hash comparison.
    
    Args:
        debate_turns: Existing debate turns
        content: Content to check
        similarity_threshold: Threshold for similarity (not used in hash comparison)
        
    Returns:
        True if content is duplicate
    """
    if not debate_turns or not content:
        return False
    
    # Generate content hash for comparison
    content_hash = generate_content_hash(content)
    
    # Check against recent turns
    for turn in debate_turns[-5:]:  # Only check last 5 turns for performance
        if generate_content_hash(turn.get("content", "")) == content_hash:
            return True
    
    return False


def generate_content_hash(content: str) -> str:
    """
    Generate a hash for content comparison.
    
    Args:
        content: Content to hash
        
    Returns:
        Hash string
    """
    # Normalize content for comparison
    normalized = content.lower().strip()
    # Remove all whitespace for comparison
    normalized = re.sub(r'\s+', '', normalized)
    
    # Generate hash
    return hashlib.md5(normalized.encode()).hexdigest()


def format_context_for_prompt(
    debate_turns: List[DebateTurn],
    current_speaker: str,
    max_context: int = 3
) -> str:
    """
    Format relevant context for inclusion in a prompt.
    
    Args:
        debate_turns: All debate turns
        current_speaker: The current speaker
        max_context: Maximum context to include
        
    Returns:
        Formatted context string
    """
    relevant_turns = get_relevant_context(debate_turns, current_speaker, max_context)
    
    if not relevant_turns:
        return "No previous discussion yet."
    
    formatted_parts = []
    for turn in relevant_turns:
        speaker = turn.get("speaker", "Unknown")
        content = turn.get("content", "")
        formatted_parts.append(f"{speaker}: {content}")
    
    return "\n\n".join(formatted_parts)


def get_last_turn_for_speaker(
    debate_turns: List[DebateTurn],
    speaker: str
) -> Optional[str]:
    """
    Get the last turn content for a specific speaker.
    
    Args:
        debate_turns: All debate turns
        speaker: Speaker to find
        
    Returns:
        Last content from that speaker or None
    """
    for turn in reversed(debate_turns):
        if turn.get("speaker", "").lower() == speaker.lower():
            return turn.get("content", "")
    return None


def summarize_debate(debate_turns: List[DebateTurn], max_length: int = 500) -> str:
    """
    Summarize the debate for final reporting.
    
    Args:
        debate_turns: All debate turns
        max_length: Maximum length for each speaker's summary
        
    Returns:
        Summary string
    """
    if not debate_turns:
        return "No debate occurred."
    
    # Group by speaker
    speaker_contents: Dict[str, List[str]] = {}
    for turn in debate_turns:
        speaker = turn.get("speaker", "Unknown")
        content = turn.get("content", "")
        if speaker not in speaker_contents:
            speaker_contents[speaker] = []
        speaker_contents[speaker].append(content)
    
    # Summarize each speaker's position
    summaries = []
    for speaker, contents in speaker_contents.items():
        # Take the last contribution as most representative
        last_content = contents[-1] if contents else ""
        if len(last_content) > max_length:
            last_content = last_content[:max_length] + "..."
        summaries.append(f"{speaker}: {last_content}")
    
    return "\n\n".join(summaries)