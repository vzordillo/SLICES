# -*- coding: UTF-8 -*-
# Hang Xiao 2024.03
# xiaohang07@live.cn
import os,sys,glob,json,io
import re,time
import numpy as np
import math,json
import tempfile
from tqdm import tqdm
from pymatgen.core.structure import Structure
import warnings
warnings.filterwarnings("ignore")
import contextlib
from itertools import zip_longest
import configparser
from contextlib import redirect_stdout
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import math
import shutil  # Used to check if SLURM commands exist
import logging
import subprocess
import getpass
from multiprocessing import Pool, cpu_count
from functools import partial
@contextlib.contextmanager
def temporaryWorkingDirectory(path):
    """
    Context manager to temporarily change the working directory.
    
    Changes to the specified directory for the duration of the context block,
    then restores the original working directory when exiting.
    
    Args:
        path (str): Path to the directory to change to
        
    Yields:
        None: Context manager yields control to the block
    """
    _oldCWD = os.getcwd()
    os.chdir(os.path.abspath(path))

    try:
        yield
    finally:
        os.chdir(_oldCWD)

def split_list(a, n):
    """
    Split a list into n approximately equal parts.
    
    Divides the list into n sublists with sizes as equal as possible.
    The remainder is distributed among the first few sublists.
    
    Args:
        a (list): List to split
        n (int): Number of parts to split into
        
    Yields:
        list: Generator yielding each sublist
    """
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def is_slurm_available():
    """
    Check if SLURM job management system is installed.
    
    Returns:
        bool: True if SLURM is available, False otherwise
    """
    return shutil.which('sinfo') is not None or shutil.which('squeue') is not None


def splitRun(filename,threads,skip_header=False):
    """
    Split and run tasks locally, automatically adjusting thread count to avoid empty task allocation.

    Args:
        filename (str): Path to JSON file containing task list
        threads (int): Desired number of threads
        skip_header (bool, optional): Whether to skip header in task list. Defaults to False.
    """
    # Clean up previous task directories and results
    for pattern in ['job_*', 'structures_ori_opt']:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
    if os.path.exists('./result.csv'):
        os.remove('./result.csv')
    
    # Read task list
    with open(filename, 'r') as f:
        try:
            cifs = json.load(f)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return
    
    # Adjust task list based on whether to skip header
    if skip_header:
        tasks = cifs[1:]
    else:
        tasks = cifs
    
    # Filter out any empty task entries (e.g., None or empty dict)
    tasks = [task for task in tasks if task]
    
    total_tasks = len(tasks)
    
    # Adjust thread count if task count is less than thread count
    actual_threads = min(threads, total_tasks) if total_tasks > 0 else 1
    if actual_threads < threads:
        print(f"Task count ({total_tasks}) is less than thread count ({threads}), will use {actual_threads} threads.")
    
    # Split task list
    cifs_split = list(split_list(tasks, actual_threads))
    use_slurm = is_slurm_available()
    # Create and submit each subtask
    for i in range(len(cifs_split)):
        job_dir = f'job_{i}'
        os.mkdir(job_dir)
        if os.path.exists('./workflow'):
            shutil.copytree('./workflow', job_dir, dirs_exist_ok=True)
        temp_json_path = os.path.join(job_dir, 'temp.json')
        with open(temp_json_path, 'w') as f:
            json.dump(cifs_split[i], f)
        
        # Submit task
        os.chdir(job_dir)
        if use_slurm:
            os.system('sbatch 0_run.sh > /dev/null 2>&1')
        else:
            os.system('python 0_run.py > log.txt 2> error.txt &')
        os.chdir('..')
    
    print("Computation tasks submitted.")

def splitRun_csv(filename,threads,skip_header=False):
    # Clean up previous task directories and results
    import glob
    import shutil
    for pattern in ['job_*', 'structures_ori_opt']:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
    if os.path.exists('./result.csv'):
        os.remove('./result.csv')
    
    # Read task list and exclude empty lines
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    if skip_header:
        lines = lines[1:]
    
    # Filter out any empty lines or lines containing only whitespace
    cifs = [line for line in lines if line.strip()]
    
    total_tasks = len(cifs)
    
    # Adjust thread count if task count is less than thread count
    actual_threads = min(threads, total_tasks) if total_tasks > 0 else 1
    if actual_threads < threads:
        print(f"Task count ({total_tasks}) is less than thread count ({threads}), will use {actual_threads} threads.")
    
    # Split task list
    cifs_split = list(split_list(cifs, actual_threads))
    use_slurm = is_slurm_available()
    # Create and submit each subtask
    for i in range(len(cifs_split)):
        job_dir = f'job_{i}'
        os.mkdir(job_dir)
        if os.path.exists('./workflow'):
            shutil.copytree('./workflow', job_dir, dirs_exist_ok=True)
        temp_csv_path = os.path.join(job_dir, 'temp.csv')
        with open(temp_csv_path, 'w') as f:
            f.writelines(cifs_split[i])
        
        # Submit task
        os.chdir(job_dir)
        if use_slurm:
            os.system('sbatch 0_run.sh > /dev/null 2>&1')
        else:
            os.system('python 0_run.py > log.txt 2> error.txt &')
        os.chdir('..')
    
    print("Computation tasks submitted.")

def splitRun_sample(threads=8,sample_size=8000):
    config = configparser.ConfigParser()
    for pattern in ['job_*', 'structures_ori_opt']:
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
    if os.path.exists('./result.csv'):
        os.remove('./result.csv')
    config["Settings"] = {'sample_size':int(sample_size/threads) }
    with open('./workflow/settings.ini', 'w') as configfile:
        config.write(configfile)
    for i in range(threads):
        os.mkdir('job_'+str(i))
        # Copy workflow directory contents (cross-platform)
        workflow_dst = 'job_'+str(i)
        if os.path.exists('./workflow'):
            if not os.path.exists(workflow_dst):
                os.makedirs(workflow_dst, exist_ok=True)
            for item in os.listdir('./workflow'):
                src = os.path.join('./workflow', item)
                dst = os.path.join(workflow_dst, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        os.chdir('job_'+str(i))
        if len(sys.argv)==2:
            if sys.argv[1]=="test":
                os.system('qsub 0_test.pbs')
        else:
            os.system('qsub 0_run.pbs > /dev/null 2>&1')
        os.chdir('..')
    print("Sampling tasks have been submitted.")

def show_progress(total_jobs=None, check_interval=5):
    use_slurm = is_slurm_available()
    if use_slurm:
        print("SLURM system detected. Using SLURM-based processing.")
        try:
            countTask = 0
            totalTask = 0  # Initialize total task count
            current_user = getpass.getuser()  # Get current username using getpass
            with tqdm(total=100, position=0, leave=True,
                      bar_format='{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}') as pbar:
                pbar.set_description("Progress")
                while True:
                    countTask0 = countTask
                    # Use squeue command to get current user's job status
                    try:
                        result = subprocess.run(
                            ['squeue', '-u', current_user, '-h', '-o', '%T'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=True
                        )
                        log = result.stdout.splitlines()
                    except subprocess.CalledProcessError as e:
                        print(f"Error executing squeue: {e.stderr}")
                        break

                    countTask = sum(1 for state in log if state in ['RUNNING', 'PENDING', 'CONFIGURING', 'SUSPENDED'])

                    # If new task count increases, reset progress bar
                    if countTask0 < countTask:
                        totalTask = countTask
                        pbar.reset(total=100)
                        pbar.set_description("Progress")

                    # If task count decreases, update progress bar
                    if countTask0 > countTask and totalTask > 0:
                        completed = (totalTask - countTask) / totalTask * 100
                        pbar.update(completed - pbar.n)  # Update to new completion percentage

                    # If all tasks complete, update progress bar to 100% and exit
                    if countTask == 0 and totalTask > 0:
                        pbar.n = pbar.total
                        pbar.refresh()
                        break

                    time.sleep(check_interval)
        except KeyboardInterrupt:
            # Cancel all jobs when user interrupts
            try:
                subprocess.run(['scancel', '-u', current_user], check=True)
                print("\nAll jobs have been canceled")
            except subprocess.CalledProcessError as e:
                print(f"\nError cancelling jobs: {e.stderr}")
        except EnvironmentError as env_err:
            print(env_err)
    else:
        print("No SLURM system detected. Falling back to local processing.")
        try:
            # If total job count not provided, automatically detect job_* directories
            if total_jobs is None:
                job_dirs = glob.glob("job_*")
                total_jobs = len(job_dirs)

            if total_jobs == 0:
                print("No tasks detected for monitoring.")
                logging.info("No tasks detected for monitoring.")
                return

            # Get absolute path of current working directory for process matching
            current_dir = os.path.abspath(os.getcwd())

            with tqdm(total=total_jobs, position=0, leave=True,
                    bar_format='{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}') as pbar:
                completed = 0

                while completed < total_jobs:
                    completed = 0

                    # Get all running python processes and their working directories
                    running_jobs = set()
                    try:
                        # Use ps command to get all python process PIDs and working directories
                        result = subprocess.run(
                            ['ps', 'aux'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )

                        for line in result.stdout.splitlines():
                            # Find python processes containing 0_run.py
                            if 'python' in line and '0_run.py' in line:
                                parts = line.split()
                                if len(parts) > 1:
                                    pid = parts[1]
                                    try:
                                        # Use pwdx to get process working directory
                                        pwd_result = subprocess.run(
                                            ['pwdx', pid],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            text=True
                                        )
                                        if pwd_result.returncode == 0:
                                            # pwdx output format: "PID: /path/to/dir"
                                            pwd_output = pwd_result.stdout.strip()
                                            if ':' in pwd_output:
                                                job_path = pwd_output.split(':', 1)[1].strip()
                                                # Extract job_X directory name
                                                if 'job_' in job_path:
                                                    job_dir_name = os.path.basename(job_path)
                                                    if job_dir_name.startswith('job_'):
                                                        running_jobs.add(job_dir_name)
                                    except:
                                        pass
                    except:
                        pass

                    # Check status of each task
                    for i in range(total_jobs):
                        job_dir = f'job_{i}'
                        is_completed = False

                        # If process not in running list, check output files
                        if job_dir not in running_jobs:
                            # Check if output files exist and have content
                            output_file1 = os.path.join(job_dir, 'output.json')
                            output_file2 = os.path.join(job_dir, 'result.csv')

                            # Check output.json
                            if os.path.exists(output_file1):
                                try:
                                    file_size = os.path.getsize(output_file1)
                                    if file_size > 10:
                                        is_completed = True
                                except (OSError, IOError):
                                    pass

                            # Check result.csv
                            if not is_completed and os.path.exists(output_file2):
                                try:
                                    file_size = os.path.getsize(output_file2)
                                    if file_size > 20:
                                        is_completed = True
                                except (OSError, IOError):
                                    pass

                        if is_completed:
                            completed += 1

                    pbar.n = completed
                    pbar.refresh()
                    time.sleep(check_interval)

                pbar.n = pbar.total
                pbar.refresh()
        except KeyboardInterrupt:
            print("\nCancellation detected. Terminating all 'pt_main_thread' and 'python' processes...")
            logging.info("Cancellation detected. Attempting to terminate all 'pt_main_thread' and 'python' processes.")
            try:
                # Define list of process names to find
                process_names = ["pt_main_thread", "python"]
                all_pids = []
                for proc_name in process_names:
                    try:
                        # Use pgrep to find exact matching process names
                        pgrep_output = subprocess.check_output(["pgrep", "-f", proc_name], stderr=subprocess.DEVNULL).decode().strip()
                        pids = pgrep_output.split('\n') if pgrep_output else []
                        pids = [pid for pid in pids if pid.isdigit()]
                        all_pids.extend(pids)
                    except subprocess.CalledProcessError:
                        # If no matching process found, continue
                        continue
                
                if not all_pids:
                    print("No processes named 'pt_main_thread' or 'python' found.")
                    logging.info("No processes named 'pt_main_thread' or 'python' found.")
                else:
                    unique_pids = list(set(all_pids))  # Remove duplicate PIDs
                    print(f"Found PIDs: {', '.join(unique_pids)}")
                    logging.info(f"Found PIDs: {', '.join(unique_pids)}")
                    
                    # Send SIGTERM signal to gracefully terminate processes
                    print("Sending SIGTERM signal...")
                    logging.info("Sending SIGTERM signal to processes.")
                    try:
                        subprocess.run(["kill"] + unique_pids, check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to send SIGTERM signal: {e}")
                        logging.error(f"Failed to send SIGTERM signal: {e}")
                    
                    # Wait 5 seconds to allow processes to gracefully terminate
                    time.sleep(5)
                    
                    # Check which processes are still running
                    remaining_pids = []
                    for proc_name in process_names:
                        try:
                            remaining_pgrep = subprocess.check_output(["pgrep", "-f", proc_name], stderr=subprocess.DEVNULL).decode().strip()
                            rem_pids = remaining_pgrep.split('\n') if remaining_pgrep else []
                            rem_pids = [pid for pid in rem_pids if pid.isdigit()]
                            remaining_pids.extend(rem_pids)
                        except subprocess.CalledProcessError:
                            continue
                    
                    remaining_pids = list(set(remaining_pids))  # Remove duplicate PIDs
                    
                    if remaining_pids:
                        print(f"Processes not terminated, sending SIGKILL signal: {', '.join(remaining_pids)}")
                        logging.info(f"Processes not terminated, sending SIGKILL signal: {', '.join(remaining_pids)}")
                        try:
                            subprocess.run(["kill", "-9"] + remaining_pids, check=True)
                            print("All related processes have been force terminated.")
                            logging.info("All related processes have been force terminated.")
                        except subprocess.CalledProcessError as e:
                            print(f"Failed to send SIGKILL signal: {e}")
                            logging.error(f"Failed to send SIGKILL signal: {e}")
                    else:
                        print("All related processes successfully terminated.")
                        logging.info("All related processes successfully terminated.")
            except subprocess.CalledProcessError:
                print("No processes named 'pt_main_thread' or 'python' found.")
                logging.info("No processes named 'pt_main_thread' or 'python' found.")
            except Exception as e:
                print(f"Error terminating processes: {e}")
                logging.error(f"Error terminating processes: {e}")
            
            print("Starting task directory cleanup...")
            logging.info("Starting task directory cleanup.")
            # Clean up job_* directories
            job_dirs = glob.glob("job_*")
            for job_dir in job_dirs:
                try:
                    if os.path.isdir(job_dir):
                        shutil.rmtree(job_dir)
                        print(f"Deleted directory: {job_dir}")
                        logging.info(f"Deleted directory: {job_dir}")
                except FileNotFoundError:
                    print(f"Directory does not exist: {job_dir}")
                    logging.warning(f"Directory does not exist: {job_dir}")
                except Exception as e:
                    print(f"Unable to delete directory {job_dir}: {e}")
                    logging.error(f"Unable to delete directory {job_dir}: {e}")
            
            print("Task monitoring ended.")
            logging.info("Task monitoring ended.")
        finally:
            print("Task monitoring ended.")
            logging.info("Task monitoring ended.")      

def cancel_all_jobs():
    use_slurm = is_slurm_available()
    if use_slurm:
        current_user = getpass.getuser()  # Get current username using getpass
        subprocess.run(['scancel', '-u', current_user], check=True)
        print("All jobs have been canceled")
    else:
        try:
            # Define list of process names to find
            process_names = ["pt_main_thread", "python"]
            all_pids = []
            for proc_name in process_names:
                try:
                    # Use pgrep to find exact matching process names
                    pgrep_output = subprocess.check_output(["pgrep", "-f", proc_name], stderr=subprocess.DEVNULL).decode().strip()
                    pids = pgrep_output.split('\n') if pgrep_output else []
                    pids = [pid for pid in pids if pid.isdigit()]
                    all_pids.extend(pids)
                except subprocess.CalledProcessError:
                    # If no matching process found, continue
                    continue
            
            if not all_pids:
                print("No processes named 'pt_main_thread' or 'python' found.")
                logging.info("No processes named 'pt_main_thread' or 'python' found.")
            else:
                unique_pids = list(set(all_pids))  # Remove duplicate PIDs
                print(f"Found PIDs: {', '.join(unique_pids)}")
                logging.info(f"Found PIDs: {', '.join(unique_pids)}")
                
                # Send SIGTERM signal to gracefully terminate processes
                print("Sending SIGTERM signal...")
                logging.info("Sending SIGTERM signal to processes.")
                try:
                    subprocess.run(["kill"] + unique_pids, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Failed to send SIGTERM signal: {e}")
                    logging.error(f"Failed to send SIGTERM signal: {e}")
                
                # Wait 5 seconds to allow processes to gracefully terminate
                time.sleep(5)
                
                # Check which processes are still running
                remaining_pids = []
                for proc_name in process_names:
                    try:
                        remaining_pgrep = subprocess.check_output(["pgrep", "-f", proc_name], stderr=subprocess.DEVNULL).decode().strip()
                        rem_pids = remaining_pgrep.split('\n') if remaining_pgrep else []
                        rem_pids = [pid for pid in rem_pids if pid.isdigit()]
                        remaining_pids.extend(rem_pids)
                    except subprocess.CalledProcessError:
                        continue
                
                remaining_pids = list(set(remaining_pids))  # Remove duplicate PIDs
                
                if remaining_pids:
                    print(f"Processes not terminated, sending SIGKILL signal: {', '.join(remaining_pids)}")
                    logging.info(f"Processes not terminated, sending SIGKILL signal: {', '.join(remaining_pids)}")
                    try:
                        subprocess.run(["kill", "-9"] + remaining_pids, check=True)
                        print("All related processes have been force terminated.")
                        logging.info("All related processes have been force terminated.")
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to send SIGKILL signal: {e}")
                        logging.error(f"Failed to send SIGKILL signal: {e}")
                else:
                    print("All related processes successfully terminated.")
                    logging.info("All related processes successfully terminated.")
        except subprocess.CalledProcessError:
            print("No processes named 'pt_main_thread' or 'python' found.")
            logging.info("No processes named 'pt_main_thread' or 'python' found.")
        except Exception as e:
            print(f"Error terminating processes: {e}")
            logging.error(f"Error terminating processes: {e}")

        print("Starting task directory cleanup...")
        logging.info("Starting task directory cleanup.")
        # Clean up job_* directories
        job_dirs = glob.glob("job_*")
        for job_dir in job_dirs:
            try:
                if os.path.isdir(job_dir):
                    shutil.rmtree(job_dir)
                    print(f"Deleted directory: {job_dir}")
                    logging.info(f"Deleted directory: {job_dir}")
            except FileNotFoundError:
                print(f"Directory does not exist: {job_dir}")
                logging.warning(f"Directory does not exist: {job_dir}")
            except Exception as e:
                print(f"Unable to delete directory {job_dir}: {e}")
                logging.error(f"Unable to delete directory {job_dir}: {e}")

def collect_json(output,glob_target,cleanup=True):
    data=[]               
    for f in glob.glob(glob_target, recursive=True):
        with open(f,"r") as infile:
            temp=json.load(infile)  # put each cifs into the final list
            for i in temp:
                data.append(i)
    with open(output,'w') as outfile:
        json.dump(data, outfile)     
    if cleanup:
        for i in glob.glob("job_*"):
            if os.path.isdir(i):
                shutil.rmtree(i)
            elif os.path.isfile(i):
                os.remove(i)
    print("Results have been collected into: "+output)

def collect_csv(output,glob_target,header="",index=False,cleanup=True):
    result_sli=""
    if index:
        index=0
        for i in glob.glob(glob_target):
            with open(i,'r') as result:
                lines=result.readlines()
                for j in range(len(lines)):
                    result_sli+=str(index)+','+lines[j]
                    index+=1
    else:
        for f in glob.glob(glob_target, recursive=True):
            with open(f,"r") as infile:
                result_sli += infile.read()
    with open(output,'w') as result:
        if header!="":
            result.write(header)
        result.write(result_sli)  
    if cleanup:
        for i in glob.glob("job_*"):
            if os.path.isdir(i):
                shutil.rmtree(i)
            elif os.path.isfile(i):
                os.remove(i)
    print("Results have been collected into: "+output)

def collect_csv_filter(output,glob_target,header,condition,cleanup=True):
    result_csv=''
    result_filtered_csv=''
    for i in glob.glob(glob_target):
        with open(i,'r') as result:
            for j in result.readlines():
                result_csv+=j
                if condition(j):
                    result_filtered_csv+=j
    with open(output,'w') as result:
        if header!="":
            result.write(header)
        result.write(result_csv) 
    with open(output.split('.')[0]+"_filtered."+output.split('.')[1],'w') as result:
        if header!="":
            result.write(header)
        result.write(result_filtered_csv) 
    if cleanup:
        for i in glob.glob("job_*"):
            if os.path.isdir(i):
                shutil.rmtree(i)
            elif os.path.isfile(i):
                os.remove(i)
    print("Results have been collected into: "+output)

def exclude_elements_json(input_json,exclude_elements):
    print("excluding materials containing elements not supported")
    flitered_json = []
    for i in tqdm(input_json,position=0, leave=True,bar_format='{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}'):
        ori = Structure.from_str(i['cif'],fmt="cif")
        species=[str(j) for j in ori.species]
        flag=0
        for j in species:
            if j in exclude_elements:
                flag+=1
                break
        if not flag and i["material_id"] != None:
            flitered_json.append(i)
    print(str(round((len(input_json)-len(flitered_json))/len(input_json)*100,1))+"% materials excluded")
    return flitered_json


def determine_bin_count(data_size, target_values):
    # Use Sturges rule as starting point
    sturges_bins = math.ceil(math.log2(data_size)) + 1
    
    # Use Freedman-Diaconis rule
    q75, q25 = np.percentile(target_values, [75, 25])
    iqr = q75 - q25
    bin_width = 2 * iqr * (len(target_values) ** (-1/3))
    fd_bins = math.ceil((max(target_values) - min(target_values)) / bin_width)
    
    # Use Scott rule
    scott_bins = math.ceil((max(target_values) - min(target_values)) / (3.5 * np.std(target_values) * (len(target_values) ** (-1/3))))
    
    # Take average of these methods and ensure bin count is in reasonable range
    avg_bins = int(np.mean([sturges_bins, fd_bins, scott_bins]))
    return max(min(avg_bins, data_size // 20), 5)  # At least 5 bins, at most 1/20 of data points

def adaptive_dynamic_binning(data, target_column, test_size=0.2, random_state=42):
    # Convert target column to numeric, set errors='coerce' to convert non-numeric to NaN
    data[target_column] = pd.to_numeric(data[target_column], errors='coerce')
    
    # Remove NaN values from target column
    data_cleaned = data.dropna(subset=[target_column])
    
    print(f"\nOriginal data rows: {len(data)}")
    print(f"Cleaned data rows: {len(data_cleaned)}")
    
    # Automatically determine bin count
    target_values = data_cleaned[target_column].values
    n_bins = determine_bin_count(len(data_cleaned), target_values)
    print(f"Automatically determined bin count: {n_bins}")
    
    # Create bins using quantile method
    percentiles = [i * 100 / n_bins for i in range(n_bins + 1)]
    bins = list(data_cleaned[target_column].quantile([p/100 for p in percentiles]))
    
    # Ensure bin boundaries are unique
    bins = sorted(set(bins))
    
    # Add labels to bins
    labels = [f'Bin{i+1}' for i in range(len(bins) - 1)]
    
    # Divide target values into intervals
    data_cleaned['bin'] = pd.cut(data_cleaned[target_column], bins=bins, labels=labels, include_lowest=True)
    
    train_data = pd.DataFrame(columns=data_cleaned.columns)
    test_data = pd.DataFrame(columns=data_cleaned.columns)
    
    # Perform stratified sampling for each interval
    for bin_label in data_cleaned['bin'].unique():
        bin_data = data_cleaned[data_cleaned['bin'] == bin_label]
        if len(bin_data) > 1:
            bin_train, bin_test = train_test_split(bin_data, test_size=test_size, random_state=random_state)
        else:
            bin_train, bin_test = bin_data, pd.DataFrame()
        
        train_data = pd.concat([train_data, bin_train])
        test_data = pd.concat([test_data, bin_test])
    
    # Remove temporary 'bin' column
    train_data = train_data.drop('bin', axis=1)
    test_data = test_data.drop('bin', axis=1)
    
    # Shuffle data
    train_data = train_data.sample(frac=1, random_state=random_state).reset_index(drop=True)
    test_data = test_data.sample(frac=1, random_state=random_state).reset_index(drop=True)
    
    return train_data, test_data, bins

def parallel_process_json(process_func, data, n_processes=16, output_file='result.csv', **kwargs):
    """
    Use multiprocessing Pool for parallel processing, each process uses single CPU.

    Args:
        process_func: Processing function that receives single data item and kwargs
        data (list): Data list to process (usually loaded from JSON file)
        n_processes (int): Number of parallel processes, default 16
        output_file (str): Output filename, default 'result.csv'
        **kwargs: Additional arguments passed to process_func

    Returns:
        list: List of processing results
    """
    # Set each process to use only 1 CPU
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"

    # Ensure process count doesn't exceed data size and CPU core count
    n_processes = min(n_processes, len(data), cpu_count())

    print(f"Using {n_processes} processes for parallel processing...")

    # Create partial function, pre-fill kwargs
    func_with_kwargs = partial(process_func, **kwargs)

    # Use Pool for parallel processing
    results = []
    with Pool(processes=n_processes) as pool:
        # Use imap_unordered for performance and add progress bar
        with tqdm(total=len(data), position=0, leave=True,
                  bar_format='{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}') as pbar:
            for result in pool.imap_unordered(func_with_kwargs, data, chunksize=1):
                if result is not None:
                    results.append(result)
                pbar.update(1)

    # Save results
    if results and output_file:
        with open(output_file, 'w') as f:
            for result in results:
                f.write(str(result) + '\n')
        print(f"Results saved to: {output_file}")

    return results

def parallel_process_csv(process_func, filename, n_processes=16, output_file='result.csv', skip_header=False, **kwargs):
    """
    Use multiprocessing Pool for parallel processing CSV file, each process uses single CPU.

    Args:
        process_func: Processing function that receives single line text and kwargs
        filename (str): CSV file path
        n_processes (int): Number of parallel processes, default 16
        output_file (str): Output filename, default 'result.csv'
        skip_header (bool): Whether to skip first line, default False
        **kwargs: Additional arguments passed to process_func

    Returns:
        list: List of processing results
    """
    # Set each process to use only 1 CPU
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"

    # Read CSV file
    with open(filename, 'r') as f:
        lines = f.readlines()

    if skip_header:
        lines = lines[1:]

    # Filter empty lines
    lines = [line for line in lines if line.strip()]

    # Ensure process count doesn't exceed data size and CPU core count
    n_processes = min(n_processes, len(lines), cpu_count())

    print(f"Using {n_processes} processes for parallel processing...")

    # Create partial function, pre-fill kwargs
    func_with_kwargs = partial(process_func, **kwargs)

    # Use Pool for parallel processing
    results = []
    with Pool(processes=n_processes) as pool:
        # Use imap_unordered for performance and add progress bar
        with tqdm(total=len(lines), position=0, leave=True,
                  bar_format='{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}') as pbar:
            for result in pool.imap_unordered(func_with_kwargs, lines, chunksize=1):
                if result is not None:
                    results.append(result)
                pbar.update(1)

    # Save results
    if results and output_file:
        with open(output_file, 'w') as f:
            for result in results:
                f.write(str(result) + '\n')
        print(f"Results saved to: {output_file}")

    return results