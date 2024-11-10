# misc imports
import sys
import time
import requests
from typing import Any, List, Optional
from pydantic import validate_arguments


SERVER_URL = 'http://localhost:5000'

@validate_arguments(config=dict(arbitrary_types_allowed=True))
def submit_jobs(
    config_list: List[Any],
    exp_class: Optional[Any] = None,
    job_func: Optional[Any] = None,
    available_gpus: Optional[List[str]] = None,
    submission_delay: int = 4.0
):
    # Precisely one of exp_class or job_func must be defined.
    assert (exp_class is not None) ^ (job_func is not None), \
        "Exactly one of exp_class or job_func must be defined."
    # We might have to convert exp_class and job_func to strings.
    if exp_class is not None and not isinstance(exp_class, str):
        exp_class = f"{exp_class.__module__}.{exp_class.__name__}"
    if job_func is not None and not isinstance(job_func, str):
        job_func = f"{job_func.__module__}.{job_func.__name__}"
    
    url = f"{SERVER_URL}/submit"
    payload_defaults = {
        'configt': config_list,
        'exp_class': exp_class,
        'job_func': job_func,
        'available_gpus': available_gpus,
        'submission_delay': submission_delay 
    }
    for cfg in config_list:
        try:
            payload_dict = {
                'config': cfg,
                **payload_defaults
            }
            response = requests.post(url, json=payload_dict)
            time.sleep(submission_delay)
            if response.status_code == 200:
                successful_job = response.json()
                print(f"--> Launched job-id: {successful_job.get('job_id')} on gpu: {successful_job.get('gpu_id')}.")
            else:
                print(f"Failed to submit job: {response.json().get('error')}")
        except requests.exceptions.ConnectionError:
            print("Failed to connect to the scheduler server. Is it running?")
            sys.exit(1)