# core/llm.py
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are LADO, a Local Autonomous Digital Operator running on the user's Windows PC.
You have just completed a full file system scan.
You help users understand what is happening on their computer.
You explain file management decisions in plain, friendly English.
Keep responses concise — 2 to 4 sentences maximum and 2 words minimum.
Never suggest deleting files directly. Always recommend user approval.
When the user agrees or says yes, actually move forward and give them 
specific actionable information — don't ask the same question again."""

# This holds the full conversation across multiple questions
conversation_history = []

def ask_llm(user_message):
    global conversation_history

    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}
            ] + conversation_history,   # full history every time
            temperature=0.4,
            max_tokens=300,
        )

        reply = response.choices[0].message.content.strip()

        # Add LADO's reply to history too
        conversation_history.append({
            "role": "assistant",
            "content": reply
        })

        return reply

    except Exception as e:
        return f"LLM unavailable: {e}"

def reset_conversation():
    global conversation_history
    conversation_history = []


def explain_suggestion(suggestion):
    prompt = f"""A file management suggestion was generated:

File:       {suggestion['file']}
Action:     {suggestion['action']}
Reason:     {suggestion['reason']}
Confidence: {suggestion['confidence']}
Risk:       {suggestion['risk']}

Explain this to the user in plain English. Why should they care? 
What will happen if they approve it?"""
    return ask_llm(prompt)


def explain_duplicate_cluster(files):
    file_list = "\n".join([f"  - {f['path']}" for f in files[:5]])
    prompt = f"""LADO found {len(files)} identical copies of a file:

{file_list}

Explain what this means, which copy to keep, and how much space 
could be freed. Each copy is {round(files[0]['size_bytes'] / (1024*1024), 2)} MB."""
    return ask_llm(prompt)


def summarize_scan(summary):
    prompt = f"""You just completed a full system scan. Results:

Total files indexed:     {summary['total_files']:,}
Total size on disk:      {summary['total_size_mb']:,} MB  
Files hashed:            {summary['hashed_files']:,}
Pending suggestions:     {summary['pending_suggestions']:,}

Give the user a friendly 3 sentence summary of what you found 
and what they should do next. Be specific."""
    return ask_llm(prompt)


def answer_user_question(question, recent_logs):
    prompt = f"""The user asked: "{question}"

Recent LADO activity logs:
{recent_logs}

Answer specifically based on the logs. Don't ask if they want 
to proceed — just give them the information."""
    return ask_llm(prompt)