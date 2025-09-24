from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import json
import time
import random
import requests
from datetime import datetime, timedelta
import base64
import io
from PIL import Image
import math
import logging
from typing import Optional, List, Dict
import hashlib
import html
import uvicorn
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Novarsis Support Center", description="AI Support Assistant for Novarsis SEO Tool")

# Configure Ollama API - UPDATED FOR HOSTED SERVICE
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY",
                           "14bfe5365cc246dc82d933e3af2aa5b6.hz2asqgJi2bO_gpN7Cp1Hcku")  # Empty default, will be set via environment
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")  # Default to hosted service
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")  # Default model
USE_HOSTED_OLLAMA = True  # Always use hosted service

# Initialize Ollama model
model = True  # We'll assume it's available and handle errors in the API call

# Initialize embedding model - Ollama doesn't have a direct embedding API like Gemini
# So we'll use keyword-based filtering only
reference_embedding = None
embedding_model = None
logger.info("Using keyword-based filtering (Ollama doesn't provide embedding API)")

# Constants
WHATSAPP_NUMBER = "+91-9999999999"
SUPPORT_EMAIL = "support@novarsis.tech"

# Enhanced System Prompt
SYSTEM_PROMPT = """You are Nova, the official AI support assistant for Novarsis AIO SEO Tool.

PERSONALITY:
- Natural and conversational like a human
- Friendly and approachable
- Brief but complete responses
- Polite and professional
- Ensure proper grammar with correct spacing and punctuation

INTRO RESPONSES:
- Who are you? → "I'm Nova, your personal assistant for Novarsis SEO Tool. I help users with SEO analysis, reports, account issues, and technical support."
- How can you help? → "I can help you with SEO website analysis, generating reports, fixing errors, managing subscriptions, and troubleshooting any Novarsis tool issues."
- What can you do? → "I assist with all Novarsis features - SEO audits, competitor analysis, keyword tracking, technical issues, billing, and more."

SCOPE:
Answer ALL questions naturally, but stay within Novarsis context:
• Greetings → Respond naturally (Hello! How can I help you today?)
• About yourself → Explain your role as Novarsis assistant
• Capabilities → List what you can help with
• Tool features → Explain Novarsis features
• Technical help → Provide solutions
• Account/billing → Assist with subscriptions

ONLY REDIRECT for completely unrelated topics like:
- Cooking recipes, travel advice, general knowledge
- Non-SEO tools or competitors
- Personal advice unrelated to SEO

For unrelated queries, politely say:
"Sorry, I only help with Novarsis SEO Tool.
Please let me know if you have any SEO tool related questions?"

RESPONSE STYLE:
- Natural conversation flow
- Answer directly without overthinking
- 2-4 lines for simple queries
- Use simple, everyday language
- Always use proper grammar with spaces between words and correct punctuation
- When user greets with a problem (e.g., "hi, what are features?"), skip greeting and answer directly
- Only greet back when user sends ONLY a greeting (like just "hi" or "hello")

TICKET GENERATION RULES:
- IMPORTANT: Only generate a ticket number when the user has agreed to have a ticket opened. When the user says 'yes' to your offer to open a ticket, then you must include a ticket number in format: NVS##### in your response.
- Example: When the user says 'yes' to your offer, respond: 'I've opened a support ticket for you. Ticket Number: NVS[RANDOM_5_DIGIT]. The ticket is now in progress, and an expert will reach out shortly.'
- Always format as 'Ticket Number: NVS#####' or 'Ticket ID: NVS#####' with the ticket number on the same line (no line breaks)
- Generate a RANDOM 5-digit number after NVS (e.g., NVS73534, NVS89421, NVS45678). NEVER use NVS12345 as it's just an example.
- When mentioning ticket status, always include the ticket number
- CRITICAL: The ticket number must always be a continuous string without any line breaks or spaces in the middle (e.g., NVS73534, not NVS\n73534 or NVS 73534)

SPECIAL INSTRUCTIONS:
1. If the user asks for SEO analysis of a website, do not perform the analysis. Instead, guide them on how to do it in the Novarsis tool and offer to raise a ticket if they face issues.
2. IMPORTANT: When user asks about features of the tool, ONLY list the features. DO NOT mention pricing plans unless specifically asked about pricing, plans, or costs. Features include:
   - Site audits with technical issue detection
   - Keyword research and tracking
   - Competitor analysis and gap identification
   - Backlink monitoring and reporting
   - On-page optimization suggestions
   - Rank tracking across multiple search engines
   - API access for integration
   - Customizable report generation
   - Mobile optimization analysis
   - Page speed monitoring
   - Schema markup validation
   - XML sitemap analysis
3. When comparing pricing plans (ONLY when asked about pricing/plans/costs), you MUST use this exact format with each bullet point on a new line:

Free Plan:
Up to 5 websites 
- Full access to all SEO tools 
- Generate reports 
- No credit card required

Pro Plan:
Up to 50 websites 
- All Free features 
- Priority support 
- API access 
- $49 per month

Enterprise Plan:
Unlimited websites (custom limits) 
- All Pro features 
- Dedicated account manager 
- SLA guarantees 
- Custom integrations 
- Contact sales for a quote

Would you like me to connect with an expert for the Enterprise model?

4. If the user mentions multiple problems, address each one in your response.
5. At the end of your response, if you feel the answer might be incomplete or the user might need more help, ask: "Have I solved your query?" If the user says no, then offer to connect with an expert and create a support ticket.
6. IMPORTANT: Never ask more than one question in a single response. This means:
   - If you have already asked a question (like the enterprise model question or an offer to open a ticket), do not ask 'Have I solved your query?' in the same response.
   - If you are going to ask 'Have I solved your query?', do not ask any other question in the same response.
7. If the user provides an email address, acknowledge it and continue the conversation. Do not restart the chat.
8. GREETING RULES:
   - If user says ONLY "hi", "hello", "hey" (single greeting), respond with: "Hello! I'm Nova, your personal assistant. How can I help you today?"
   - If user says greeting + problem (e.g., "hi, what are the features?"), SKIP the greeting and directly address the problem
   - Never start with a greeting when the user has already asked a question with their greeting
9. When offering to create a support ticket, use the phrase: "For more information, Shall I raise a support ticket for you?" instead of other variations. This question should always appear on a new line.
10. IMPORTANT: When you indicate that the issue is being handled by the team (e.g., "Our team will review", "get back to you", "working on your issue"), do NOT ask "Have I solved your query?" because the issue is not yet resolved.
11. When asked about features, NEVER include pricing information unless explicitly asked. Only list the tool's features.
"""

# Context-based quick reply suggestions
QUICK_REPLY_SUGGESTIONS = {
    "initial": [
        "How do I analyze my website SEO?",
        "Check my subscription status",
        "I'm getting an error message",
        "Generate SEO report",
        "Compare pricing plans",
        "Check ticket status",
        "Connect with an Expert"
    ],
    "seo_analysis": [
        "How to improve my SEO score?",
        "What are meta tags?",
        "Check page load speed",
        "Analyze competitor websites",
        "Mobile optimization tips"
    ],
    "account": [
        "Upgrade my plan",
        "Reset my password",
        "View billing history",
        "Cancel subscription",
        "Update payment method"
    ],
    "technical": [
        "API integration help",
        "Report not generating",
        "Login issues",
        "Data sync problems",
        "Browser compatibility",
        "Connect with an Expert"
    ],
    "report": [
        "Schedule automatic reports",
        "Export to PDF",
        "Share report with team",
        "Customize report sections",
        "Historical data comparison"
    ],
    "error": [
        "Website not loading",
        "Analysis stuck at 0%",
        "404 error on dashboard",
        "Payment failed",
        "Can't access reports",
        "Connect with an Expert"
    ],
    "pricing": [
        "What's included in Premium?",
        "Student discount available?",
        "Annual vs monthly billing",
        "Team plans pricing",
        "Free trial details"
    ]
}


def get_context_suggestions(message: str) -> list:
    """Get relevant quick reply suggestions based on user's input context."""
    if not message or len(message.strip()) < 2:
        return QUICK_REPLY_SUGGESTIONS["initial"]

    message_lower = message.lower().strip()

    # Return empty if message is very short
    if len(message_lower) < 3:
        return []

    # Check for specific actions first
    if any(word in message_lower for word in ['ticket', 'status', 'track', 'nvs']):
        return ["Check ticket status", "Connect with an Expert", "View all tickets", "Create new ticket"]
    elif any(word in message_lower for word in ['expert', 'human', 'agent', 'support', 'help']):
        return ["Connect with an Expert", "Check ticket status", "Call support", "Email support"]
    # Check for keywords and return appropriate suggestions
    elif any(
            word in message_lower for word in ['seo', 'analysis', 'analyze', 'score', 'optimization', 'meta', 'crawl']):
        return QUICK_REPLY_SUGGESTIONS["seo_analysis"]
    elif any(word in message_lower for word in
             ['account', 'subscription', 'plan', 'billing', 'payment', 'upgrade', 'cancel']):
        return QUICK_REPLY_SUGGESTIONS["account"]
    elif any(word in message_lower for word in
             ['error', 'issue', 'problem', 'not working', 'failed', 'stuck', 'broken']):
        return QUICK_REPLY_SUGGESTIONS["error"]
    elif any(word in message_lower for word in ['report', 'export', 'pdf', 'schedule', 'download']):
        return QUICK_REPLY_SUGGESTIONS["report"]
    elif any(word in message_lower for word in ['api', 'integration', 'technical', 'login', 'password']):
        return QUICK_REPLY_SUGGESTIONS["technical"]
    elif any(word in message_lower for word in ['price', 'pricing', 'cost', 'plan', 'cheap', 'expensive', 'free']):
        return QUICK_REPLY_SUGGESTIONS["pricing"]
    elif any(word in message_lower for word in ['how', 'what', 'why', 'when', 'where']):
        # For question words, show initial helpful suggestions
        return QUICK_REPLY_SUGGESTIONS["initial"]
    else:
        return []


# Novarsis Keywords - expanded for better detection
NOVARSIS_KEYWORDS = [
    'novarsis', 'seo', 'website analysis', 'meta tags', 'page structure', 'link analysis',
    'seo check', 'seo report', 'subscription', 'account', 'billing', 'plan', 'premium',
    'starter', 'error', 'bug', 'issue', 'problem', 'not working', 'failed', 'crash',
    'login', 'password', 'analysis', 'report', 'dashboard', 'settings', 'integration',
    'google', 'api', 'website', 'url', 'scan', 'audit', 'optimization', 'mobile', 'speed',
    'performance', 'competitor', 'ranking', 'keywords', 'backlinks', 'technical seo',
    'canonical', 'schema', 'sitemap', 'robots.txt', 'crawl', 'index', 'search console',
    'analytics', 'traffic', 'organic', 'serp'
]

# Casual/intro keywords that should be allowed
CAUSAL_ALLOWED = [
    'hello', 'hi', 'hey', 'who are you', 'what are you', 'what can you do',
    'how can you help', 'help me', 'assist', 'support', 'thanks', 'thank you',
    'bye', 'goodbye', 'good morning', 'good afternoon', 'good evening',
    'yes', 'no', 'okay', 'ok', 'sure', 'please', 'sorry'
]

# Clearly unrelated topics that should be filtered
UNRELATED_TOPICS = [
    'recipe', 'cooking', 'food', 'biryani', 'pizza', 'travel', 'vacation',
    'movie', 'song', 'music', 'game', 'sports', 'cricket', 'football',
    'weather', 'politics', 'news', 'stock', 'crypto', 'bitcoin',
    'medical', 'doctor', 'medicine', 'disease', 'health'
]

# Greeting keywords
GREETING_KEYWORDS = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]

# Set up templates - with error handling
try:
    templates = Jinja2Templates(directory="templates")
    logger.info("Templates initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize templates: {str(e)}")


    # Create a simple fallback template renderer
    class SimpleTemplates:
        def __init__(self, directory):
            self.directory = directory

        def TemplateResponse(self, name, context):
            # Simple fallback - just return a basic HTML response
            return HTMLResponse(
                "<html><body><h1>Novarsis Support Center</h1><p>Template rendering failed. Please check server logs.</p></body></html>")


    templates = SimpleTemplates("templates")


# FAST MCP - Fast Adaptive Semantic Transfer with Memory Context Protocol
class FastMCP:
    def __init__(self):
        self.conversation_memory = []  # Full conversation memory
        self.context_window = []  # Recent context (last 10 messages)
        self.user_intent = None  # Current user intent
        self.topic_stack = []  # Stack of conversation topics
        self.entities = {}  # Named entities extracted
        self.user_profile = {
            "name": None,
            "plan": None,
            "issues_faced": [],
            "preferred_style": "concise",
            "interaction_count": 0
        }
        self.conversation_state = {
            "expecting_response": None,  # What type of response we're expecting
            "last_question": None,  # Last question asked by bot
            "pending_action": None,  # Any pending action
            "emotional_tone": "neutral"  # User's emotional state
        }

    def update_context(self, role, message):
        """Update conversation context with new message"""
        entry = {
            "role": role,
            "content": message,
            "timestamp": datetime.now(),
            "intent": self.extract_intent(message) if role == "user" else None
        }

        self.conversation_memory.append(entry)
        self.context_window.append(entry)

        # Keep context window to last 10 messages
        if len(self.context_window) > 10:
            self.context_window.pop(0)

        if role == "user":
            self.analyze_user_message(message)
        else:
            self.analyze_bot_response(message)

    def extract_intent(self, message):
        """Extract user intent from message"""
        message_lower = message.lower()

        # Intent patterns
        if any(word in message_lower for word in ['how', 'what', 'where', 'when', 'why']):
            return "question"
        elif any(word in message_lower for word in ['yes', 'yeah', 'sure', 'okay', 'ok', 'yep', 'yup']):
            return "confirmation"
        elif any(word in message_lower for word in ['no', 'nope', 'nah', 'not']):
            return "denial"
        elif any(word in message_lower for word in ['help', 'assist', 'support']):
            return "help_request"
        elif any(word in message_lower for word in ['error', 'issue', 'problem', 'broken', 'not working']):
            return "problem_report"
        elif any(word in message_lower for word in ['thanks', 'thank you', 'appreciate']):
            return "gratitude"
        elif any(word in message_lower for word in ['more', 'elaborate', 'explain', 'detail']):
            return "elaboration_request"
        else:
            return "statement"

    def analyze_user_message(self, message):
        """Analyze user message for context and emotion"""
        message_lower = message.lower()

        # Update emotional tone
        if any(word in message_lower for word in ['urgent', 'asap', 'immediately', 'quickly']):
            self.conversation_state["emotional_tone"] = "urgent"
        elif any(word in message_lower for word in ['frustrated', 'annoyed', 'angry', 'upset']):
            self.conversation_state["emotional_tone"] = "frustrated"
        elif any(word in message_lower for word in ['please', 'thanks', 'appreciate']):
            self.conversation_state["emotional_tone"] = "polite"

        # Extract entities
        if 'website' in message_lower or 'site' in message_lower:
            self.entities['subject'] = 'website'
        if 'seo' in message_lower:
            self.entities['subject'] = 'seo'
        if 'report' in message_lower:
            self.entities['subject'] = 'report'

        self.user_profile["interaction_count"] += 1

    def analyze_bot_response(self, message):
        """Track what the bot asked or offered"""
        message_lower = message.lower()

        if '?' in message:
            self.conversation_state["last_question"] = message
            self.conversation_state["expecting_response"] = "answer"

        if 'need more help' in message_lower or 'need help' in message_lower:
            self.conversation_state["expecting_response"] = "help_confirmation"

        if 'try these steps' in message_lower or 'follow these' in message_lower:
            self.conversation_state["expecting_response"] = "feedback_on_solution"

    def get_context_prompt(self):
        """Generate context-aware prompt for AI"""
        context_parts = []

        # Add conversation history
        if self.context_window:
            context_parts.append("=== Conversation Context ===")
            for entry in self.context_window[-5:]:  # Last 5 messages
                role = "User" if entry["role"] == "user" else "Assistant"
                context_parts.append(f"{role}: {entry['content']}")

        # Add conversation state
        if self.conversation_state["expecting_response"]:
            context_parts.append(f"\n[Expecting: {self.conversation_state['expecting_response']}]")

        if self.conversation_state["emotional_tone"] != "neutral":
            context_parts.append(f"[User tone: {self.conversation_state['emotional_tone']}]")

        if self.entities:
            context_parts.append(f"[Current topic: {', '.join(self.entities.values())}]")

        return "\n".join(context_parts)

    def should_filter_novarsis(self, message):
        """Determine if Novarsis filter should be applied"""
        # Don't filter if we're expecting a response to our question
        if self.conversation_state["expecting_response"] in ["help_confirmation", "answer", "feedback_on_solution"]:
            return False

        # Don't filter for contextual responses
        intent = self.extract_intent(message)
        if intent in ["confirmation", "denial", "elaboration_request"]:
            return False

        return True


# Initialize FAST MCP
fast_mcp = FastMCP()

# Global session state (in a real app, you'd use Redis or a database)
session_state = {
    "chat_history": [],
    "unresolved_queries": [],
    "support_tickets": {},
    "current_plan": None,
    "current_query": {},
    "typing": False,
    "user_name": "User",
    "session_start": datetime.now(),
    "resolved_count": 0,
    "pending_input": None,
    "uploaded_file": None,
    "checking_ticket_status": False,
    "intro_given": False,
    "last_user_query": "",
    "fast_mcp": fast_mcp,  # Add FAST MCP to session
    "last_bot_message_ends_with_query_solved": False
}

# Initialize current plan
plans = [
    {"name": "STARTER", "price": "$100/Year", "validity": "Valid till: Dec 31, 2025",
     "features": ["5 Websites", "Monthly Reports", "Email Support"]},
    {"name": "PREMIUM", "price": "$150/Year", "validity": "Valid till: Dec 31, 2025",
     "features": ["Unlimited Websites", "Real-time Reports", "Priority Support", "API Access"]}
]
session_state["current_plan"] = random.choice(plans)


# Pydantic models for API
class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime
    show_feedback: bool = True  # Changed default to True


class ChatRequest(BaseModel):
    message: str
    image_data: Optional[str] = None


class TicketStatusRequest(BaseModel):
    ticket_id: str


class FeedbackRequest(BaseModel):
    feedback: str
    message_index: int


# Helper Functions
def generate_avatar_initial(name):
    return name[0].upper()


def format_time(timestamp):
    return timestamp.strftime("%I:%M %p")


def cosine_similarity(vec1, vec2):
    if len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def is_greeting(query: str) -> bool:
    query_lower = query.lower().strip()
    return any(greeting in query_lower for greeting in GREETING_KEYWORDS)


def is_casual_allowed(query: str) -> bool:
    """Check if it's a casual/intro question that should be allowed"""
    query_lower = query.lower().strip()
    return any(word in query_lower for word in CAUSAL_ALLOWED)


def is_clearly_unrelated(query: str) -> bool:
    """Check if query is clearly unrelated to our tool"""
    query_lower = query.lower().strip()
    return any(topic in query_lower for topic in UNRELATED_TOPICS)


def is_novarsis_related(query: str) -> bool:
    # First check if it's a casual/intro question - always allow these
    if is_casual_allowed(query):
        return True

    # Check if it's clearly unrelated - always filter these
    if is_clearly_unrelated(query):
        return False

    # Since Ollama doesn't have embedding API, we use keyword-based filtering
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in NOVARSIS_KEYWORDS)


def get_intro_response() -> str:
    return "Hello! I'm Nova, your personal assistant. How can I help you today?"


def call_ollama_api(prompt: str, image_data: Optional[str] = None) -> str:
    """Call Ollama API with the prompt - supports both local and hosted Ollama"""
    try:
        # Check if using hosted service with API key
        if OLLAMA_API_KEY and USE_HOSTED_OLLAMA:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OLLAMA_API_KEY}"
            }
        else:
            # Local Ollama doesn't need auth
            headers = {
                "Content-Type": "application/json"
            }

        # Try different API formats based on service type
        if USE_HOSTED_OLLAMA:
            # Hosted service uses OpenAI compatible endpoint
            data = {
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.7
            }
            endpoint = f"{OLLAMA_BASE_URL}/v1/chat/completions"  # OpenAI compatible endpoint
        else:
            # Local Ollama format
            data = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
            endpoint = f"{OLLAMA_BASE_URL}/api/generate"

        # If there's image data, include it (for vision models)
        if image_data and not USE_HOSTED_OLLAMA:
            data["images"] = [image_data]

        logger.info(f"Calling Ollama API at: {endpoint}")

        # Make the API call with increased timeout
        response = requests.post(
            endpoint,
            headers=headers,
            json=data,
            timeout=60  # 60 seconds timeout
        )

        logger.info(f"Ollama response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            # Different response formats for local vs hosted
            if USE_HOSTED_OLLAMA:
                # OpenAI compatible format
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0].get("message", {}).get("content", "No response generated.")
                else:
                    return result.get("response", "No response generated.")
            else:
                # Local Ollama format
                return result.get("response", "I couldn't generate a response. Please try again.")
        else:
            # Handle specific error codes
            if response.status_code == 401:
                return "Authentication error: Invalid API key. Please check your Ollama API key."
            elif response.status_code == 404:
                return f"Model not found: The model '{OLLAMA_MODEL}' is not available. Please check the model name."
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return f"API Error ({response.status_code}). Please check if the service is available."

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        return f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Please check your internet connection and the service URL."
    except requests.exceptions.Timeout:
        logger.error("Ollama API timeout")
        return "Response timeout. The service is taking too long to respond. Please try a simpler query."
    except Exception as e:
        logger.error(f"Ollama API error: {str(e)}")
        return f"Error: {str(e)}. Please check the logs for details."


def format_pricing_plans(text: str) -> str:
    """Format pricing plans to ensure each bullet point is on a new line"""
    # Check if the text contains pricing plan information
    if "Free Plan:" in text and "Pro Plan:" in text and "Enterprise Plan:" in text:
        # Extract the pricing section
        pricing_start = text.find("Free Plan:")
        if pricing_start != -1:
            # Find the end of the pricing section (before the question about connecting with expert)
            pricing_end = text.find("Would you like me to connect with an expert for the Enterprise model?")
            if pricing_end == -1:
                pricing_end = len(text)

            pricing_section = text[pricing_start:pricing_end]

            # Replace the pricing section with properly formatted one
            formatted_pricing = """Free Plan: 
Up to 5 websites 
- Full access to all SEO tools 
- Generate reports 
- No credit card required

Pro Plan:
Up to 50 websites 
- All Free features 
- Priority support 
- API access 
- $49 per month

Enterprise Plan:
Unlimited websites (custom limits) 
- All Pro features 
- Dedicated account manager 
- SLA guarantees 
- Custom integrations 
- Contact sales for a quote"""

            # Replace the pricing section in the original text
            text = text[:pricing_start] + formatted_pricing + "\n" + text[pricing_end:]

    return text


def remove_duplicate_questions(text: str) -> str:
    """Remove duplicate questions to ensure only one question appears at the end"""
    # Check if the response contains the enterprise model question
    if "Would you like me to connect with an expert for the Enterprise model?" in text:
        # Remove "Have I solved your query?" if it appears after the enterprise model question
        enterprise_question_pos = text.find("Would you like me to connect with an expert for the Enterprise model?")
        query_solved_pos = text.find("Have I solved your query?")

        if query_solved_pos > enterprise_question_pos:
            # Remove the "Have I solved your query?" part
            text = text[:query_solved_pos].strip()

    # Check for ticket offer questions and remove "Have I solved your query?" if it appears
    ticket_offer_patterns = [
        r"For more information, Shall I raise a support ticket for you",
        r"Would you like me to open a ticket",
        r"Should I create a ticket",
        r"Do you want me to generate a ticket",
        r"Would you like me to create a support ticket"
    ]

    for pattern in ticket_offer_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            query_solved_pos = text.find("Have I solved your query?")
            if query_solved_pos != -1:
                # Remove the "Have I solved your query?" part
                text = text[:query_solved_pos].strip()
            break

    # Check for phrases indicating the issue is being handled by the team
    team_handling_patterns = [
        r"Our team will",
        r"get back to you",
        r"review your",
        r"working on your",
        r"expert will reach out",
        r"team has been notified",
        r"will contact you"
    ]

    for pattern in team_handling_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            query_solved_pos = text.find("Have I solved your query?")
            if query_solved_pos != -1:
                # Remove the "Have I solved your query?" part
                text = text[:query_solved_pos].strip()
            break

    return text


def fix_ticket_number_formatting(text: str) -> str:
    """Fix ticket number formatting to ensure it appears on one line"""
    # Fix any ticket numbers that might have been split by newlines or spaces
    text = re.sub(r'Ticket Number:\s*NVS\s*([\d\s]+)',
                  lambda m: f'Ticket Number: NVS{m.group(1).replace(" ", "").replace("\n", "")}', text)
    text = re.sub(r'Ticket ID:\s*NVS\s*([\d\s]+)',
                  lambda m: f'Ticket ID: NVS{m.group(1).replace(" ", "").replace("\n", "")}', text)

    # Fix standalone NVS numbers that might be split
    text = re.sub(r'NVS\s+([\d]{5})', r'NVS\1', text)

    # Ensure no line breaks within ticket numbers
    text = re.sub(r'(Ticket (?:Number|ID):\s*)NVS\n([\d]+)', r'\1NVS\2', text)

    return text


def format_ticket_offer_question(text: str) -> str:
    """Format the ticket offer question to appear on a new line"""
    # Replace the ticket offer question with the formatted version
    text = re.sub(r'For more information, Shall I raise a support ticket for you\?',
                  r'\n\nFor more information, Shall I raise a support ticket for you?', text)

    return text


def generate_ticket_number() -> str:
    """Generate a unique ticket number in format NVS#####"""
    return f"NVS{random.randint(10000, 99999)}"


def clean_response(text: str) -> str:
    """Clean and format the response text"""
    # First fix any broken ticket numbers
    text = fix_ticket_number_formatting(text)

    # Format pricing plans if present
    text = format_pricing_plans(text)

    # Remove duplicate questions
    text = remove_duplicate_questions(text)

    # Fix ticket number formatting again after other processing
    text = fix_ticket_number_formatting(text)

    # Format ticket offer question
    text = format_ticket_offer_question(text)

    # Final check: ensure no line breaks in ticket numbers
    text = re.sub(r'(NVS)\s*\n\s*([\d]{5})', r'\1\2', text)
    text = re.sub(r'(NVS)\s+([\d]{5})', r'\1\2', text)

    return text


def fix_common_spacing_issues(text: str) -> str:
    """Fix common spacing and hyphenation issues in text"""

    # Pattern to add space between alphanumeric characters (but not for ticket numbers)
    # First, protect ticket numbers from being modified
    import re
    ticket_pattern = r'(NVS\d+)'
    protected_tickets = {}

    # Find and protect all ticket numbers
    for match in re.finditer(ticket_pattern, text):
        placeholder = f'__TICKET_{len(protected_tickets)}__'
        protected_tickets[placeholder] = match.group()
        text = text.replace(match.group(), placeholder)

    # Now fix spacing between numbers and letters (but not within protected areas)
    # Add space between number and letter (e.g., "50claude" -> "50 claude")
    text = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', text)
    # Add space between letter and number (e.g., "apple4" -> "apple 4")
    text = re.sub(r'([a-zA-Z])(\d+)', r'\1 \2', text)

    # Restore protected ticket numbers
    for placeholder, original in protected_tickets.items():
        text = text.replace(placeholder, original)

    # Common words that are often incorrectly combined
    spacing_fixes = [
        # Time-related
        (r'\b(next)(week|month|year|day|time)\b', r'\1 \2'),
        (r'\b(last)(week|month|year|day|time|night)\b', r'\1 \2'),
        (r'\b(this)(week|month|year|day|time|morning|afternoon|evening)\b', r'\1 \2'),

        # Common phrases
        (r'\b(can)(not)\b', r'\1not'),  # cannot should be one word
        (r'\b(any)(one|body|thing|where|time|way|how)\b', r'\1\2'),  # anyone, anybody, etc.
        (r'\b(some)(one|body|thing|where|time|times|what|how)\b', r'\1\2'),  # someone, somebody, etc.
        (r'\b(every)(one|body|thing|where|time|day)\b', r'\1\2'),  # everyone, everybody, etc.
        (r'\b(no)(one|body|thing|where)\b', r'\1\2'),  # noone -> no one needs special handling

        # Tool-related
        (r'\b(web)(site|page|master|mail)\b', r'\1\2'),
        (r'\b(data)(base|set)\b', r'\1\2'),
        (r'\b(back)(up|end|link|links|ground)\b', r'\1\2'),
        (r'\b(key)(word|words|board)\b', r'\1\2'),
        (r'\b(user)(name|names)\b', r'\1\2'),
        (r'\b(pass)(word|words)\b', r'\1\2'),
        (r'\b(down)(load|loads|time)\b', r'\1\2'),
        (r'\b(up)(load|loads|date|dates|grade|time)\b', r'\1\2'),

        # Business/SEO terms
        (r'\b(on)(line|board|going)\b', r'\1\2'),
        (r'\b(off)(line|board|set)\b', r'\1\2'),
        (r'\b(over)(view|all|load|time)\b', r'\1\2'),
        (r'\b(under)(stand|standing|stood|line|score)\b', r'\1\2'),
        (r'\b(out)(put|come|reach|line|look)\b', r'\1\2'),
        (r'\b(in)(put|come|sight|line|bound)\b', r'\1\2'),

        # Common compound words that need space
        (r'\b(alot)\b', r'a lot'),
        (r'\b(atleast)\b', r'at least'),
        (r'\b(aswell)\b', r'as well'),
        (r'\b(inorder)\b', r'in order'),
        (r'\b(upto)\b', r'up to'),
        (r'\b(setup)\b', r'set up'),  # as verb

        # Fix "Im" -> "I'm"
        (r'\b(Im)\b', r"I'm"),
        (r'\b(Ive)\b', r"I've"),
        (r'\b(Ill)\b', r"I'll"),
        (r'\b(Id)\b', r"I'd"),
        (r'\b(wont)\b', r"won't"),
        (r'\b(cant)\b', r"can't"),
        (r'\b(dont)\b', r"don't"),
        (r'\b(doesnt)\b', r"doesn't"),
        (r'\b(didnt)\b', r"didn't"),
        (r'\b(isnt)\b', r"isn't"),
        (r'\b(arent)\b', r"aren't"),
        (r'\b(wasnt)\b', r"wasn't"),
        (r'\b(werent)\b', r"weren't"),
        (r'\b(hasnt)\b', r"hasn't"),
        (r'\b(havent)\b', r"haven't"),
        (r'\b(hadnt)\b', r"hadn't"),
        (r'\b(wouldnt)\b', r"wouldn't"),
        (r'\b(couldnt)\b', r"couldn't"),
        (r'\b(shouldnt)\b', r"shouldn't"),
        (r'\b(youre)\b', r"you're"),
        (r'\b(youve)\b', r"you've"),
        (r'\b(youll)\b', r"you'll"),
        (r'\b(youd)\b', r"you'd"),
        (r'\b(hes)\b', r"he's"),
        (r'\b(shes)\b', r"she's"),
        (r'\b(its)\b(?! \w+ing)', r"it's"),  # its -> it's (but not before -ing verbs)
        (r'\b(were)\b(?! \w+ing)', r"we're"),  # were -> we're contextually
        (r'\b(theyre)\b', r"they're"),
        (r'\b(theyve)\b', r"they've"),
        (r'\b(theyll)\b', r"they'll"),
        (r'\b(theyd)\b', r"they'd"),
        (r'\b(whats)\b', r"what's"),
        (r'\b(wheres)\b', r"where's"),
        (r'\b(theres)\b', r"there's"),
        (r'\b(thats)\b', r"that's"),

        # Common hyphenated words
        (r'\b(re)(check|restart|send|reset|do|run|build)\b', r'\1-\2'),
        (r'\b(pre)(view|set|defined|configured)\b', r'\1-\2'),
        (r'\b(co)(operate|ordinate|author)\b', r'\1-\2'),
        (r'\b(multi)(purpose|factor|level)\b', r'\1-\2'),
        (r'\b(self)(service|help|hosted)\b', r'\1-\2'),
        (r'\b(real)(time)\b', r'\1-\2'),
        (r'\b(up)(to)(date)\b', r'\1-\2-\3'),
        (r'\b(state)(of)(the)(art)\b', r'\1-\2-\3-\4'),

        # Fix spacing around punctuation
        (r'\s+([.,!?;:])', r'\1'),  # Remove space before punctuation
        (r'([.,!?;:])([A-Za-z])', r'\1 \2'),  # Add space after punctuation

        # Fix multiple spaces
        (r'\s+', r' '),
    ]

    # Apply all fixes
    for pattern, replacement in spacing_fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Special case for "no one" (needs special handling)
    text = re.sub(r'\b(noone)\b', r'no one', text, flags=re.IGNORECASE)

    # Ensure proper capitalization at sentence start
    text = re.sub(r'^([a-z])', lambda m: m.group(1).upper(), text)
    text = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)

    return text


def format_response_text(text: str) -> str:
    """Format the response text to ensure proper bullet points and numbered lists"""
    # Split text into lines for processing
    lines = text.split('\n')
    formatted_lines = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            formatted_lines.append('')
            continue

        # Process numbered lists (e.g., "1. ", "2. ", etc.)
        if re.match(r'^\s*\d+\.\s+', line):
            # This is a numbered list item, ensure it's on its own line
            formatted_lines.append(line)

        # Process bullet points (e.g., "- ", "• ", etc.)
        elif re.match(r'^\s*[-•]\s+', line):
            # This is a bullet point, ensure it's on its own line
            formatted_lines.append(line)

        # Check if line contains numbered list items in the middle
        elif re.search(r'\s\d+\.\s+', line):
            # Split the line at numbered list items
            parts = re.split(r'(\s\d+\.\s+)', line)
            new_line = parts[0]
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    # Add the numbered item on a new line
                    new_line += '\n' + parts[i] + parts[i + 1]
                else:
                    new_line += parts[i]
            formatted_lines.append(new_line)

        # Check if line contains bullet points in the middle
        elif re.search(r'\s[-•]\s+', line):
            # Split the line at bullet points
            parts = re.split(r'(\s[-•]\s+)', line)
            new_line = parts[0]
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    # Add the bullet point on a new line
                    new_line += '\n' + parts[i] + parts[i + 1]
                else:
                    new_line += parts[i]
            formatted_lines.append(new_line)

        # Regular text
        else:
            formatted_lines.append(line)

    # Join the formatted lines
    formatted_text = '\n'.join(formatted_lines)

    # Additional formatting for pricing plans
    if "Free Plan:" in formatted_text and "Pro Plan:" in formatted_text and "Enterprise Plan:" in formatted_text:
        # Extract the pricing section
        pricing_start = formatted_text.find("Free Plan:")
        if pricing_start != -1:
            # Find the end of the pricing section
            pricing_end = formatted_text.find("Would you like me to connect with an expert for the Enterprise model?")
            if pricing_end == -1:
                pricing_end = len(formatted_text)

            pricing_section = formatted_text[pricing_start:pricing_end]

            # Format each pricing plan
            plans = re.split(r'(Free Plan:|Pro Plan:|Enterprise Plan:)', pricing_section)
            formatted_plans = []

            for i in range(1, len(plans), 2):
                if i + 1 < len(plans):
                    plan_name = plans[i]
                    plan_details = plans[i + 1]

                    # Format the plan details with bullet points
                    details = plan_details.split('-')
                    formatted_details = [details[0].strip()]  # First part (e.g., "Up to 5 websites")

                    for detail in details[1:]:
                        if detail.strip():
                            formatted_details.append(f"- {detail.strip()}")

                    formatted_plans.append(f"{plan_name}\n" + '\n'.join(formatted_details))

            # Replace the pricing section in the original text
            formatted_text = formatted_text[:pricing_start] + '\n\n'.join(formatted_plans) + formatted_text[
                                                                                             pricing_end:]

    return formatted_text


def format_response_lists(text: str) -> str:
    """Format numbered lists and bullet points to appear on separate lines with proper spacing"""

    # First handle variations of "follow these steps" or similar phrases
    step_intros = [
        r'(follow these steps?:?)\s*',
        r'(here are the steps?:?)\s*',
        r'(try these steps?:?)\s*',
        r'(please try:?)\s*',
        r'(steps to follow:?)\s*',
        r'(you can:?)\s*',
        r'(to do this:?)\s*',
    ]

    for pattern in step_intros:
        text = re.sub(pattern + r'(\d+\.)', r'\1\n\n\2', text, flags=re.IGNORECASE)

    # Fix numbered lists that appear inline (e.g., "text. 1. item 2. item")
    # Add newline before numbers that follow a period but aren't already on new line
    text = re.sub(r'([.!?])\s+(\d+\.\s+)', r'\1\n\n\2', text)

    # Handle numbered items that are separated by just a space
    # Pattern: "1. something 2. something" -> "1. something\n2. something"
    text = re.sub(r'(\d+\.[^\n.!?]+[.!?]?)\s+(\d+\.\s+)', r'\1\n\n\2', text)

    # Ensure numbered items at start of line
    text = re.sub(r'(?<!\n)(\d+\.\s+[A-Z])', r'\n\1', text)

    # Handle bullet points (-, *, •)
    # Add newline before bullet if not already there
    text = re.sub(r'(?<!\n)\s*([•\-\*])\s+([A-Z])', r'\n\1 \2', text)

    # Handle "Plan details" and plan names
    text = re.sub(r'(Plan details?:?)\s*(?!\n)', r'\n\n\1\n', text, flags=re.IGNORECASE)

    # Format each plan name on new line with proper spacing
    plan_names = ['Free Plan:', 'Pro Plan:', 'Premium Plan:', 'Enterprise Plan:', 'Starter Plan:', 'Basic Plan:']
    for plan in plan_names:
        # Look for plan name and ensure it's on new line with spacing
        text = re.sub(rf'(?<!\n)({plan})', r'\n\n\1', text, flags=re.IGNORECASE)
        # Add newline after plan name if features follow immediately
        text = re.sub(rf'({plan})\s*([A-Z\-•])', r'\1\n\2', text, flags=re.IGNORECASE)

    # Handle Step-by-step instructions
    text = re.sub(r'(?<!\n)(Step\s+\d+[:.])\s*', r'\n\n\1 ', text, flags=re.IGNORECASE)

    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)

    # Clean up excessive newlines but keep proper spacing
    text = re.sub(r'\n{4,}', r'\n\n\n', text)

    # Remove leading/trailing whitespace from each line
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)

    return text.strip()


def format_response_presentable(text: str) -> str:
    """Make the response more presentable with proper formatting"""

    # Ensure questions are on new paragraphs
    questions_patterns = [
        r'(Would you like[^?]+\?)',
        r'(Do you [^?]+\?)',
        r'(Have I [^?]+\?)',
        r'(Should I [^?]+\?)',
        r'(Can I [^?]+\?)',
        r'(Shall I [^?]+\?)',
        r'(For more information[^?]+\?)',
        r'(Is there [^?]+\?)',
        r'(Did this [^?]+\?)',
        r'(Does this [^?]+\?)',
    ]

    for pattern in questions_patterns:
        # Add double newline before question if not already present
        text = re.sub(r'(?<!\n\n)' + pattern, r'\n\n\1', text, flags=re.IGNORECASE)

    # Format specific sections that often appear
    # Ticket information
    text = re.sub(r'(Ticket (?:Number|ID):\s*NVS\d+)', r'\n\1', text)

    # Format error/solution sections
    text = re.sub(r'((?:Error|Solution|Note|Tip|Warning|Important):)\s*', r'\n\n\1\n', text, flags=re.IGNORECASE)

    # Ensure proper paragraph breaks after sentences before certain keywords
    paragraph_triggers = [
        'To ', 'For ', 'Please ', 'You can ', 'Try ', 'Follow ',
        'First ', 'Second ', 'Third ', 'Next ', 'Then ', 'Finally ',
        'Additionally ', 'Also ', 'Furthermore ', 'However ',
    ]

    for trigger in paragraph_triggers:
        text = re.sub(rf'([.!?])\s+({trigger})', r'\1\n\n\2', text)

    # Clean up spacing issues
    text = re.sub(r'\s*\n\s*', r'\n', text)  # Remove spaces around newlines
    text = re.sub(r'\n{3,}', r'\n\n', text)  # Max 2 newlines
    text = re.sub(r'^\n+', '', text)  # Remove leading newlines
    text = re.sub(r'\n+$', '', text)  # Remove trailing newlines

    return text.strip()


def extract_and_save_ticket_from_response(response_text: str, user_query: str) -> None:
    """Extract ticket number from AI response and save it to session state"""
    # Pattern to find ticket numbers in the response
    ticket_patterns = [
        r'Ticket Number:\s*(NVS\d{5})',
        r'Ticket ID:\s*(NVS\d{5})',
        r'ticket\s+(NVS\d{5})',
        r'(NVS\d{5})'
    ]

    for pattern in ticket_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            ticket_id = match.group(1) if '(' in pattern else match.group(0).split(':')[-1].strip()

            # Check if this is a valid ticket format
            if re.match(r'^NVS\d{5}$', ticket_id):
                # Save the ticket to session state
                ticket_data = {
                    'query': user_query,
                    'timestamp': datetime.now(),
                    'ticket_id': ticket_id,
                    'status': 'In Progress',
                    'priority': 'Normal'
                }

                # Add to support tickets if not already present
                if ticket_id not in session_state["support_tickets"]:
                    session_state["support_tickets"][ticket_id] = ticket_data
                    logger.info(f"Saved ticket {ticket_id} to session state")
                break


def get_ai_response(user_input: str, image_data: Optional[str] = None, chat_history: list = None) -> str:
    try:
        # Get FAST MCP instance
        mcp = session_state.get("fast_mcp", FastMCP())

        # Update MCP with user input
        mcp.update_context("user", user_input)

        # Check if we should apply Novarsis filter
        should_filter = mcp.should_filter_novarsis(user_input)

        # Only filter if MCP says we should
        if should_filter and not is_novarsis_related(user_input):
            return """Sorry, I only help with Novarsis SEO Tool.

Please let me know if you have any SEO tool related questions?"""

        # Get context from MCP
        context = mcp.get_context_prompt()

        # Enhanced system prompt based on emotional tone
        enhanced_prompt = SYSTEM_PROMPT
        if mcp.conversation_state["emotional_tone"] == "urgent":
            enhanced_prompt += "\n[User is urgent - provide immediate, actionable solutions]"
        elif mcp.conversation_state["emotional_tone"] == "frustrated":
            enhanced_prompt += "\n[User is frustrated - be extra helpful and empathetic]"

        # Create the full prompt
        if image_data:
            prompt = f"{enhanced_prompt}\n\n{context}\n\nUser query with screenshot: {user_input}"
        else:
            prompt = f"{enhanced_prompt}\n\n{context}\n\nUser query: {user_input}"

        # Call Ollama API
        response_text = call_ollama_api(prompt, image_data)

        # Fix alphanumeric spacing FIRST (before other processing)
        # Protect ticket numbers
        ticket_pattern = r'(NVS\d+)'
        protected_tickets = {}
        for match in re.finditer(ticket_pattern, response_text):
            placeholder = f'__TICKET_{len(protected_tickets)}__'
            protected_tickets[placeholder] = match.group()
            response_text = response_text.replace(match.group(), placeholder)

        # Add spaces between numbers and letters
        response_text = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', response_text)
        response_text = re.sub(r'([a-zA-Z])(\d+)', r'\1 \2', response_text)

        # Restore ticket numbers
        for placeholder, original in protected_tickets.items():
            response_text = response_text.replace(placeholder, original)

        # Enhanced cleaning for grammar and formatting
        # Remove ** symbols
        response_text = response_text.replace("**", "")
        # Remove any repetitive intro lines if present
        response_text = re.sub(r'^(Hey there[!,. ]*I\'?m Nova.*?assistant[.!]?\s*)', '', response_text,
                               flags=re.IGNORECASE).strip()
        # Keep alphanumeric, spaces, common punctuation, newlines, and bullet/section characters
        response_text = re.sub(r'[^a-zA-Z0-9 .,!?:;()\n•-]', '', response_text)

        # Fix common grammar issues
        # Ensure space after period if not followed by a newline
        response_text = re.sub(r'\.([A-Za-z])', r'. \1', response_text)
        # Fix double spaces
        response_text = re.sub(r'\s+', ' ', response_text)
        # Ensure space after comma
        response_text = re.sub(r',([A-Za-z])', r', \1', response_text)
        # Ensure space after question mark and exclamation
        response_text = re.sub(r'([!?])([A-Za-z])', r'\1 \2', response_text)
        # Fix missing spaces between words
        response_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', response_text)

        # --- Formatting improvements for presentability ---
        # Normalize multiple spaces
        response_text = re.sub(r'\s+', ' ', response_text)
        # Ensure proper paragraph separation
        response_text = re.sub(r'([.!?])\s', r'\1\n\n', response_text)

        # Format the response text to ensure proper bullet points and numbered lists
        response_text = format_response_text(response_text)

        # --- End formatting improvements ---

        # Clean the response (format pricing, remove duplicate questions, fix ticket numbers)
        response_text = clean_response(response_text)

        # Fix common spacing and grammar issues
        response_text = fix_common_spacing_issues(response_text)

        # Format numbered lists and bullet points for better presentation
        response_text = format_response_lists(response_text)

        # Make the response more presentable
        response_text = format_response_presentable(response_text)

        # Final ticket number cleanup - ensure no breaks in ticket numbers
        # This is critical to handle any NVS numbers that got split
        response_text = re.sub(r'(Ticket (?:Number|ID):\s*)NVS\s*\n\s*([\d]+)', r'\1NVS\2', response_text)
        response_text = re.sub(r'NVS\s*\n\s*([\d]{5})', r'NVS\1', response_text)
        response_text = re.sub(r'NVS\s+([\d]{5})', r'NVS\1', response_text)

        # Replace example ticket number NVS12345 with a random one if it appears
        if 'NVS12345' in response_text:
            random_ticket = f'NVS{random.randint(10000, 99999)}'
            response_text = response_text.replace('NVS12345', random_ticket)

        # Ensure "Have I solved your query?" is always on a new paragraph
        if "Have I solved your query?" in response_text:
            # Replace any occurrence where it's not after a newline
            response_text = response_text.replace(" Have I solved your query?", "\n\nHave I solved your query?")
            # Also handle if it's at the start of a line but without enough spacing
            response_text = response_text.replace("\nHave I solved your query?", "\n\nHave I solved your query?")
            # Clean up any triple newlines that might have been created
            response_text = re.sub(r'\n{3,}Have I solved your query\?', '\n\nHave I solved your query?', response_text)

        return response_text.strip()
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return "I encountered an issue processing your request. Please try rephrasing your question or connect with our human support team for assistance."


def save_unresolved_query(query_data: Dict) -> str:
    query_data['timestamp'] = datetime.now()
    query_data['ticket_id'] = f"NVS{random.randint(10000, 99999)}"
    query_data['status'] = "In Progress"
    query_data['priority'] = "High" if "urgent" in query_data['query'].lower() else "Normal"
    session_state["unresolved_queries"].append(query_data)
    session_state["support_tickets"][query_data['ticket_id']] = query_data
    return query_data['ticket_id']


# API Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Check if the user is responding to "Have I solved your query?"
    if session_state.get("last_bot_message_ends_with_query_solved"):
        if request.message.lower() in ["no", "nope", "not really", "not yet"]:
            # User says no, so we connect with an expert
            session_state["last_bot_message_ends_with_query_solved"] = False
            return await connect_expert()
        elif request.message.lower() in ["yes", "yeah", "yep", "thank you", "thanks"]:
            # User says yes, we can acknowledge
            session_state["last_bot_message_ends_with_query_solved"] = False
            response = "Great! I'm glad I could help. Feel free to ask if you have any more questions about Novarsis! 🚀"
            bot_message = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(),
                "show_feedback": True
            }
            session_state["chat_history"].append(bot_message)
            return {"response": response, "show_feedback": True}

    # Check if the message is an email
    if re.match(r"[^@]+@[^@]+\.[^@]+", request.message):
        # It's an email, so we acknowledge and continue
        # We don't want to restart the chat, so we just pass it to the AI
        pass  # We'll let the AI handle it as per the system prompt

    # Add user message to chat history
    user_message = {
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now()
    }
    session_state["chat_history"].append(user_message)

    # Store current query for potential escalation
    session_state["current_query"] = {
        "query": request.message,
        "timestamp": datetime.now()
    }

    # Store last user query for "Connect with an Expert"
    session_state["last_user_query"] = request.message

    # Get AI response with chat history for context
    time.sleep(0.5)  # Simulate thinking time

    if session_state["checking_ticket_status"]:
        ticket_id = request.message.strip().upper()

        if ticket_id.startswith("NVS") and len(ticket_id) > 3:
            if ticket_id in session_state["support_tickets"]:
                ticket = session_state["support_tickets"][ticket_id]
                response = f"""🎫 Ticket Details:

Ticket ID: {ticket_id}
Status: {ticket['status']}
Priority: {ticket['priority']}
Created: {ticket['timestamp'].strftime('%Y-%m-%d %H:%M')}
Query: {ticket['query']}

Our team is working on your issue. You'll receive a notification when there's an update."""
            else:
                response = f"❌ Ticket ID '{ticket_id}' not found. Please check the ticket number and try again, or contact support at {SUPPORT_EMAIL}."
        else:
            response = "⚠️ Please enter a valid ticket ID (e.g., NVS12345)."

        session_state["checking_ticket_status"] = False
        show_feedback = True  # Changed to True
    elif is_greeting(request.message):
        # Check if there's more content after the greeting (like a problem)
        message_lower = request.message.lower()
        # Remove greeting words to check if there's additional content
        remaining_message = request.message
        for greeting in GREETING_KEYWORDS:
            if greeting in message_lower:
                # Remove the greeting word (case-insensitive) and common punctuation
                remaining_message = re.sub(rf'\b{greeting}\b[,.]?\s*', '', remaining_message, flags=re.IGNORECASE)
                break

        remaining_message = remaining_message.strip()

        # If there's content after greeting, handle the FULL MESSAGE but with instruction to skip greeting
        if remaining_message and len(remaining_message) > 2:
            # Pass the full message but with special instruction to skip greeting
            enhanced_input = f"[USER HAS GREETED WITH PROBLEM - SKIP GREETING AND DIRECTLY ADDRESS THE ISSUE]\n{request.message}"
            response = get_ai_response(enhanced_input, request.image_data, session_state["chat_history"])
        else:
            # Just greeting
            response = get_intro_response()

        # Extract and save any ticket numbers from the response
        extract_and_save_ticket_from_response(response, request.message)

        session_state["intro_given"] = True
        show_feedback = True  # Changed to True
    else:
        response = get_ai_response(request.message, request.image_data, session_state["chat_history"])
        show_feedback = True  # Already True

        # Extract and save any ticket numbers from the AI response
        extract_and_save_ticket_from_response(response, request.message)

    # Update FAST MCP with bot response
    if "fast_mcp" in session_state:
        session_state["fast_mcp"].update_context("assistant", response)

    # Check if the response ends with "Have I solved your query?"
    if response.strip().endswith("Have I solved your query?"):
        session_state["last_bot_message_ends_with_query_solved"] = True
    else:
        session_state["last_bot_message_ends_with_query_solved"] = False

    # Add bot response to chat history
    bot_message = {
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(),
        "show_feedback": show_feedback
    }
    session_state["chat_history"].append(bot_message)

    # Don't send suggestions with response anymore since we're doing real-time
    return {"response": response, "show_feedback": show_feedback}


@app.post("/api/check-ticket-status")
async def check_ticket_status():
    session_state["checking_ticket_status"] = True
    response = "Please enter your ticket number (e.g., NVS12345):"

    bot_message = {
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(),
        "show_feedback": True  # Changed to True
    }
    session_state["chat_history"].append(bot_message)

    return {"response": response}


@app.post("/api/connect-expert")
async def connect_expert():
    if session_state["last_user_query"]:
        ticket_id = save_unresolved_query({
            "query": session_state["last_user_query"],
            "timestamp": datetime.now()
        })
        response = f"""I've created a priority support ticket for you:

🎫 Ticket ID: {ticket_id}
📱 Status: Escalated to Human Support
⏱️ Response Time: Within 15 minutes

Our expert team has been notified and will reach out to you shortly via:
• In-app chat
• Email to your registered address
• WhatsApp: {WHATSAPP_NUMBER}

You can check your ticket status anytime by typing 'ticket {ticket_id}'"""
    else:
        response = "I'd be happy to connect you with an expert. Please first send your query so I can create a support ticket for you."

    bot_message = {
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(),
        "show_feedback": True  # Changed to True
    }
    session_state["chat_history"].append(bot_message)

    return {"response": response}


@app.post("/api/feedback")
async def feedback(request: FeedbackRequest):
    if request.feedback == "no":
        ticket_id = save_unresolved_query(session_state["current_query"])
        response = f"""I understand this didn't fully resolve your issue. I've created a priority support ticket for you:

🎫 Ticket ID: {ticket_id}
📱 Status: Escalated to Human Support
⏱️ Response Time: Within 15 minutes

Our expert team has been notified and will reach out to you shortly via:
• In-app chat
• Email to your registered address
• WhatsApp: {WHATSAPP_NUMBER}

You can check your ticket status anytime by typing 'ticket {ticket_id}'"""
        session_state["resolved_count"] -= 1
    else:
        response = "Great! I'm glad I could help. Feel free to ask if you have any more questions about Novarsis! 🚀"
        session_state["resolved_count"] += 1

    bot_message = {
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(),
        "show_feedback": True  # Changed to True
    }
    session_state["chat_history"].append(bot_message)

    return {"response": response}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG files are allowed")

    # Read file and convert to base64
    contents = await file.read()
    base64_image = base64.b64encode(contents).decode('utf-8')

    return {"image_data": base64_image, "filename": file.filename}


@app.get("/api/chat-history")
async def get_chat_history():
    return {"chat_history": session_state["chat_history"]}


@app.get("/api/suggestions")
async def get_suggestions():
    """Get initial suggestions when the chat loads."""
    return {"suggestions": QUICK_REPLY_SUGGESTIONS["initial"]}


@app.post("/api/typing-suggestions")
async def get_typing_suggestions(request: dict):
    """Get real-time suggestions based on what user is typing."""
    user_input = request.get("input", "")
    suggestions = get_context_suggestions(user_input)
    return {"suggestions": suggestions}


# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Create index.html template
with open("templates/index.html", "w") as f:
    f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Novarsis Support Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            font-family: 'Inter', sans-serif !important;
        }

        body {
            background: #f0f2f5;
            margin: 0;
            padding: 0;
        }

        .main-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }

        .header-container {
            background: white;
            border-radius: 16px;
            padding: 16px 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-right: 10px;
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            background: #e8f5e9;
            border-radius: 20px;
            font-size: 13px;
            color: #2e7d32;
            font-weight: 500;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: #4caf50;
            border-radius: 50%;
            margin-right: 6px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .chat-container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            height: 70vh;
            min-height: 500px;
            overflow-y: auto;
            padding: 20px;
            margin-bottom: 20px;
            position: relative;
        }

        .message-wrapper {
            display: flex;
            margin-bottom: 20px;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .user-message-wrapper {
            justify-content: flex-end;
        }

        .bot-message-wrapper {
            justify-content: flex-start;
        }

        .message-content {
            max-width: 70%;
            min-width: min-content;
            width: fit-content;
            padding: 16px 20px;
            border-radius: 18px;
            font-size: 15px;
            line-height: 1.6;
            position: relative;
            word-wrap: break-word;
            white-space: pre-wrap;
        }

        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 5px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }

        .bot-message {
            background: #f1f3f5;
            color: #2d3436;
            border-bottom-left-radius: 5px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin: 0 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 16px;
            flex-shrink: 0;
        }

        .user-avatar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .bot-avatar {
            background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
            color: white;
        }

        .timestamp {
            font-size: 11px;
            color: rgba(0,0,0,0.5);
            margin-top: 8px;
            font-weight: 400;
        }

        .user-timestamp {
            color: rgba(255,255,255,0.8);
            text-align: right;
        }

        .typing-indicator {
            display: flex;
            align-items: center;
            padding: 15px;
            background: #f1f3f5;
            border-radius: 18px;
            width: fit-content;
            margin-left: 64px;
            margin-bottom: 20px;
        }

        .typing-dot {
            width: 8px;
            height: 8px;
            background: #95a5a6;
            border-radius: 50%;
            margin: 0 3px;
            animation: typing 1.4s infinite;
        }

        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }

        .input-container {
            background: white;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            position: sticky;
            bottom: 20px;
        }

        .suggestions-container {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
            max-height: 80px;
            overflow-y: auto;
            padding: 4px 0;
            transition: opacity 0.15s ease;
            min-height: 32px;
        }

        .suggestion-pill {
            padding: 8px 14px;
            background: #f0f2f5;
            border: 1px solid #e1e4e8;
            border-radius: 20px;
            font-size: 13px;
            color: #24292e;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
            flex-shrink: 0;
            font-weight: 500;
            animation: slideInFade 0.3s ease-out forwards;
            opacity: 0;
        }

        @keyframes slideInFade {
            from {
                opacity: 0;
                transform: translateY(-5px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .suggestion-pill:hover {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(102, 126, 234, 0.2);
        }

        .suggestion-pill:active {
            transform: translateY(0);
        }

        .suggestions-container::-webkit-scrollbar {
            height: 4px;
        }

        .suggestions-container::-webkit-scrollbar-track {
            background: transparent;
        }

        .suggestions-container::-webkit-scrollbar-thumb {
            background: #d0d0d0;
            border-radius: 2px;
        }

        .message-form {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .message-input {
            flex: 1;
            border-radius: 24px;
            border: 1px solid #e0e0e0;
            padding: 14px 20px;
            font-size: 15px;
            background: #f8f9fa;
            color: #333333;
            outline: none;
        }

        .message-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
        }

        .send-btn {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        .send-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        .attachment-btn {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: #f8f9fa;
            border: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
            color: #54656f;
            padding: 0;
        }

        .attachment-btn:hover {
            background-color: #f1f3f5;
            border-color: #667eea;
            transform: scale(1.05);
        }

        .attachment-btn.success {
            background-color: #e8f5e9;
            color: #4caf50;
            border-color: #4caf50;
            pointer-events: none;
        }

        .attachment-btn.success svg path {
            fill: #4caf50;
        }

        .feedback-container {
            display: flex;
            gap: 10px;
            margin-top: 10px;
            margin-left: 64px;
        }

        .feedback-btn {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            border: 1px solid #e0e0e0;
            background: white;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .feedback-btn:hover {
            background: #f8f9fa;
            border-color: #667eea;
        }

        .file-input {
            display: none;
        }

        /* Initial message styling - Ultra Compact */
        .initial-message .message-content {
            padding: 8px 12px !important;
            line-height: 1.2 !important;
            max-width: max-content !important;
            min-width: unset !important;
            width: max-content !important;
            display: inline-block !important;
            font-size: 14px !important;
        }

        .initial-message.bot-message-wrapper {
            display: flex;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .initial-message .avatar {
            width: 32px;
            height: 32px;
            font-size: 13px;
            margin-right: 8px;
            flex-shrink: 0;
        }

        .initial-message .timestamp {
            font-size: 10px;
            color: rgba(0,0,0,0.4);
            margin-top: 3px;
            display: block;
        }

        /* Force initial bot message to be compact */
        .initial-message .bot-message {
            max-width: max-content !important;
            width: max-content !important;
            display: inline-block !important;
            white-space: nowrap !important;
        }

        /* Allow timestamp to wrap normally */
        .initial-message .bot-message .timestamp {
            white-space: normal !important;
        }

        /* Scrollbar Styling */
        ::-webkit-scrollbar {
            width: 6px;
        }

        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .main-container {
                padding: 10px;
            }

            .chat-container {
                height: 65vh;
                border-radius: 12px;
                padding: 15px;
            }

            .message-content {
                max-width: 80%;
                font-size: 14px;
            }

            .input-container {
                padding: 12px;
                border-radius: 12px;
            }

            .header-container {
                padding: 12px 16px;
                border-radius: 12px;
            }

            .avatar {
                width: 36px;
                height: 36px;
                font-size: 14px;
            }

            .typing-indicator {
                margin-left: 52px;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="header-container">
            <div class="logo-section">
                <span class="logo">🚀 NOVARSIS</span>
                <span style="color: #95a5a6; font-size: 14px;">AI Support Center</span>
            </div>
            <div class="status-indicator">
                <div class="status-dot"></div>
                <span>Nova is Online</span>
            </div>
        </div>

        <div class="chat-container" id="chat-container">
            <!-- Initial greeting message -->
            <div class="message-wrapper bot-message-wrapper initial-message">
                <div class="avatar bot-avatar">N</div>
                <div class="message-content bot-message">
                    Hi, I am Nova, How may I assist you today?
                    <div class="timestamp bot-timestamp">Now</div>
                </div>
            </div>
        </div>

        <div class="input-container">
            <div class="suggestions-container" id="suggestions-container">
                <!-- Quick reply suggestions will be dynamically added here -->
            </div>

            <form class="message-form" id="message-form">
                <input type="file" id="file-input" class="file-input" accept="image/jpeg,image/jpg,image/png">
                <button type="button" class="attachment-btn" id="attachment-btn">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1 -1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z" fill="currentColor"/>
                    </svg>
                </button>
                <input type="text" class="message-input" id="message-input" placeholder="Type your message...">
                <button type="submit" class="send-btn">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="white"/>
                    </svg>
                </button>
            </form>
        </div>
    </div>

    <script>
        // Format time function
        function formatTime(timestamp) {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        }

        // Current time for welcome message
        document.addEventListener('DOMContentLoaded', function() {
            // Set current time for initial greeting
            const initialTimestamp = document.querySelector('.initial-message .timestamp');
            if (initialTimestamp) {
                initialTimestamp.textContent = formatTime(new Date());
            }

            // Load initial suggestions
            loadInitialSuggestions();
        });

        // Chat container
        const chatContainer = document.getElementById('chat-container');

        // Message input
        const messageForm = document.getElementById('message-form');
        const messageInput = document.getElementById('message-input');
        const attachmentBtn = document.getElementById('attachment-btn');
        const fileInput = document.getElementById('file-input');

        // File handling
        let uploadedImageData = null;
        let uploadedFileName = '';

        attachmentBtn.addEventListener('click', function() {
            fileInput.click();
        });

        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    uploadedImageData = event.target.result.split(',')[1]; // Get base64 data
                    uploadedFileName = file.name;
                    attachmentBtn.classList.add('success');
                    // Change icon to checkmark
                    attachmentBtn.innerHTML = `
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" fill="currentColor"/>
                        </svg>
                    `;
                };
                reader.readAsDataURL(file);
            }
        });

        // Add message to chat
        function addMessage(role, content, showFeedback = true) {
            const messageWrapper = document.createElement('div');
            messageWrapper.className = `message-wrapper ${role}-message-wrapper`;

            const avatar = document.createElement('div');
            avatar.className = `avatar ${role}-avatar`;
            avatar.textContent = role === 'user' ? '@' : 'N';

            const messageContent = document.createElement('div');
            messageContent.className = `message-content ${role}-message`;
            // Set textContent to preserve formatting
            messageContent.textContent = content;

            const timestamp = document.createElement('div');
            timestamp.className = `timestamp ${role}-timestamp`;
            timestamp.textContent = formatTime(new Date());

            messageContent.appendChild(timestamp);

            if (role === 'user') {
                messageWrapper.appendChild(messageContent);
                messageWrapper.appendChild(avatar);
            } else {
                messageWrapper.appendChild(avatar);
                messageWrapper.appendChild(messageContent);
                // Feedback buttons removed: assistant messages now only show avatar and content.
            }

            chatContainer.appendChild(messageWrapper);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        // Show typing indicator
        function showTypingIndicator() {
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            typingIndicator.innerHTML = `
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            `;
            chatContainer.appendChild(typingIndicator);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return typingIndicator;
        }

        // Update suggestions with smooth animation
        function updateSuggestions(suggestions) {
            const container = document.getElementById('suggestions-container');

            // Smooth transition
            container.style.opacity = '0';

            setTimeout(() => {
                container.innerHTML = '';

                if (suggestions && suggestions.length > 0) {
                    suggestions.forEach((suggestion, index) => {
                        const pill = document.createElement('div');
                        pill.className = 'suggestion-pill';
                        pill.textContent = suggestion;
                        pill.style.animationDelay = `${index * 50}ms`;
                        pill.onclick = () => {
                            messageInput.value = suggestion;
                            messageForm.dispatchEvent(new Event('submit'));
                        };
                        container.appendChild(pill);
                    });
                }

                container.style.opacity = '1';
            }, 150);
        }

        // Load initial suggestions
        async function loadInitialSuggestions() {
            try {
                const response = await fetch('/api/suggestions');
                const data = await response.json();
                updateSuggestions(data.suggestions);
            } catch (error) {
                console.error('Error loading suggestions:', error);
            }
        }

        // Real-time typing suggestions with debouncing
        let typingTimer;
        const doneTypingInterval = 300; // ms

        async function fetchTypingSuggestions(input) {
            if (input.trim().length < 2) {
                // Show initial suggestions if input is empty or very short
                if (input.trim().length === 0) {
                    loadInitialSuggestions();
                } else {
                    updateSuggestions([]);
                }
                return;
            }

            try {
                const response = await fetch('/api/typing-suggestions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ input: input })
                });

                const data = await response.json();
                updateSuggestions(data.suggestions);
            } catch (error) {
                console.error('Error fetching suggestions:', error);
            }
        }

        // Handle input changes for real-time suggestions
        messageInput.addEventListener('input', function(e) {
            clearTimeout(typingTimer);
            const inputValue = e.target.value;

            // Debounce the API call
            typingTimer = setTimeout(() => {
                fetchTypingSuggestions(inputValue);
            }, doneTypingInterval);
        });

        // Handle focus to show suggestions
        messageInput.addEventListener('focus', function(e) {
            if (e.target.value.trim().length === 0) {
                loadInitialSuggestions();
            } else {
                fetchTypingSuggestions(e.target.value);
            }
        });

        // Send message
        async function sendMessage(message, imageData = null) {
            // Handle special commands
            if (message.toLowerCase() === 'check ticket status') {
                // Clear suggestions
                updateSuggestions([]);

                // Call the check ticket status API
                try {
                    const response = await fetch('/api/check-ticket-status', {
                        method: 'POST'
                    });
                    const data = await response.json();
                    addMessage('assistant', data.response, true);
                } catch (error) {
                    console.error('Error checking ticket status:', error);
                    addMessage('assistant', 'Sorry, I encountered an error checking ticket status.', true);
                }

                // Load initial suggestions after a delay
                setTimeout(() => {
                    loadInitialSuggestions();
                }, 500);
                return;
            }

            if (message.toLowerCase() === 'connect with an expert') {
                // Clear suggestions
                updateSuggestions([]);

                // Call the connect expert API
                try {
                    const response = await fetch('/api/connect-expert', {
                        method: 'POST'
                    });
                    const data = await response.json();
                    addMessage('assistant', data.response, true);
                } catch (error) {
                    console.error('Error connecting with expert:', error);
                    addMessage('assistant', 'Sorry, I encountered an error connecting you with an expert.', true);
                }

                // Load initial suggestions after a delay
                setTimeout(() => {
                    loadInitialSuggestions();
                }, 500);
                return;
            }

            // Normal message handling
            // Add user message
            addMessage('user', message);

            // Clear suggestions after sending
            updateSuggestions([]);

            // Show typing indicator
            const typingIndicator = showTypingIndicator();

            try {
                // Send to API
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        image_data: imageData
                    })
                });

                const data = await response.json();

                // Remove typing indicator
                typingIndicator.remove();

                // Add bot response
                addMessage('assistant', data.response, data.show_feedback);

                // Load initial suggestions after response
                setTimeout(() => {
                    loadInitialSuggestions();
                }, 500);

                // Reset attachment
                if (uploadedImageData) {
                    attachmentBtn.classList.remove('success');
                    attachmentBtn.innerHTML = `
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1 -1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z" fill="currentColor"/>
                        </svg>
                    `;
                    uploadedImageData = null;
                    uploadedFileName = '';
                    fileInput.value = '';
                }

            } catch (error) {
                console.error('Error sending message:', error);
                typingIndicator.remove();
                addMessage('assistant', 'Sorry, I encountered an error. Please try again.', true);
                // Show initial suggestions even on error
                setTimeout(() => {
                    loadInitialSuggestions();
                }, 500);
            }
        }

        // Send feedback
        async function sendFeedback(feedback) {
            const messageIndex = document.querySelectorAll('.message-wrapper').length - 1;

            try {
                const response = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        feedback: feedback,
                        message_index: messageIndex
                    })
                });

                const data = await response.json();
                addMessage('assistant', data.response, true);

            } catch (error) {
                console.error('Error sending feedback:', error);
            }
        }

        // Handle form submission
        messageForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const message = messageInput.value.trim();
            if (message) {
                await sendMessage(message, uploadedImageData);
                messageInput.value = '';
            }
        });

        // Handle Enter key in message input
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                messageForm.dispatchEvent(new Event('submit'));
            }
        });
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
