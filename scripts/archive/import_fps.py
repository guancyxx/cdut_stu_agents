#!/usr/bin/env python3
"""
QDUOJ FPS Import Script using Django Management Command
Run this script inside the QDUOJ backend container
"""
import os
import sys

# Add Django app path
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oj.settings')

import django
django.setup()

from fps.parser import FPSParser, FPSHelper
from problem.models import Problem, ProblemTag
from options.options import SysOptions
from utils.constants import Difficulty
from utils.shortcuts import rand_str
from account.models import User
from django.conf import settings
from django.db import transaction

def import_fps_file(fps_file_path, creator_username='root'):
    """Import problems from FPS XML file"""
    
    # Get creator user
    try:
        creator = User.objects.get(username=creator_username)
    except User.DoesNotExist:
        print(f"Error: User '{creator_username}' not found")
        return 0
    
    # Parse FPS file
    print(f"Parsing FPS file: {fps_file_path}")
    try:
        parser = FPSParser(fps_file_path)
        problems = parser.parse()
        print(f"Found {len(problems)} problems")
    except Exception as e:
        print(f"Error parsing FPS file: {e}")
        return 0
    
    # Import problems
    helper = FPSHelper()
    imported_count = 0
    
    with transaction.atomic():
        for idx, problem_data in enumerate(problems, 1):
            try:
                # Create test case directory
                test_case_id = rand_str()
                test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
                os.mkdir(test_case_dir)
                
                # Save test cases
                test_case_info = helper.save_test_case(problem_data, test_case_dir)
                
                # Prepare test case scores
                score = []
                for item in test_case_info["test_cases"].values():
                    score.append({
                        "score": 0,
                        "input_name": item["input_name"],
                        "output_name": item.get("output_name")
                    })
                
                # Process images
                problem_data = helper.save_image(
                    problem_data,
                    settings.UPLOAD_DIR,
                    settings.UPLOAD_PREFIX
                )
                
                # Calculate time limit (convert to ms)
                if problem_data["time_limit"]["unit"] == "ms":
                    time_limit = problem_data["time_limit"]["value"]
                else:
                    time_limit = problem_data["time_limit"]["value"] * 1000
                
                # Prepare template code
                template = {}
                prepend = {}
                append = {}
                
                for t in problem_data.get("prepend", []):
                    prepend[t["language"]] = t["code"]
                
                for t in problem_data.get("append", []):
                    append[t["language"]] = t["code"]
                
                for t in problem_data.get("template", []):
                    lang = t["language"]
                    our_lang = "Python3" if lang == "Python" else lang
                    template_base = "{}\n{}\n{}"
                    template[our_lang] = template_base.format(
                        prepend.get(lang, ""),
                        t["code"],
                        append.get(lang, "")
                    )
                
                # Check if SPJ
                spj = problem_data.get("spj") is not None
                spj_code = problem_data["spj"]["code"] if spj else None
                spj_language = problem_data["spj"]["language"] if spj else None
                
                # Create problem
                problem = Problem.objects.create(
                    _id=f"fps-{rand_str(4)}",
                    title=problem_data["title"],
                    description=problem_data.get("description", ""),
                    input_description=problem_data.get("input", ""),
                    output_description=problem_data.get("output", ""),
                    hint=problem_data.get("hint", ""),
                    test_case_score=score,
                    time_limit=time_limit,
                    memory_limit=problem_data["memory_limit"]["value"],
                    samples=problem_data.get("samples", []),
                    template=template,
                    rule_type="ACM",
                    source=problem_data.get("source", "FPS Import"),
                    spj=spj,
                    spj_code=spj_code,
                    spj_language=spj_language,
                    spj_version=rand_str(8) if spj else "",
                    visible=False,
                    languages=SysOptions.language_names,
                    created_by=creator,
                    difficulty=Difficulty.MID,
                    test_case_id=test_case_id
                )
                
                imported_count += 1
                print(f"[{imported_count}/{len(problems)}] Imported: {problem.title} (ID: {problem._id})")
                
            except Exception as e:
                print(f"Error importing problem {idx}: {e}")
                import traceback
                traceback.print_exc()
    
    return imported_count

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_fps.py <fps_file_path>")
        sys.exit(1)
    
    fps_file = sys.argv[1]
    
    if not os.path.exists(fps_file):
        print(f"Error: File not found: {fps_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("QDUOJ FPS Import Tool")
    print("=" * 60)
    print()
    
    count = import_fps_file(fps_file)
    
    print()
    print("=" * 60)
    print(f"Import completed! Successfully imported {count} problems")
    print("=" * 60)
