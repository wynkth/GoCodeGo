from django.http import HttpResponse
from django.utils import timezone

import subprocess
import time
import os
import uuid

from models import Problem, ProblemSolution

def check(request):
    if not request.user.is_authenticated():
        return HttpResponse('')
    if request.is_ajax():
        code_user =  request.POST['code'].strip()
        problem_id = int(request.POST['problem'])

        check_solved = ProblemSolution.objects.get_or_none(problem=problem_id, user=request.user)
        
        if check_solved is None or not check_solved.checked:
            problem_testcode = Problem.objects.get(id=problem_id).test_cases
            code = """package main
                        import "fmt"
                        import "math"
                        import "strconv"

                        var _ = math.E
                        var _ = strconv.IntSize

                        func assert(result interface{}, expected interface{}){
                            if(result != expected){
                                panic(fmt.Sprintf("FAILED! Yielded %v, but expected %v as the result", result, expected))
                            }
                        }\n""" + code_user + "\nfunc main() {\n" + problem_testcode + "\n}"
            res = session_comp_run(code)

            if res == "": # Problem solved
                if check_solved is None:
                    check_solved = ProblemSolution(user=request.user, problem=Problem.objects.get(id=problem_id), solution=code_user, pub_date=timezone.now(), checked=True)
                else:
                    check_solved.checked = True
                    check_solved.solution = code_user
                    check_solved.pub_date = timezone.now()

                check_solved.save()

            return HttpResponse(res)
        else:
            return HttpResponse('You have already solved this problem!')
    else:
        return HttpResponse('')

def save(request):
    if not request.user.is_authenticated():
        return HttpResponse('')
    if request.is_ajax():
        code_user = request.POST['code'].strip()
        problem_id = int(request.POST['problem'])

        solution = ProblemSolution.objects.get_or_none(problem=problem_id, user=request.user)

        if solution is None:
            solution = ProblemSolution(user=request.user, problem=Problem.objects.get(id=problem_id), solution=code_user, pub_date=timezone.now(), checked=False)
            solution.save()
        elif solution is not None and not solution.checked:
            solution.solution = code_user
            solution.pub_date = timezone.now()
            solution.save()    
        else:
            return HttpResponse('You have already solved this problem!')

        return HttpResponse('Save success!')
    else:
        return HttpResponse('')


def compile_go(source_file, target_file):
    # Clean up the target file if it exists
    if os.path.isfile(target_file):
        os.remove(target_file)

    # Run the GO process
    proc = subprocess.Popen(['go', 'build', '-o', target_file, source_file], stderr=subprocess.PIPE)
    out = proc.communicate()[1]

    # Check if the target file has been created successfully
    if not os.path.isfile(target_file):
        return out
    else:
        return True

def run_timeout(program_path, args, timeout_limit):
    # Try running the program
    proc = subprocess.Popen([program_path]+args, stderr=subprocess.PIPE)

    # Wait until the timeout time is reached
    time_elapsed = 0
    while proc.poll() is None and time_elapsed < timeout_limit:
        time.sleep(1)
        time_elapsed += 1

    # Kill the process if it is still alive
    # since it should've finished already
    if proc.poll() is None:
        proc.terminate()
        return 'ERROR: Your code got timed out! You need to Git Gud with GO!'

    # Get the thing if we haven't timed out
    return proc.communicate()[1]

def session_comp_run(input_code):
    session = str(uuid.uuid4())

    # Produce the temporary code file
    code_file = '/tmp/' + session + '.go'
    code = file(code_file, 'w')
    code.write(input_code)
    code.close()

    # Compile the program and delete the code
    executable = '/tmp/' + session
    result = compile_go(code_file, executable)
    os.remove(code_file)

    # If the code didn't compile, put out why
    if isinstance(result, str):
        return result

    # Run the code with a timeout
    # and return its result
    result = run_timeout(executable, [], 5)
    os.remove(executable)

    return result