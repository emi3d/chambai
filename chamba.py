import os
import logging
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate
from playwright.sync_api import sync_playwright
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('application_debug.log')
    ]
)
logger = logging.getLogger(__name__)


load_dotenv()

class OpenRouterClient:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1", 
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        logger.debug("OpenRouterClient initialized with API key")
    
    def analyze_fit(self, cv: str, job: dict) -> dict:
        """Analyze job fit with detailed logging"""
        try:
            #logger.info(f"Starting analysis for job: {job.get('title', 'Unknown')}")
            #logger.debug(f"Job details: {json.dumps(job, indent=2)}")
            
            prompt=f"""
            You are an expert recruiter and profesional coach. +25 years of experience.
            Analyze job fit:

            Ideal Job: Find me jobs that helps me grow my career into f1 as an engineer related to software in the near future.
            CV: {cv[:2000]}
            Extract for each job:
            Job Title: title
            Company: company
            Location: location
            Job Description: description

            And match the score 0-10 for compatibility with cv and Ideal job.

            Respond ONLY with JSON: {{"match_score": "number between 0 and 10", "should_apply": "bool", "explanation": "brief explanation of why this is a good/bad fit in maximum 12 words."}}
            here are the jobs:
            {json.dumps(job, indent=2)}
            """
            #print(prompt2)
            #logger.debug(f"Generated prompt:\n{prompt}")

            response = self.client.chat.completions.create(
                model="google/gemini-2.0-pro-exp-02-05:free",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            logger.debug(f"OpenRouter response: {response}")
            analysis = json.loads(response.choices[0].message.content)
            logger.info(f"Analysis complete.")
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenRouter response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in analyze_fit: {str(e)}")
            raise

class LinkedInAgent:
    def __init__(self):
        self.llm = OpenRouterClient()
        self.recommendations = []
        logger.info("LinkedInAgent initialized")

    def _log_recommendation(self, recommendation: dict):
        """Structured logging for recommendations"""
        logger.info(
            "Job recommendation",
            extra={
                "job_id": recommendation.get("job_id"),
                "title": recommendation.get("title"),
                "company": recommendation.get("company"),
                "match_score": recommendation.get("match_score")
            }
        )

    def run(self, cv_text: str):
        
        try:
            logger.info("Starting job analysis process")
            logger.debug(f"CV text length: {len(cv_text)} characters")

            if not os.path.exists("job_listings.json"):
                logger.error("job_listings.json file not found")
                raise FileNotFoundError("job_listings.json not found")

            with open("job_listings.json", "r", encoding="utf-8") as f:
                job_listings = json.load(f)
                logger.info(f"Loaded {len(job_listings)} job listings")
            
            unique_jobs = []
            seen_job_ids = set()

            for job in job_listings:
                job_id = job.get("job_id")
                if job_id and job_id not in seen_job_ids:
                    unique_jobs.append(job)
                    seen_job_ids.add(job_id)
            #evalua chambas de 10 en 10
            chunk_size = 10
            trabajos = set()
            for i in range(0, len(unique_jobs), chunk_size):
                chunk = job_listings[i:i+chunk_size]
                logger.info(f"Evaluating jobs {i+1} to {min(i+chunk_size, len(job_listings))} in one chunk")
                analysis_chunk = self.llm.analyze_fit(cv_text, json.dumps(chunk, indent=2))
                
                if not isinstance(analysis_chunk, list):
                    analysis_chunk = [analysis_chunk]
                
                for job, analysis in zip(chunk, analysis_chunk):
                    if analysis.get("should_apply", False):
                        recommendation = {
                            "job_id": job.get("job_id"),
                            "title": job.get("title", "Unknown"),
                            "company": job.get("company", "Unknown"),
                            "location": job.get("location"),
                            "job_url": job.get("job_url"),
                            "match_score": analysis.get("match_score"),
                            "explanation": analysis.get("explanation")
                        }
                        self.recommendations.append(recommendation)
                        self._log_recommendation(recommendation)
                        logger.debug(f"Full recommendation details:\n{json.dumps(recommendation, indent=2)}")
                    else:
                        logger.info(f"Skipping job: {job.get('title', 'Unknown')} (Not recommended)")
            

            logger.info(f"Generated {len(self.recommendations)} recommendations")
            with open("applications.json", "w", encoding="utf-8") as f:
                json.dump(self.recommendations, f, indent=2)
                logger.info("Saved recommendations to applications.json")

            return self.recommendations

        except Exception as e:
            logger.error(f"Fatal error in run method: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        
        log_level = "DEBUG" #os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(log_level)
        
        logger.info("Starting application")
        
        if not os.path.exists("my_cv.txt"):
            logger.error("my_cv.txt file not found")
            raise FileNotFoundError("my_cv.txt not found")

        with open("my_cv.txt", "r", encoding="utf-8") as f:
            cv_text = f.read()
            logger.debug("Loaded CV text from file")

        agent = LinkedInAgent()
        results = agent.run(cv_text)
        
        logger.info("Process completed successfully")
        logger.debug(f"Final recommendations:\n{json.dumps(results, indent=2)}")

    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        raise