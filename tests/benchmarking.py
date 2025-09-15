"""
Improved benchmarking script for Ollama (local), OpenRouter, and Groq models.

Features:
- Enhanced error handling and debugging
- Better API endpoint compatibility
- Improved response parsing
- More robust connectivity checks
- Better logging and progress tracking

Usage:
  1. Fill in API keys and endpoints below (OPENROUTER_API_KEY, GROQ_API_KEY).
  2. Ensure Ollama local server is running (default: http://localhost:11434/api/generate)
  3. Install dependencies: pip install aiohttp tqdm pandas
  4. Run: python improved_benchmark.py
"""

import asyncio
import aiohttp
import time
import json
import csv
import os
import sys
import textwrap
import logging
from tqdm.asyncio import tqdm
from typing import Dict, Any, List, Tuple
import subprocess
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIG ====================
# Ollama (local)
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://172.29.77.140:11434/api/generate')

# OpenRouter
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_URL = os.getenv('OPENROUTER_URL', 'https://openrouter.ai/api/v1/chat/completions')

# Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_URL = os.getenv('GROQ_URL', 'https://api.groq.com/openai/v1/chat/completions')

# Models to test (editable)
MODELS = {
    'ollama_gpt-oss': {
        'backend': 'ollama',
        'model': 'gpt-oss:latest',
        'enabled': True
    },
    'ollama_magistral': {
        'backend': 'ollama',
        'model': 'magistral:latest',
        'enabled': True
    },
    'openrouter_deepseekv3': {
        'backend': 'openrouter',
        'model': 'deepseek/deepseek-chat',
        'enabled': bool(OPENROUTER_API_KEY)
    },
    'groq_llama3.3': {
        'backend': 'groq',
        'model': 'llama-3.1-70b-versatile',
        'enabled': bool(GROQ_API_KEY)
    }
}

# Benchmark sample sizes
SAMPLES = {
    'mmlu': 4,
    'gsm8k': 4,
    'humaneval': 3
}

# Output
OUT_CSV = 'benchmark_results.csv'

# ==================== BENCHMARK DATA ====================
MMLU_SAMPLES = [
    ("What is the capital of France?",
     ['A) Rome', 'B) Madrid', 'C) Paris', 'D) Berlin'], 'C'),
    ("Which gas is most abundant in Earth's atmosphere?",
     ['A) Oxygen', 'B) Nitrogen', 'C) Carbon Dioxide', 'D) Argon'], 'B'),
    ("Which element has the atomic number 6?",
     ['A) Carbon', 'B) Oxygen', 'C) Nitrogen', 'D) Helium'], 'A'),
    ("Who wrote 'Pride and Prejudice'?",
     ['A) Emily Bronte', 'B) Charles Dickens', 'C) Jane Austen', 'D) Mary Shelley'], 'C'),
]

GSM8K_SAMPLES = [
    ("If 5 people share 24 apples equally, how many apples does each person get?", 4.8),
    ("A train travels 60 miles in 1.5 hours. What's its average speed in mph?", 40.0),
    ("What is 15% of 200?", 30.0),
    ("If you have 3 boxes with 4, 5, and 6 candies, how many candies total?", 15.0),
]

HUMANEVAL_SAMPLES = [
    (
        "Return the sum of a list of integers.\nFunction signature: def solve(nums: list) -> int:",
        textwrap.dedent('''
        def _test(user_func):
            assert user_func([1,2,3]) == 6
            assert user_func([]) == 0
            assert user_func([-1,1]) == 0
        ''')
    ),
    (
        "Return True if a string is palindrome (case-insensitive, ignore non-alnum).\nFunction: def solve(s: str) -> bool:",
        textwrap.dedent('''
        def _test(user_func):
            assert user_func('A man, a plan, a canal: Panama') is True
            assert user_func('hello') is False
        ''')
    ),
    (
        "Given two integers a and b, return a**b.\nFunction: def solve(a:int,b:int)->int:",
        textwrap.dedent('''
        def _test(user_func):
            assert user_func(2,3) == 8
            assert user_func(5,0) == 1
        ''')
    ),
]

# ==================== CONNECTIVITY CHECKS ====================
async def check_connectivity():
    """Check if services are reachable before starting benchmarks."""
    logger.info("Checking service connectivity...")
    
    # Check Ollama
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Try a simple ping to Ollama
            async with session.get(OLLAMA_URL.replace('/api/generate', '/api/tags'), timeout=5) as resp:
                if resp.status == 200:
                    logger.info("✓ Ollama server is reachable")
                else:
                    logger.warning(f"⚠ Ollama server responded with status {resp.status}")
    except Exception as e:
        logger.error(f"✗ Ollama server unreachable: {e}")
    
    # Check OpenRouter
    if OPENROUTER_API_KEY:
        try:
            headers = {'Authorization': f'Bearer {OPENROUTER_API_KEY}'}
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('https://openrouter.ai/api/v1/models', headers=headers, timeout=10) as resp:
                    if resp.status in [200, 401]:  # 401 means we reached the server
                        logger.info("✓ OpenRouter API is reachable")
                    else:
                        logger.warning(f"⚠ OpenRouter API responded with status {resp.status}")
        except Exception as e:
            logger.error(f"✗ OpenRouter API unreachable: {e}")
    
    # Check Groq
    if GROQ_API_KEY:
        try:
            headers = {'Authorization': f'Bearer {GROQ_API_KEY}'}
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get('https://api.groq.com/openai/v1/models', headers=headers, timeout=10) as resp:
                    if resp.status in [200, 401]:  # 401 means we reached the server
                        logger.info("✓ Groq API is reachable")
                    else:
                        logger.warning(f"⚠ Groq API responded with status {resp.status}")
        except Exception as e:
            logger.error(f"✗ Groq API unreachable: {e}")

# ==================== API HELPERS ====================

async def call_ollama(session: aiohttp.ClientSession, model: str, prompt: str, max_tokens=512) -> Dict[str, Any]:
    """Call Ollama API with improved error handling."""
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {
            'num_predict': max_tokens,
            'temperature': 0.0
        }
    }
    
    try:
        start = time.perf_counter()
        async with session.post(OLLAMA_URL, json=payload, timeout=120) as resp:
            ttb = time.perf_counter() - start
            
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"Ollama API error {resp.status}: {error_text}")
                return {'status': resp.status, 'ttb': ttb, 'total': ttb, 'error': error_text}
            
            response_data = await resp.json()
            total = time.perf_counter() - start
            
            return {
                'status': resp.status,
                'ttb': ttb,
                'total': total,
                'response': response_data
            }
            
    except asyncio.TimeoutError:
        return {'status': 408, 'ttb': 0, 'total': 120, 'error': 'Request timeout'}
    except Exception as e:
        logger.error(f"Ollama API call failed: {e}")
        return {'status': 500, 'ttb': 0, 'total': 0, 'error': str(e)}

async def call_openrouter(session: aiohttp.ClientSession, model: str, prompt: str, max_tokens=512) -> Dict[str, Any]:
    """Call OpenRouter API with improved error handling."""
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:3000',
        'X-Title': 'Benchmark Script'
    }
    
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0
    }
    
    try:
        start = time.perf_counter()
        async with session.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120) as resp:
            ttb = time.perf_counter() - start
            
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"OpenRouter API error {resp.status}: {error_text}")
                return {'status': resp.status, 'ttb': ttb, 'total': ttb, 'error': error_text}
            
            response_data = await resp.json()
            total = time.perf_counter() - start
            
            return {
                'status': resp.status,
                'ttb': ttb,
                'total': total,
                'response': response_data
            }
            
    except asyncio.TimeoutError:
        return {'status': 408, 'ttb': 0, 'total': 120, 'error': 'Request timeout'}
    except Exception as e:
        logger.error(f"OpenRouter API call failed: {e}")
        return {'status': 500, 'ttb': 0, 'total': 0, 'error': str(e)}

async def call_groq(session: aiohttp.ClientSession, model: str, prompt: str, max_tokens=512) -> Dict[str, Any]:
    """Call Groq API with improved error handling."""
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.0
    }
    
    try:
        start = time.perf_counter()
        async with session.post(GROQ_URL, headers=headers, json=payload, timeout=120) as resp:
            ttb = time.perf_counter() - start
            
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"Groq API error {resp.status}: {error_text}")
                return {'status': resp.status, 'ttb': ttb, 'total': ttb, 'error': error_text}
            
            response_data = await resp.json()
            total = time.perf_counter() - start
            
            return {
                'status': resp.status,
                'ttb': ttb,
                'total': total,
                'response': response_data
            }
            
    except asyncio.TimeoutError:
        return {'status': 408, 'ttb': 0, 'total': 120, 'error': 'Request timeout'}
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return {'status': 500, 'ttb': 0, 'total': 0, 'error': str(e)}

# Dispatcher with better error handling
async def call_model(session: aiohttp.ClientSession, model_key: str, prompt: str) -> Dict[str, Any]:
    """Call model with proper error handling."""
    cfg = MODELS[model_key]
    backend = cfg['backend']
    model_name = cfg['model']
    
    try:
        if backend == 'ollama':
            return await call_ollama(session, model_name, prompt)
        elif backend == 'openrouter':
            return await call_openrouter(session, model_name, prompt)
        elif backend == 'groq':
            return await call_groq(session, model_name, prompt)
        else:
            return {'status': 500, 'ttb': 0, 'total': 0, 'error': f'Unknown backend: {backend}'}
    except Exception as e:
        logger.error(f"Model call failed for {model_key}: {e}")
        return {'status': 500, 'ttb': 0, 'total': 0, 'error': str(e)}

# ==================== RESPONSE PARSING ====================

def extract_text_from_response(model_key: str, resp: Dict[str, Any]) -> str:
    """Extract text from API response with improved parsing."""
    if 'error' in resp:
        return f"ERROR: {resp['error']}"
    
    data = resp.get('response', {})
    
    if not isinstance(data, dict):
        return str(data)
    
    # Handle different response formats
    try:
        # OpenRouter/Groq format: choices[0].message.content
        if 'choices' in data and isinstance(data['choices'], list) and data['choices']:
            choice = data['choices'][0]
            if isinstance(choice, dict):
                if 'message' in choice and isinstance(choice['message'], dict):
                    content = choice['message'].get('content', '')
                    if content:
                        return content
                if 'text' in choice:
                    return choice['text']
        
        # Ollama format: response field
        if 'response' in data:
            return str(data['response'])
        
        # Ollama alternative: output field
        if 'output' in data:
            return str(data['output'])
        
        # Direct text field
        if 'text' in data:
            return str(data['text'])
        
        # If we have raw response
        if 'raw' in data:
            return str(data['raw'])
        
    except Exception as e:
        logger.error(f"Error extracting text from response: {e}")
        logger.debug(f"Response data: {data}")
    
    return str(data)

# ==================== SCORING FUNCTIONS ====================

def score_mmlu_answer(pred: str, correct: str) -> bool:
    """Score MMLU answer with better extraction."""
    if not pred or "ERROR:" in pred:
        return False
    
    pred_up = pred.upper().strip()
    correct_up = correct.upper().strip()
    
    # Direct match
    if correct_up in pred_up:
        return True
    
    # Look for letter patterns
    import re
    # Find single letters that might be answers
    letters = re.findall(r'\b([A-D])\b', pred_up)
    if letters and letters[0] == correct_up:
        return True
    
    # Look for "Answer: X" or similar patterns
    answer_match = re.search(r'(?:answer|choice)[\s:]*([A-D])', pred_up)
    if answer_match and answer_match.group(1) == correct_up:
        return True
    
    return False

def score_gsm8k_answer(pred: str, correct: float, tol=1e-2) -> bool:
    """Score GSM8K answer with better number extraction."""
    if not pred or "ERROR:" in pred:
        return False
    
    # Try to extract numbers from the prediction
    import re
    
    # Look for decimal numbers
    numbers = re.findall(r'-?\d+\.?\d*', pred)
    
    for num_str in numbers:
        try:
            val = float(num_str)
            if abs(val - correct) <= max(tol, abs(correct) * 0.02):
                return True
        except ValueError:
            continue
    
    return False

def score_humaneval_solution(code: str, test_code: str, timeout_sec=5) -> Tuple[bool, str]:
    """Score HumanEval solution with better code extraction."""
    if not code or "ERROR:" in code:
        return False, "No valid code provided"
    
    # Extract code from markdown if present
    if '```python' in code:
        parts = code.split('```python')
        if len(parts) > 1:
            code_part = parts[1].split('```')[0]
            code = code_part.strip()
    elif '```' in code:
        parts = code.split('```')
        if len(parts) >= 3:
            code = parts[1].strip()
    
    # Create test wrapper
    wrapper = f"""
import sys
import traceback

{code}

# Bind solve function
try:
    user_func = solve
except NameError:
    print('ERROR: Function "solve" not found')
    sys.exit(1)
except Exception as e:
    print(f'ERROR: Could not bind solve function: {{e}}')
    sys.exit(1)

{test_code}

if __name__ == '__main__':
    try:
        _test(user_func)
        print('PASS')
    except AssertionError as e:
        print(f'FAIL: Assertion error: {{e}}')
    except Exception as e:
        print(f'ERROR: {{type(e).__name__}}: {{e}}')
        traceback.print_exc()
"""
    
    try:
        proc = subprocess.run(
            [sys.executable, '-c', wrapper],
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
        output = proc.stdout + proc.stderr
        success = 'PASS' in output and proc.returncode == 0
        return success, output
        
    except subprocess.TimeoutExpired:
        return False, 'TIMEOUT: Code execution took too long'
    except Exception as e:
        return False, f'EXECUTION_ERROR: {e}'

# ==================== BENCHMARK TASKS ====================

async def run_mmlu(session: aiohttp.ClientSession, model_key: str) -> List[Dict[str, Any]]:
    """Run MMLU benchmark."""
    results = []
    logger.info(f"Running MMLU for {model_key}")
    
    for i, (question, choices, correct) in enumerate(MMLU_SAMPLES[:SAMPLES['mmlu']]):
        logger.info(f"  MMLU {i+1}/{SAMPLES['mmlu']}")
        
        prompt = (f"Answer the multiple choice question by selecting the correct letter (A, B, C, or D).\n\n"
                 f"Question: {question}\n\n"
                 f"Choices:\n" + '\n'.join(choices) + "\n\n"
                 f"Answer:")
        
        resp = await call_model(session, model_key, prompt)
        text = extract_text_from_response(model_key, resp)
        correct_flag = score_mmlu_answer(text, correct)
        
        results.append({
            'dataset': 'MMLU',
            'question': question,
            'model': model_key,
            'response': text[:200],  # Truncate long responses
            'correct': correct_flag,
            'expected': correct,
            'ttb': resp.get('ttb', 0),
            'total': resp.get('total', 0),
            'status': resp.get('status', 0)
        })
        
    return results

async def run_gsm8k(session: aiohttp.ClientSession, model_key: str) -> List[Dict[str, Any]]:
    """Run GSM8K benchmark."""
    results = []
    logger.info(f"Running GSM8K for {model_key}")
    
    for i, (question, answer) in enumerate(GSM8K_SAMPLES[:SAMPLES['gsm8k']]):
        logger.info(f"  GSM8K {i+1}/{SAMPLES['gsm8k']}")
        
        prompt = (f"Solve this math problem step by step and provide the final numeric answer.\n\n"
                 f"Problem: {question}\n\n"
                 f"Solution:")
        
        resp = await call_model(session, model_key, prompt)
        text = extract_text_from_response(model_key, resp)
        correct_flag = score_gsm8k_answer(text, answer)
        
        results.append({
            'dataset': 'GSM8K',
            'question': question,
            'model': model_key,
            'response': text[:200],
            'correct': correct_flag,
            'expected': answer,
            'ttb': resp.get('ttb', 0),
            'total': resp.get('total', 0),
            'status': resp.get('status', 0)
        })
        
    return results

async def run_humaneval(session: aiohttp.ClientSession, model_key: str) -> List[Dict[str, Any]]:
    """Run HumanEval benchmark."""
    results = []
    logger.info(f"Running HumanEval for {model_key}")
    
    for i, (description, test_code) in enumerate(HUMANEVAL_SAMPLES[:SAMPLES['humaneval']]):
        logger.info(f"  HumanEval {i+1}/{SAMPLES['humaneval']}")
        
        prompt = (f"Write a Python function that solves the following problem. "
                 f"Return only the function code, no explanation.\n\n"
                 f"{description}\n\n"
                 f"Code:")
        
        resp = await call_model(session, model_key, prompt)
        text = extract_text_from_response(model_key, resp)
        passed, output = score_humaneval_solution(text, test_code)
        
        results.append({
            'dataset': 'HumanEval',
            'question': description,
            'model': model_key,
            'response': text[:500],
            'passed': passed,
            'test_output': output[:200],
            'ttb': resp.get('ttb', 0),
            'total': resp.get('total', 0),
            'status': resp.get('status', 0)
        })
        
    return results

async def run_all_for_model(session: aiohttp.ClientSession, model_key: str) -> List[Dict[str, Any]]:
    """Run all benchmarks for a single model."""
    results = []
    
    try:
        results.extend(await run_mmlu(session, model_key))
        results.extend(await run_gsm8k(session, model_key))
        results.extend(await run_humaneval(session, model_key))
    except Exception as e:
        logger.error(f"Error running benchmarks for {model_key}: {e}")
        traceback.print_exc()
    
    return results

# ==================== MAIN ====================

async def main():
    """Main benchmark execution."""
    logger.info("Starting benchmark suite...")
    
    # Check connectivity first
    await check_connectivity()
    
    # Filter enabled models
    enabled_models = {k: v for k, v in MODELS.items() if v.get('enabled', True)}
    logger.info(f"Benchmarking {len(enabled_models)} models: {list(enabled_models.keys())}")
    
    if not enabled_models:
        logger.error("No models enabled for benchmarking!")
        return
    
    results = []
    timeout = aiohttp.ClientTimeout(total=180)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for model_key in enabled_models.keys():
            logger.info(f'\n=== Benchmarking {model_key} ===')
            try:
                model_results = await run_all_for_model(session, model_key)
                results.extend(model_results)
                logger.info(f"Completed {model_key}: {len(model_results)} tests")
            except Exception as e:
                logger.error(f'Error benchmarking {model_key}: {e}')
                traceback.print_exc()

    # Save results to CSV
    if results:
        keys = set()
        for row in results:
            keys.update(row.keys())
        keys = sorted(list(keys))
        
        with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        
        logger.info(f'Results saved to {OUT_CSV}')
    else:
        logger.warning("No results to save!")

    # Print summary
    print_summary(results)

def print_summary(results: List[Dict[str, Any]]):
    """Print benchmark summary."""
    from collections import defaultdict
    
    if not results:
        print("\n=== NO RESULTS ===")
        return
    
    summary = defaultdict(lambda: {
        'total': 0, 'mmlu_correct': 0, 'gsm8k_correct': 0, 'humaneval_passed': 0,
        'mmlu_total': 0, 'gsm8k_total': 0, 'humaneval_total': 0,
        'ttb_sum': 0.0, 'total_sum': 0.0, 'errors': 0
    })
    
    for row in results:
        model = row['model']
        dataset = row['dataset']
        
        summary[model]['total'] += 1
        summary[model]['ttb_sum'] += float(row.get('ttb', 0) or 0)
        summary[model]['total_sum'] += float(row.get('total', 0) or 0)
        
        if row.get('status', 200) != 200:
            summary[model]['errors'] += 1
        
        if dataset == 'MMLU':
            summary[model]['mmlu_total'] += 1
            if row.get('correct'):
                summary[model]['mmlu_correct'] += 1
        elif dataset == 'GSM8K':
            summary[model]['gsm8k_total'] += 1
            if row.get('correct'):
                summary[model]['gsm8k_correct'] += 1
        elif dataset == 'HumanEval':
            summary[model]['humaneval_total'] += 1
            if row.get('passed'):
                summary[model]['humaneval_passed'] += 1

    print('\n' + '='*50)
    print('BENCHMARK SUMMARY')
    print('='*50)
    
    for model, stats in summary.items():
        print(f'\n{model}:')
        print(f"  Total samples: {stats['total']}")
        print(f"  Errors: {stats['errors']}")
        
        if stats['total'] > 0:
            avg_ttb = stats['ttb_sum'] / stats['total']
            avg_total = stats['total_sum'] / stats['total']
            print(f"  Avg time-to-first-byte: {avg_ttb:.3f}s")
            print(f"  Avg total time: {avg_total:.3f}s")
        
        if stats['mmlu_total'] > 0:
            mmlu_acc = stats['mmlu_correct'] / stats['mmlu_total']
            print(f"  MMLU accuracy: {stats['mmlu_correct']}/{stats['mmlu_total']} ({mmlu_acc:.1%})")
        
        if stats['gsm8k_total'] > 0:
            gsm8k_acc = stats['gsm8k_correct'] / stats['gsm8k_total']
            print(f"  GSM8K accuracy: {stats['gsm8k_correct']}/{stats['gsm8k_total']} ({gsm8k_acc:.1%})")
        
        if stats['humaneval_total'] > 0:
            he_acc = stats['humaneval_passed'] / stats['humaneval_total']
            print(f"  HumanEval pass rate: {stats['humaneval_passed']}/{stats['humaneval_total']} ({he_acc:.1%})")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Benchmark interrupted by user")
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        traceback.print_exc()