import asyncio
import json
import time
import logging
from pathlib import Path
import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

from core.llm import engine
from core.controller import Controller
from core.memory import MemorySystem

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stress_test")

class MockWebSocket:
    async def send_json(self, data):
        # Silence output for bulk testing
        pass

QUESTIONS = {
    "CHAT": [
        "What is your favorite hobby and why?", "Describe a perfect weekend.", "If you could live in any country, where would you go?",
        "What makes someone a good friend?", "What is the best way to relax after a long day?", "Tell me about a memorable trip.",
        "Do you prefer books or movies? Why?", "What is a skill everyone should learn?", "What is the meaning of success to you?",
        "What motivates people to work hard?", "How do you handle stress?", "What is the importance of sleep?",
        "How can someone improve communication skills?", "Why do people enjoy music?", "What are the benefits of exercise?",
        "What makes a good leader?", "What are common causes of procrastination?", "How can someone stay productive?",
        "What role does technology play in daily life?", "How do habits shape a person’s life?", "What makes a good teacher?",
        "How do people build confidence?", "What is the best way to learn something new?", "Why do people like storytelling?",
        "What makes a conversation interesting?", "Why do people enjoy games?", "What are some ways to save money?",
        "How can someone improve focus?", "Why is curiosity important?", "What makes a good decision?"
    ],
    "BALANCED": [
        "Explain the difference between a hobby and a profession.", "Why do humans need social interaction?", "What are the pros and cons of remote work?",
        "Explain the concept of supply and demand.", "Why is critical thinking important?", "What causes inflation?",
        "Explain the difference between RAM and storage.", "Why do people procrastinate?", "What makes teamwork effective?",
        "Explain how the internet works in simple terms.", "Why do some businesses fail?", "What are the benefits of reading books?",
        "How does exercise improve mental health?", "What are the risks of social media addiction?", "What makes a good business idea?",
        "Why do people follow trends?", "How does advertising influence behavior?", "What is the difference between data and information?",
        "What makes communication persuasive?", "Why do humans form habits?", "What is the role of education in society?",
        "Why do people fear failure?", "How does memory work?", "What is the importance of curiosity in science?",
        "Why do some technologies succeed while others fail?", "What is the difference between knowledge and wisdom?",
        "Why is time management important?", "What makes a strong argument?", "Why do people enjoy solving puzzles?",
        "What factors influence decision making?"
    ],
    "RESEARCH": [
        "Explain the causes of World War I.", "Describe the history of the internet.", "Explain how artificial intelligence works.",
        "What are the main causes of climate change?", "Explain the evolution of personal computers.", "What is quantum computing?",
        "Explain how vaccines work.", "What are the main renewable energy sources?", "Explain how blockchain technology works.",
        "What are the key principles of machine learning?", "Explain the history of space exploration.", "What are the main causes of economic recessions?",
        "Explain the development of the smartphone industry.", "What are the main programming paradigms?", "Explain how search engines rank websites.",
        "What are the major components of a computer CPU?", "Explain how neural networks learn.", "What are the ethical concerns around AI?",
        "Explain the basics of cryptography.", "What are the main causes of biodiversity loss?", "Explain how GPS works.",
        "What is the history of the Linux operating system?", "Explain the difference between supervised and unsupervised learning.",
        "What are the stages of software development?", "Explain Moore's law.", "What are the major types of databases?",
        "Explain how recommendation systems work.", "What are the risks of artificial general intelligence?", "Explain how cloud computing works.",
        "What are the major trends in AI development?"
    ],
    "LIGHTWEIGHT": [
        "What is the capital of Japan?", "What is 2 + 2?", "Name three programming languages.", "What is the boiling point of water?",
        "What planet is known as the Red Planet?", "What is the square root of 81?", "Name two mammals.", "What is the chemical symbol for gold?",
        "What year did World War II end?", "What is the largest ocean?", "What color do you get by mixing red and blue?",
        "How many days are in a week?", "What is the fastest land animal?", "What is the capital of France?",
        "What is the binary representation of 2?", "What language is used for web styling?", "What is the largest planet in the solar system?",
        "What does CPU stand for?", "What is the opposite of hot?", "What is 10 × 10?", "Name a prime number.",
        "What is the freezing point of water?", "What gas do humans breathe in to survive?", "What is the tallest mountain on Earth?",
        "What device stores long term computer data?", "What is the capital of Mongolia?", "What is 5 squared?",
        "What programming language is known for AI?", "What does HTML stand for?", "What is the speed of light approximately?"
    ],
    "CODER": [
        "Write a Python function to reverse a string.", "Write Python code to check if a number is prime.", "Write a function to calculate factorial.",
        "Write Python code to sort a list.", "Write a function to count words in a sentence.", "Write Python code to remove duplicates from a list.",
        "Write a function to check if a string is a palindrome.", "Write Python code to find the largest number in a list.", "Write a function to generate Fibonacci numbers.",
        "Write Python code to read a text file.", "Write Python code to count vowels in a string.", "Write a function to merge two lists.",
        "Write Python code to calculate average of numbers.", "Write a function to convert Celsius to Fahrenheit.", "Write Python code to shuffle a list.",
        "Write a function to check if a number is even.", "Write Python code to find the length of a list without using len().", "Write a function to remove spaces from a string.",
        "Write Python code to create a dictionary from two lists.", "Write a function to count characters in a string.", "Write Python code to generate random numbers.",
        "Write a function to find the smallest number in a list.", "Write Python code to join strings in a list.", "Write a function to check if two strings are anagrams.",
        "Write Python code to split a sentence into words.", "Write a function to calculate power of a number.", "Write Python code to count list elements.",
        "Write a function to reverse a list.", "Write Python code to create a simple calculator.", "Write a function to check if a number is positive."
    ],
    "MATH": [
        "Solve 45 + 78.", "Solve 120 − 37.", "Multiply 23 × 19.", "Divide 144 by 12.", "Find the square of 16.", "Find the cube of 5.",
        "What is 25 percent of 200?", "Solve 3x + 5 = 20.", "What is the area of a rectangle 5 by 10?", "What is the perimeter of a square with side 8?",
        "What is the square root of 144?", "Convert 0.75 to a fraction.", "What is the average of 10, 20, 30?", "What is 7 factorial?",
        "What is the value of pi approximately?", "Convert 90 degrees to radians.", "Solve x² = 49.", "Find the sum of numbers from 1 to 10.",
        "What is 2⁸?", "What is log10(100)?", "What is the area of a circle radius 7?", "Convert 100 Celsius to Fahrenheit.",
        "What is 15 percent of 80?", "Simplify 8/12.", "Solve 2x − 4 = 10."
    ],
    "REASONING": [
        "If all cats are animals and some animals are pets, are all cats pets?", "A bat and ball cost $1.10. Bat costs $1 more. How much is the ball?", "If you have 3 apples and take away 2, how many do you have?",
        "Which weighs more, 1 kg of steel or 1 kg of feathers?", "If two people take 2 hours to build a wall, how long do four people take?", "A train travels 60 km in 1 hour. How far in 3 hours?",
        "If today is Monday, what day is in 10 days?", "A farmer has 17 sheep. All but 9 die. How many remain?", "If a book costs $12 and you pay $20, what change do you get?",
        "What comes next in the sequence: 2, 4, 8, 16, ?", "A clock shows 3:15. What is the angle between the hands?", "If you double a number and add 10 you get 30. What is the number?",
        "A car travels 100 km using 5 liters fuel. How many liters for 200 km?", "What number is missing: 1, 3, 6, 10, ?", "If a triangle has angles 60, 60, 60 what type is it?",
        "If 5 machines make 5 items in 5 minutes, how long for 100 machines to make 100 items?", "A number is divisible by 2 and 3. What is it divisible by?", "If you flip a coin twice, how many outcomes exist?",
        "If a cube has side length 3, what is its volume?", "If a sequence doubles each step starting from 1, what is the 6th term?", "What is the next number: 3, 9, 27, ?",
        "If you walk north then south same distance, where do you end?", "If a test has 50 questions and you answer 40 correctly, what percent is correct?", "What number comes next: 5, 10, 20, 40, ?",
        "If three angles of a triangle sum to 180, what is the third angle if two are 50 and 60?"
    ]
}

async def run_stress_test():
    ws = MockWebSocket()
    results = []

    logger.info("Starting NexusMind Stress Test (200 Questions)")
    
    total_questions = sum(len(q) for q in QUESTIONS.values())
    count = 0

    for category, questions in QUESTIONS.items():
        logger.info(f"Testing Category: {category} ({len(questions)} questions)")
        for q in questions:
            count += 1
            logger.info(f"[{count}/{total_questions}] Processing: {q[:50]}...")
            
            # Fresh start for each question to avoid state pollution and locks
            memory = MemorySystem()
            controller = Controller(memory)
            
            start = time.time()
            try:
                # Direct call to controller to simulate real usage
                # We expect the router to map these to appropriate profiles
                response = await controller.handle_request(f"stress_test_session_{count}", q, websocket=ws)
                duration = time.time() - start
                
                results.append({
                    "id": count,
                    "question": q,
                    "category": category,
                    "profile_used": response.get("profile"),
                    "response_snippet": response.get("content", "")[:100].replace("\n", " "),
                    "status": "success",
                    "latency": round(duration, 2),
                    "tps": response.get("tps", 0)
                })
            except Exception as e:
                duration = time.time() - start
                logger.error(f"Error processing '{q}': {e}")
                results.append({
                    "id": count,
                    "question": q,
                    "category": category,
                    "status": "error",
                    "error": str(e),
                    "latency": round(duration, 2)
                })
            
            # Incremental save
            try:
                with open("stress_test_results.json", "w") as f:
                    json.dump(results, f, indent=2)
            except Exception as se:
                logger.error(f"Failed to save results: {se}")
            
            # Short sleep to prevent CPU saturation
            await asyncio.sleep(0.05)

    logger.info(f"Stress test complete. Results saved to stress_test_results.json")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
