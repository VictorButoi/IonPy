# misc imports
import os
import sys
import pathlib
import submitit
from typing import List, Any, Union
from pydantic import validate_arguments

# ionpy imports
from ionpy.util import Config


@validate_arguments(config=dict(arbitrary_types_allowed=True))
def run_exp(
    exp_class: Any,
    exp_object: Union[pathlib.Path, Config],
    gpu: int = '0'
):
    # Important imports, otherwise the processes will not be able to import the necessary modules
    sys.path.append('/storage/vbutoi/projects')
    sys.path.append('/storage/vbutoi/projects/ESE')

    # Set the visible gpu.
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)

    # Get the experiment class, either fresh or from a path.
    if isinstance(exp_object, Config): 
       exp = exp_class.from_config(exp_object)
    else:
        exp = exp_class(exp_object)

    # Run the experiment.
    exp.run()


class SliteRunner:

    def __init__(
            self, 
            project: str,
            exp_class: Any,
            available_gpus: List[str],
            exp_name: str = None, 
            log_root_dir: str='/storage/vbutoi/scratch'
            ):

        # Configure Submitit object
        self.project_name = project 
        self.exp_name = exp_name
        self.log_root_dir = log_root_dir
        self.avail_gpus = available_gpus
        self.exp_class = exp_class 

        # Initalize executor if not none
        if exp_name is not None:
            self.init_executor()

        # Keep cache of jobs
        self.jobs = []
    
    def init_executor(self):
        # Create submitit executor
        submitit_root = f"{self.log_root_dir}/{self.project_name}/{self.exp_name}/submitit"

        # Setup the excutor parameters
        self.executor = submitit.LocalExecutor(folder=submitit_root)
        self.executor.parameters['visible_gpus'] = self.avail_gpus
        self.executor.parameters['timeout_min'] = int(24 * 60 * 7)

        print("Initalized SliteRunner")

    def set_exp_name(self, exp_name):
        self.exp_name = exp_name
        self.init_executor()

    def submit_exps(
        self,
        exp_objects: List[Any] = None
    ):
        assert self.exp_name is not None, "Must set exp_name before running experiment."
        # exp_objects is a list of either configs or exp_paths
        assert len(exp_objects) <= len(self.avail_gpus),\
                "Currently, must have same number of experiments as available gpus."

        # Keep track of the local jobs
        local_job_list = []

        for c_idx, exp_obj in enumerate(exp_objects):

            # Submit the job
            job = self.executor.submit(
                run_exp,
                exp_class=self.exp_class,
                exp_object=exp_obj,
                gpu=self.avail_gpus[c_idx] 
            )

            print(f"Submitted job id: {job.job_id}.")
            self.jobs.append(job)
            local_job_list.append(job)
        
        return local_job_list

    def kill_jobs(
        self,
        job_list = None
    ):
        if job_list is None:
            job_list = self.jobs
            
        for job in job_list:
            job.cancel()
