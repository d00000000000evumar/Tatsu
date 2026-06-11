"""
Tatsu AI — Intent Router
===========================
Classifies user intent to optimize tool selection and response strategy.
"""

import logging
import re

logger = logging.getLogger("tatsu.core.intent_router")


class IntentCategory:
    CONVERSATION = "conversation"       # General chat, greetings
    CALCULATION = "calculation"         # Math problems
    WEB_BROWSE = "web_browse"           # Open URLs, websites
    APP_LAUNCH = "app_launch"           # Launch applications
    FILE_OPERATION = "file_operation"   # File CRUD
    FILE_SEARCH = "file_search"         # Search files
    SYSTEM_INFO = "system_info"         # System monitoring
    TERMINAL = "terminal"              # Shell commands
    MEMORY = "memory"                  # Remember/recall
    PLANNING = "planning"              # Multi-step tasks
    UNKNOWN = "unknown"


class IntentRouter:
    """
    Fast, pattern-based intent classification.
    Provides hints to the agent about which tools are most relevant.
    The LLM still makes the final tool selection decision.
    """

    # Pattern → intent mappings
    PATTERNS = {
        IntentCategory.CALCULATION: [
            r"(?:what(?:'s| is)\s+)?\d+\s*[\+\-\*\/\^]",
            r"calculate|compute|solve|math|equation",
            r"(?:how much is|what is)\s+\d+",
            r"percent|percentage|average|sum|total",
        ],
        IntentCategory.WEB_BROWSE: [
            r"open\s+(?:the\s+)?(?:website|site|url|page|link)",
            r"open\s+(?:youtube|google|github|reddit|twitter|facebook|instagram)",
            r"go\s+to\s+\w+\.(?:com|org|net|io|dev)",
            r"search\s+(?:the\s+)?(?:web|internet|google|online)",
            r"browse|navigate\s+to",
        ],
        IntentCategory.APP_LAUNCH: [
            r"open\s+(?!the\s+(?:website|site|url|file|folder))(?:the\s+)?(?:\w+)",
            r"launch|start|run\s+(?:the\s+)?(?:\w+)",
            r"close\s+(?:\w+)",
        ],
        IntentCategory.FILE_OPERATION: [
            r"(?:create|make|new)\s+(?:a\s+)?(?:file|folder|directory)",
            r"delete|remove\s+(?:the\s+)?(?:file|folder)",
            r"move|copy|rename\s+(?:the\s+)?(?:file|folder)",
            r"read|show|display\s+(?:the\s+)?(?:file|contents)",
            r"list\s+(?:the\s+)?(?:files|folders|directory)",
        ],
        IntentCategory.FILE_SEARCH: [
            r"find|search|locate\s+(?:the\s+)?(?:file|folder|document)",
            r"where\s+is\s+(?:the\s+)?(?:file|folder)",
            r"look\s+for",
        ],
        IntentCategory.SYSTEM_INFO: [
            r"cpu|ram|memory|disk|battery|storage",
            r"system\s+(?:info|information|status|stats)",
            r"processes|running|uptime",
            r"how\s+much\s+(?:ram|memory|disk|storage)",
        ],
        IntentCategory.TERMINAL: [
            r"run\s+(?:the\s+)?command",
            r"execute|terminal|shell|cmd|powershell",
            r"pip\s+|npm\s+|git\s+",
        ],
        IntentCategory.MEMORY: [
            r"remember|memorize|save|store",
            r"recall|remind|what\s+(?:is|was)\s+my",
            r"forget|preference|setting",
        ],
        IntentCategory.PLANNING: [
            r"plan|strategy|steps|workflow",
            r"how\s+(?:do|can|should)\s+i",
            r"help\s+me\s+(?:with|to)\s+(?:\w+\s+)+",
        ],
    }

    def classify(self, message: str) -> tuple[str, float]:
        """
        Classify user intent based on message patterns.

        Returns:
            Tuple of (intent_category, confidence).
        """
        msg_lower = message.lower().strip()

        scores: dict[str, int] = {}
        for category, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    score += 1
            if score > 0:
                scores[category] = score

        if not scores:
            return IntentCategory.CONVERSATION, 0.5

        best = max(scores, key=scores.get)
        confidence = min(scores[best] / 3.0, 1.0)  # Normalize to 0-1
        return best, confidence

    def get_relevant_tools(self, intent: str) -> list[str]:
        """Get the most relevant tools for a given intent."""
        tool_map = {
            IntentCategory.CALCULATION: ["calculator"],
            IntentCategory.WEB_BROWSE: ["browser"],
            IntentCategory.APP_LAUNCH: ["app_launcher"],
            IntentCategory.FILE_OPERATION: ["file_manager"],
            IntentCategory.FILE_SEARCH: ["search"],
            IntentCategory.SYSTEM_INFO: ["system_info"],
            IntentCategory.TERMINAL: ["terminal"],
            IntentCategory.MEMORY: ["memory"],
            IntentCategory.PLANNING: ["task_planner"],
        }
        return tool_map.get(intent, [])
