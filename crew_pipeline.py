#!/usr/bin/env python3
import os
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ======================
# Define Agents
# ======================
architect = Agent(
    role="System Architect",
    goal="Design a working system that integrates Airtable, the job scraper, and Excel export.",
    backstory="Senior architect with 15 years of experience building scalable systems.",
    verbose=True,
    llm="anthropic/claude-3-haiku-20240307"   # Claude Haiku
)

integration_engineer = Agent(
    role="Integration Engineer",
    goal="Implement Airtable API integration, job scraper wrapper, and Excel export inside FastAPI.",
    backstory="Python backend engineer specializing in APIs and scrapers.",
    verbose=True,
    llm="ollama/gemma:2b"   # Local Gemma-2B via Ollama
)

qa_engineer = Agent(
    role="QA Engineer",
    goal="Test the system thoroughly and debug until it is error-free.",
    backstory="Expert at catching bugs and stress-testing systems.",
    verbose=True,
    llm="anthropic/claude-3-haiku-20240307"   # Claude Haiku
)

deployment_specialist = Agent(
    role="Deployment Specialist",
    goal="Prepare the system for local and cloud deployment with smooth setup.",
    backstory="Ops specialist with experience in packaging and cloud deployment.",
    verbose=True,
    llm="ollama/gemma:2b"   # Local Gemma-2B via Ollama
)

# ======================
# Define Tasks
# ======================
challenge_brief = """
Build a complete Job Application Management System:

- Web interface (FastAPI + HTML/JS frontend)
- Connect to Airtable to fetch clients
- For each client: run job scraper, save jobs, export Excel (company, description, link, applied-status)
- Prevent duplicates, organize jobs per client/date
- Future-ready for AI agents to auto-apply later
- Deliver code, requirements.txt, and deployment instructions
"""

task_architecture = Task(
    description="Analyze the challenge and produce a full architecture (data flow, tech stack, integration points).",
    agent=architect,
    expected_output="System architecture with flow diagrams and error handling strategy."
)

task_integration = Task(
    description="Implement FastAPI backend with Airtable integration, scraper wrapper, and Excel export endpoints.",
    agent=integration_engineer,
    expected_output="Production-ready Python code (main.py + helpers).",
    context=[task_architecture]
)

task_qa = Task(
    description="Test the implementation end-to-end, validate Airtable fetch, scraper results, Excel export, and fix errors.",
    agent=qa_engineer,
    expected_output="QA test logs confirming stability.",
    context=[task_integration]
)

task_deployment = Task(
    description="Prepare deployment package: requirements.txt, .env example, and step-by-step run instructions.",
    agent=deployment_specialist,
    expected_output="Deployment-ready package with docs.",
    context=[task_qa]
)

# ======================
# Crew Definition
# ======================
crew = Crew(
    agents=[architect, integration_engineer, qa_engineer, deployment_specialist],
    tasks=[task_architecture, task_integration, task_qa, task_deployment],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("🚀 Crew AI Job Scraper Challenge Starting (Claude 🤝 Gemma)...")
    result = crew.kickoff(inputs={"challenge": challenge_brief})
    print("\n=== FINAL DELIVERABLE ===")
    print(result)
