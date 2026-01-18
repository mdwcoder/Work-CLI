import google.generativeai as genai
from openai import OpenAI
import datetime

class AIHandler:
    def __init__(self, provider: str, api_key: str):
        self.provider = provider.upper()
        self.api_key = api_key
        
        if self.provider == "GEMINI":
            genai.configure(api_key=self.api_key)
        elif self.provider == "OPENAI":
            self.client = OpenAI(api_key=self.api_key)
            
    def format_context(self, events: list) -> str:
        """
        Converts DB event rows into a readable context string.
        Events is expected to be a list of sqlite3.Row or dicts with 'timestamp', 'event_type', 'description'.
        """
        if not events:
            return "No work history found."
            
        lines = ["Work History Log:"]
        
        for ev in events:
            ts = ev['timestamp']
            etype = ev['event_type']
            # Safely get description if it exists (it might not in old rows or if column missing)
            desc = ""
            if 'description' in ev.keys() and ev['description']:
                desc = f" ({ev['description']})"
                
            lines.append(f"- {ts}: {etype}{desc}")
            
        return "\n".join(lines)

    def ask_ai(self, user_query: str, context_str: str) -> str:
        """
        Sends the query + context to the selected provider.
        """
        prompt = f"""
        You are a helpful Work Time tracking assistant.
        Analyze the following work history log and answer the user's question.
        
        CONTEXT DATA:
        {context_str}
        
        USER QUESTION:
        {user_query}
        
        Keep the answer concise and helpful. Valid formats in history are ISO 8601.
        """
        
        try:
            if self.provider == "GEMINI":
                return self._ask_gemini(prompt)
            elif self.provider == "OPENAI":
                return self._ask_openai(prompt)
            else:
                return "Error: Unknown AI Provider."
        except Exception as e:
            return f"AI Error: {str(e)}"

    def _ask_gemini(self, prompt: str) -> str:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text

    def _ask_openai(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-3.5-turbo",
        )
        return response.choices[0].message.content
