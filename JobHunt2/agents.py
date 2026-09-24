import os
from google import genai
from google.genai import types

class Agent:
    def __init__(self, role_name, system_instruction):
        self.role_name = role_name
        self.system_instruction = system_instruction
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # Using gemini-3.6-flash as the default for reasoning tasks
        self.model = 'gemini-3.6-flash'

    def run(self, prompt):
        """Executes the agent with the given prompt."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.2 # Lower temperature for analytical tasks
                )
            )
            return response.text
        except Exception as e:
            print(f"[{self.role_name}] Error: {e}")
            return f"Error executing {self.role_name}"

class JobFilter(Agent):
    def __init__(self):
        super().__init__(
            role_name="Job Filter",
            system_instruction=(
                "You are the Job Filter Bot. Your permanent job is to evaluate every vacancy "
                "against the provided CV and job criteria.\n"
                "CRITICAL RULE 1: If the job Location is NOT in India (e.g., USA, UK) and is not explicitly marked as 'Remote India', you MUST classify it as REJECT.\n"
                "CRITICAL RULE 2: Examine required skills and calculate a 'Match Score' from 0 to 100 based on how well the CV skills overlap with the job requirements.\n"
                "Classify opportunities as HIGH MATCH, POSSIBLE MATCH, or REJECT.\n"
                "Format your response EXACTLY as follows:\n"
                "CLASSIFICATION: [HIGH MATCH | POSSIBLE MATCH | REJECT]\n"
                "SCORE: [0-100]\n"
                "REASONING: [Explain the evidence]"
            )
        )
    
    def evaluate(self, job_data, cv_text, preferences):
        prompt = f"""
        **Job Vacancy Details:**
        {job_data}

        **Master CV:**
        {cv_text}

        **Preferences:**
        {preferences}

        Evaluate the match.
        """
        return self.run(prompt)

class CompanyInvestigator(Agent):
    def __init__(self):
        super().__init__(
            role_name="Company Investigator",
            system_instruction=(
                "You are the Company Investigator. For each HIGH MATCH opportunity, research the "
                "employer and vacancy (using the provided context). Find recent developments, hiring "
                "context, and useful information for tailoring an application. Produce a concise "
                "research brief with source links. Do NOT contact anyone."
            )
        )
    
    def research(self, job_data):
        # In a real scenario, this agent would be equipped with a Google Search Tool.
        # For this implementation, we simulate the research using the LLM's internal knowledge base.
        prompt = f"""
        **Job Vacancy Details:**
        {job_data}

        Please provide a research brief on this company and role context.
        """
        return self.run(prompt)

class ApplicationTailor(Agent):
    def __init__(self):
        super().__init__(
            role_name="Application Tailor",
            system_instruction=(
                "You are the Application Tailor. Receive HIGH MATCH vacancies and the Company "
                "Investigator report. Create a vacancy-specific version of the resume. Reorder and "
                "emphasize genuine experience according to the vacancy. Create a short tailored cover letter. "
                "NEVER invent employment, degrees, achievements, skills, dates, or numbers. "
                "Produce drafts only. Never submit an application."
            )
        )
    
    def draft(self, job_data, cv_text, research_report):
        prompt = f"""
        **Job Vacancy Details:**
        {job_data}

        **Master CV:**
        {cv_text}

        **Company Research Report:**
        {research_report}

        Please provide:
        1. A Tailored Cover Letter Draft
        2. Suggestions on which bullet points from the CV to emphasize or reorder.
        """
        return self.run(prompt)

class NetworkScout(Agent):
    def __init__(self):
        super().__init__(
            role_name="Network Scout",
            system_instruction=(
                "You are the Network Scout. For every HIGH MATCH vacancy, identify professional contacts "
                "relevant to the role (recruiters, hiring managers). Explain why each person may be relevant. "
                "Draft a personalized outreach message. NEVER send messages without approval."
            )
        )
    
    def find_contacts(self, job_data, research_report):
        prompt = f"""
        **Job Vacancy Details:**
        {job_data}

        **Company Research Report:**
        {research_report}

        Draft potential outreach messages and suggest titles of people (e.g., 'Head of Engineering at X') to look for on LinkedIn.
        """
        return self.run(prompt)
