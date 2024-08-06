from flask import Flask, jsonify, request, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from uuid import uuid4 as uuid
from threading import Thread
from datetime import datetime
import json

from flask_cors import CORS

from crew import CompanyResearchCrew
from job_manager import append_event, jobs_lock, jobs, Event

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["4 per day"]  # Adjust the limit as needed
)

def kickoff_crew(job_id: str, companies: list[str], positions: [list]):
    print(f"Running crew for {job_id} with companies: {companies} and positions: {positions}")

    results = None
    try:
        company_research_crew = CompanyResearchCrew(job_id)
        company_research_crew.setup_crew(companies, positions)
        results = company_research_crew.kickoff()

    except Exception as e:
        print(f"Error running crew for {job_id}: {e}")
        append_event(job_id, f"CREW FAILED: {str(e)}")
        with jobs_lock:
            jobs[job_id].status = "ERROR"
            jobs[job_id].result = str(e)

    with jobs_lock:
        jobs[job_id].status = "COMPLETED"
        jobs[job_id].result = results
        jobs[job_id].events.append(Event(
            data="CREW COMPLETED",
            timestamp=datetime.now()
        )
        )

@app.route('/api/crew', methods=['POST'])
@limiter.limit("4 per day")  # Limit to 4 requests per day per IP
def run_crew():
    data = request.json
    if not data or 'companies' not in data or 'positions' not in data:
        abort(400, description="Invalid request: Incorrect or Missing data. Please provide companies and positions.")

    job_id = str(uuid())
    companies = data['companies']
    positions = data['positions']

    # Run the crew
    thread = Thread(target=kickoff_crew, args=(job_id, companies, positions))
    thread.start()

    return jsonify({'job_id': job_id}), 200

@app.route('/api/crew/<job_id>', methods=['GET'])
def get_status(job_id):
    # TODO: Lock the job
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            abort(404, description="Job not found")

    # Parse the JSON data
    try:
        result_json = json.loads(job.result)
    except:
        result_json = job.result

    # Return Everything
    return jsonify({
        'job_id': job_id,
        'status': job.status,
        'result': result_json,
        'events': [{
            "timestamp": event.timestamp.isoformat(),
            "data": event.data
        } for event in job.events]
    }), 200

if __name__ == '__main__':
    app.run()