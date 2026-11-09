import os
import re
import json
import fastapi
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

my_api_key = os.getenv("GROQ_API_KEY")

if not my_api_key:
    raise ValueError("Api Error, There's no api key")

client = Groq(api_key=my_api_key)

model = "qwen/qwen3.8-27b"
app = fastapi.FastAPI()

class UserRequest(BaseModel):
    message: str

PAYPAL_POLICY_KNOWLEDGE_BASE = {
    "Holds": (
        "PayPal may place a temporary hold on your funds for up to 21 days to ensure a secure transaction. "
        "Holds are common for new sellers, international cross-border sales, or sudden spikes in transaction volume. "
        "Funds can be released earlier (usually within 3-7 days) if you upload valid carrier tracking information "
        "and the buyer confirms receipt of the item."
    ),
    "Disputes": (
        "Buyers can file a dispute in the Resolution Center within 180 days of the transaction date. "
        "Disputes can be opened for 'Item Not Received' (INR) or 'Significantly Not as Described' (SNAD). "
        "Once a dispute is filed, the buyer and seller have 20 days to communicate and resolve it. "
        "If unresolved, either party can escalate the dispute to a formal claim for PayPal to investigate."
    ),
    "Fees": (
        "Standard domestic merchant processing fees are 2.99% + $0.49 per transaction. "
        "For international cross-border payments, an additional percentage-based fee of 1.50% applies, "
        "along with a fixed fee based on the currency received. Currency conversion incurs a 3.0% spread "
        "above the wholesale exchange rate."
    ),
    "Access": (
        "If your account is locked due to multiple invalid login attempts, password resets can be requested via "
        "verified email or SMS OTP. Card linking errors usually occur if the billing address matches incorrectly "
        "with your bank records or if the card is already linked to another active PayPal profile."
    )
}

with open(os.path.join(os.path.dirname(__file__), "faq.json"), encoding="utf-8") as f:
    FAQS = json.load(f)


def get_words(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w.rstrip("s") for w in words if len(w) > 3}


def find_faqs(query, top_k=5):
    query_words = get_words(query)
    scored = []
    for faq in FAQS:
        score = len(query_words & get_words(faq["question"])) * 2
        score += len(query_words & get_words(faq["answer"]))
        if score >= 2:
            scored.append((score, faq))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [faq for score, faq in scored[:top_k]]


@app.get("/")
def home():
    return {"status": "PayPal Flux AI agent is Active"}

@app.post("/api/chat/stream")
def stream_chat_agent(payload: UserRequest):

    kb_text = "\n\n".join(
        f"## {topic}\n{text}" for topic, text in PAYPAL_POLICY_KNOWLEDGE_BASE.items()
    )

    matches = find_faqs(payload.message)
    faq_text = "\n\n".join(
        f"Q: {faq['question']}\nA: {faq['answer']}" for faq in matches
    ) or "No matching FAQ found."

    system_prompt = f"""
    You are an advanced, strictly professional Flux AI Agent for PayPal Customer Support.
    Read the user's open-ended query and determine if it falls within your acceptable PayPal support documentation context.

    KNOWLEDGE BASE (your only source of facts):
    {kb_text}

    MOST RELEVANT FAQ ENTRIES FOR THIS QUESTION (also a source of facts, prefer these when they match):
    {faq_text}

    ALLOWED CONTEXT TOPICS:
    - Payout holds, frozen funds, release timelines.
    - Transaction disputes, chargebacks, refund status.
    - Merchant fees, currency conversion rates, international charges.
    - Basic account access issues (password reset, card linking errors).
    - Account limitations, fraud/security, subscriptions, India KYC, wallet and transfers, developer/API and sandbox questions.

    For example: Where is my payment, how much time will it need to be done?
    Say: International payout holds typically take up to 21 days to clear unless shipping tracking information is verified in your activity log.

    CRITICAL INSTRUCTIONS:
    1. If the query is within the ALLOWED CONTEXT, ANSWER IT YOURSELF using the KNOWLEDGE BASE and the FAQ ENTRIES. Start with [REPLY] followed by a concise answer (2-4 sentences). Vague questions such as "where is my payment?" still count as ALLOWED CONTEXT: answer with the relevant policy and suggest a next step.
    2. Use [TRANSFER] ONLY if the query is unrelated to PayPal support (chitchat/out of scope), needs an account-specific action you cannot perform, or neither the KNOWLEDGE BASE nor the FAQ ENTRIES have anything relevant. When in doubt and the topic is even loosely covered, use [REPLY].
    3. Never invent policies, numbers, or timelines that are not in the KNOWLEDGE BASE or FAQ ENTRIES.
    4. After your main text response, you MUST append a triple pipe separator (|||) followed by a concise 3-field Summary Matrix for the human team: Intent, Key Details, Sentiment.

    EXACT OUTPUT FORMAT EXAMPLES:
    Example 1 (Factual Reply):
    [REPLY] International payout holds typically take up to 21 days to clear unless shipping tracking information is verified in your activity log.|||Intent: Payout hold timeline query; Details: None; Sentiment: Neutral

    Example 2 (Fee Question):
    [REPLY] Domestic fees are 2.99% + $0.49 per transaction. International payments add 1.50% plus a fixed currency-based fee, and currency conversion has a 3.0% spread.|||Intent: Fee inquiry; Details: International sales; Sentiment: Neutral

    Example 3 (Transfer Case):
    [TRANSFER] I don't have enough information to answer that.
    """

    def event_generator():
        try:
            # Call Groq with stream=True
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": payload.message}
                ],
                temperature=0.0, # To  block hallucinations
                stream=True
            )

            # Yield chunks
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"[TRANSFER] Connecting you to live support due to a system blip.|||Intent: System Error; Details: {str(e)}; Sentiment: Urgent"


    return StreamingResponse(event_generator(), media_type="text/event-stream")