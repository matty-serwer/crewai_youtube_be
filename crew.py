from agents import CompanyResearchAgents
from job_manager import append_event
from tasks import CompanyResearchTasks
from crewai import Crew

class CompanyResearchCrew:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.crew = None

    def setup_crew(self, companies: list[str], positions: [list]):
        print(f"Running crew for {self.job_id} with companies: {companies} and positions: {positions}")

        # SETUP AGENTS
        agents = CompanyResearchAgents(self.job_id)
        research_manager = agents.research_manager(companies, positions)
        company_research_agent = agents.company_research_agent()

        # SETUP TASKS
        tasks = CompanyResearchTasks(self.job_id)
        company_research_tasks = [
            tasks.company_research(company_research_agent, company, positions) for company in companies
        ]
        manage_research = tasks.manage_research(research_manager, companies, positions, company_research_tasks)

        # CREATE CREW
        self.crew = Crew(
            agents=[research_manager, company_research_agent],
            tasks=[*company_research_tasks, manage_research],
            verbose=2
        )

    def kickoff(self):
        if not self.crew:
            print(f"Error: Crew not setup for {self.job_id}")
            return
        append_event(self.job_id, "CREW STARTED")
        try:
            print(f"Running crew for {self.job_id}")
            results = self.crew.kickoff()
            append_event(self.job_id, f"CREW COMPLETED: {results}")
            return results

        except Exception as e:
            append_event(self.job_id, f"CREW ERROR: {e}")
            return str(e)

