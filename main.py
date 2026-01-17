import os
import base64
from datetime import datetime, timedelta
from openai import OpenAI
from exa_py import Exa
from dotenv import load_dotenv
import resend
import markdown
from markdown_pdf import MarkdownPdf, Section

load_dotenv()

# COnfigs
EXA_API_KEY = os.getenv("EXA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

SENDER_EMAIL = "onboarding@resend.dev"
RECIPIENT_EMAIL = "samemerald8@gmail.com"


exa = Exa(api_key=EXA_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY, max_retries=3)
resend.api_key = RESEND_API_KEY

def fetch_tech_intelligence():
    """Step 1: Use Exa's Neural Search to find high-signal content."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    queries = [
        "Major startup funding announcements, tech exits, policy updates, or ecosystem news in Africa from the last Week",
        "Latest technical breakthroughs in AI and LLM frameworks published in the past day; Focus on: new libraries, models, tools, agentic workflows, memory management in LLMs, and local compute/latency constraints",
        "New tech policy updates or ecosystem news from acroos Africa. And The most insightful post-mortem or 'lessons learned' essay or article published today by or about an African tech founder or investor"
    ]
    
    all_contents = ""
    
    for query in queries:
        # Search and get the full text content of the top results
        search_response = exa.search_and_contents(
            query,
            num_results=5,
            start_published_date=yesterday,
            type='auto',
            text={"max_characters": 2000} # Get enough text for the LLM to summarize
        )
        
        for result in search_response.results:
            all_contents += f"\nSource: {result.url}\nContent: {result.text}\n---\n"
          
    print(all_contents)        
    return all_contents

def compile_newsletter(raw_data):
    """Step 2: Use the Editor LLM to synthesize the data into your format."""
    
    system_prompt = """
    You are the 'MEST AI Insider', a specialized intelligence analyst for a founder in the MEST Africa incubator. 
    Your goal is to distill raw web data into a high-signal, actionable briefing.

    ### ANALYTICAL PRIORITIES (The Filter):
    1.  **Direct Relevance (The 'MEST' Lens):** Prioritize anything mentioning Ghana, Nigeria, Africa, or MEST alumni. If a startup raised money, mention the sector and why it matters for the West African market.
    2.  **AI Focus:** When reporting on AI, ignore 'AI is changing the world' hype. Focus on: new libraries, models, tools, agentic workflows, memory management in LLMs, and local compute/latency constraints.
    3.  **Founder Psychology:** Highlight 'why' things happened (e.g., 'They pivoted because of currency volatility') rather than just 'what' happened.

    ### TONE & STYLE:
    - **Concise & Punchy:** Use bolding for company names and technical terms.
    - **No Fluff:** If a piece of news isn't significant, leave it out. 
    - **Intellectual Honesty:** If two sources conflict, note the discrepancy.

    ### STRUCTURE:
    # 📰 Daily Tech Intelligence Briefing - [Date]
    
    ## 🚀 HEADLINES (5 sentences max)
    Summarize the absolute "must-know" vibe of the day.

    ## 🇬🇭 ACCRA, LAGOS & MEST SCOOP
    Focus on local ecosystem shifts, local events, or regional policy (e.g., BoG regulations).

    ## 🌍 THE AFRICAN BIG DEAL
    Funding rounds, M&A activity, or major expansions. Focus on the 'Why now?'.

    ## 🤖 THE AI EDGE (Technical Deep Dive)
    Explain one technical AI development as if explaining it to a CTO. How can we use this in our MEST projects?

    ## 🧠 FOUNDER WISDOM
    One nugget of advice, a quote, or a link to a founder's thread/essay.

    ### FORMATTING RULES:
    - Use Markdown headers.
    - Every claim MUST have a [Source Link] immediately following it.
    - Keep total length under 800 words for maximum scannability.
    """

    user_prompt = f"Synthesize the following raw intelligence into the newsletter format:\n\n{raw_data}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3 # Low temperature for factual accuracy
    )
    
    return response.choices[0].message.content

def create_pdf(md_content, filename):
    """Generates a styled PDF from Markdown content."""
    pdf = MarkdownPdf(toc_level=2)
    # Adding CSS for better PDF readability
    custom_css = "body { font-family: sans-serif; } h1 { color: #1a73e8; } h2 { color: #d93025; }"
    pdf.add_section(Section(md_content, toc=False), user_css=custom_css)
    pdf.save(filename)
    return filename

def send_email_with_attachment(md_content, pdf_path):
    """Step 3: Send HTML email with the PDF as a Base64 attachment."""
    html_body = markdown.markdown(md_content)
    
    # Read and encode the PDF for Resend
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
        base64_pdf = base64.b64encode(pdf_data).decode()

    params = {
        "from": f"MEST AI Agent <{SENDER_EMAIL}>",
        "to": [RECIPIENT_EMAIL],
        "subject": f"Daily Tech Digest - {datetime.now().strftime('%d %b')}",
        "html": f"<div style='font-family:sans-serif;'>{html_body}</div>",
        "attachments": [
            {
                "filename": os.path.basename(pdf_path),
                "content": base64_pdf,
            }
        ],
    }

    try:
        resend.Emails.send(params)
        print(f"✅ Email and PDF sent successfully to {RECIPIENT_EMAIL}!")
    except Exception as e:
        print(f"❌ Failed to send: {e}")

def main():
    date_str = datetime.now().strftime("%Y%m%d")
    pdf_filename = f"MEST_Digest_{date_str}.pdf"

    print("🛰️ Gathering intelligence...")
    raw_intel = fetch_tech_intelligence()
    
    print("🧠 Synthesizing newsletter...")
    newsletter = compile_newsletter(raw_intel)
    
    print("📄 Creating PDF...")
    create_pdf(newsletter, pdf_filename)
    
    print("📧 Sending email with attachment...")
    send_email_with_attachment(newsletter, pdf_filename)

if __name__ == "__main__":
    main()
