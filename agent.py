import openai
import os
import logging
import datetime
import csv

# API Key
if "OPENAI_API_KEY" not in os.environ:
    raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
openai.api_key = os.environ["OPENAI_API_KEY"] # store api key in env var

class Agent: # Base agent class
    # For session logging of LLM prompts/responses
    session_id = None
    conversation_log = None
    log_folder = "logs/logs"
    conversation_folder = "logs/conversation"

    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger("agent")
        self.configure_logger() # Initialize logger for debugging
        
        # Initialize session-specific conversation log if not already set
        if Agent.session_id is None:
            self.reset()

    @staticmethod
    def reset(): # Reset session ID and reinitializes log
        Agent.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        Agent.conversation_log = os.path.join(Agent.conversation_folder, f"conversation_log_{Agent.session_id}.csv")
        os.makedirs(Agent.conversation_folder, exist_ok=True)
        with open(Agent.conversation_log, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Agent", "Role", "Message"])

        # Log new session
        logger = logging.getLogger("agent")
        logger.info(f"--- New Session Started: {Agent.session_id} ---")

    def configure_logger(self): # Configure logging
        os.makedirs(Agent.log_folder, exist_ok=True)
        
        if not self.logger.hasHandlers():
            # Set logging level and define the log format
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            # File handler for logging to a file
            log_file = os.path.join(Agent.log_folder, "agent.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # Console handler for logging to the console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def log_conversation(self, role, message): # Append conversation log
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(Agent.conversation_log, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, self.name, role, message])

    def call_api(self, sys_msg, usr_msg): # Calls openAI API
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": usr_msg}
                ],
                max_tokens=2048, # Add args feature later
                temperature=1,
                top_p=1.0,
                frequency_penalty=0.05,
                presence_penalty=0.05
            )
            output = response.choices[0].message.content.strip()
            self.logger.info("Received response: %s", output) # Log for debugging
            # Log prompts and response for illustrative purposes
            self.log_conversation("system", sys_msg)
            self.log_conversation("user", usr_msg)
            self.log_conversation("assistant", output)
            return output
        except Exception as e:
            self.logger.error(f"Error in API call: {e}")
            return None

    def process(self, *args, **kwargs):
        raise NotImplementedError("Implement in the agent subclasses")
    
class SummarizationAgent(Agent): # Summarization Agent
    def __init__(self):
        super().__init__("Summarization Agent")
        self.summaries = []
    
    def process(self, article, feedback=None):
        # Log the start of the summarization process
        self.logger.info("Starting summarization...")
        
        # Prompts
        if feedback: # Refine summary based on feedback from Personalization Agent
            self.logger.debug("Refining summary based on feedback...")
            sys_msg = (
                "You are a summarization agent who summarizes a news article based on feedback about previous summaries."
                "You should use the feedback to produce a more relevant summary. The summary should be three sentences long. Try to include facts from the article."
            )
            # Try to include facts from the article. -- remove if want more speculative/inferred response and less factual
            usr_msg = f"Generate a summary on the following  by taking into account this feedback: \n {feedback}.  \nArticle: \n {article}"
        else: # Initial zero-shot summary
            self.logger.debug("Generating initial summary...")
            sys_msg = "You are a summarization agent who summarizes news articles in three sentences."
            usr_msg = f"Please summarize the following article: {article}"
        
        summary = self.call_api(sys_msg, usr_msg) # Generate summary based on prompts
        if summary:
            self.logger.info("Summary generated successfully.")
            self.summaries.append(summary)
        else:
            self.logger.error("Failed to generate summary.")
        
        return summary

class PersonalizationAgent(Agent): # Personalization Agent
    def __init__(self, profile):
        super().__init__("Personalization Agent")
        self.profile = profile # List of keywords (How will we get this? Survey, reading history?, ideally with usage)
        self.persona = self.generate_persona()
    
    def generate_persona(self):
        # Create a persona based on profile keywords
        sys_msg = (
                    "You are an assistant that generates a user persona based on their background knowledge. You will be given a list of keyphrases."
                    "Describe the user's familiarity with each topic, and indicate whether they are an expert, moderately informed, or a beginner."
                    )
        usr_msg = (
            f"Create a user persona based on the following keywords: {', '.join(self.profile)}. "
                )
        persona_description = self.call_api(sys_msg, usr_msg)
        self.logger.info(f"Generated persona: {persona_description}")
        return persona_description
    
    def generate_feedback(self, summary):
        # Use the persona and summary to generate feedback about the summary
        sys_msg = (
            "You are a personalization assistant who provides feedback to tailor an article summary "
            "based on the user's background knowledge and familiarity level."
            "We're tailoring the summary to the user's knowledge level, not interpreting or analyzing the article."
            "The feedback should not diverge from the context of a summary.\n"
            "Please do the following: "
            "\n 1. Suggest whether the user would need more context, less context, or if the summary is appropriate as is and why."
            "\n 2. Provide itemized specific feedback on which details to add or remove."
        )
        usr_msg = (
            f"Based on this persona: '{self.persona}', analyze the following summary: '{summary}' and provide feedback. "
        )
        feedback = self.call_api(sys_msg, usr_msg)
        self.logger.info(f"Generated feedback: {feedback}")
        return feedback

    def process(self, summary):
        # Generate and return feedback based on the summary produced by Summarization Agent
        feedback = self.generate_feedback(summary)
        return feedback

#################################################   WIP    #################################################

class ArbiterAgent(Agent): # Arbiter Agent
    def __init__(self):
        super().__init__("Arbiter Agent")

    def check_bias(self, article, summary):
        # Check bias
        raise NotImplementedError("To be completed.")
    
    def check_truth(self, article, summary):
        # Check for preservation of truth/facts
        sys_msg = (
            "You are an assistant that evaluates whether a summary preserves the key information from an article. Please do the following: \n"
            "1. If the summary is accurate and reflects the main points of the article, respond with 'Arbiter=1'. Otherwise 'Arbiter=0'\n"
            "2. If there are inaccuracies, explain what is incorrect.\n"
            "It is okay if the article adds or removes context regarding topics in the article. It doesn't have to be perfect, allow some flexibility."
        )
        # "2. If there are inaccuracies or missing information, explain what is incorrect or missing.\n"
        usr_msg = (
            f"Here is the original article:\n\n{article}\n\n"
            f"Here is the summary:\n\n{summary}\n\n"
            "Please check the summary given the article."
        )

        try:
            response = self.call_api(sys_msg, usr_msg)

            if 'Arbiter=1' in response:
                return True, "Acceptable"
            else:
                return False, response
        except Exception as e:
            self.logger.error(f"Error in summary verification: {e}")
            return False, "Error during verification"
    
    def generate_keyphrases(self):
        # Generate keyphrases for dynamic user profiles
        raise NotImplementedError("To be completed.")

    def update_profile(self):
        # Dynamically update user profile for more accurate persona
        raise NotImplementedError("To be completed.")
    
    def process(self, article, summaries):
        for summary in reversed(summaries):
            is_accurate, feedback = self.check_truth(article, summary)
            if is_accurate:
                self.logger.info("Summary accepted.")
                return summary
            else:
                self.logger.warning("Summary needs revision: %s", feedback)
        
        self.logger.warning("No acceptable summary found. Reverting to zero-shot summary.")
        return summaries[0] if summaries else None