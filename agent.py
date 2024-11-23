import openai
import os
import logging
import datetime
import csv
import json
import warnings

from sympy import per

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
    config_folder = "config"

    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger("agent")
        self.configure_logger() # Initialize logger for debugging
        
        self.api_params = self.load_api_config()  # Load API params from config
        self.messages = self.initialize_messages() # initialize messages list with sys msg

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

    
    def load_api_config(self):
        # Load API config and initial messages for the given agent
        api_config_file = os.path.join(Agent.config_folder, "api_config.csv")
        if not os.path.exists(api_config_file):
            error_message = f"API config file '{api_config_file}' does not exist."
            self.logger.error(error_message)
            raise FileNotFoundError(error_message)
        try:
            with open(api_config_file, mode='r', newline='', encoding='utf-8', errors='replace') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row["AgentName"].strip() == self.name:
                        # Convert config to proper types and return as dict
                        # Provide defaults for all except for sys and usr msg
                        system_message = row.get("SystemMessage", "").strip()
                        user_message_template = row.get("UserMessage", "").strip()
                        # check for sys and usr msgs
                        if not system_message:
                            error_message = f"SystemMessage is missing for agent: '{self.name}'."
                            self.logger.critical(error_message)
                            raise ValueError(error_message)

                        if not user_message_template:
                            error_message = f"UserMessage is missing or empty for agent: '{self.name}'."
                            self.logger.critical(error_message)
                            raise ValueError(error_message)
                        
                        return {
                            "model": row.get("Model", "gpt-4o").strip(),
                            "temperature": float(row.get("Temperature", 1)),
                            "max_tokens": int(row.get("MaxTokens", 2048)),
                            "top_p": float(row.get("TopP", 1)),
                            "frequency_penalty": float(row.get("frequency_penalty", 0)),
                            "presence_penalty": float(row.get("presence_penalty", 0)),
                            "system_message": system_message,
                            "user_message_template": user_message_template
                        }
            # if no config found
            error_message = f"No API configuration found for agent '{self.name}'."
            self.logger.error(error_message)
            raise ValueError(error_message)
        except Exception as e:
            self.logger.error(f"Error loading API config: {e}")
            raise

    def initialize_messages(self):
        # Initialize the agent's messages list with the system message
        messages = []
        system_message = self.api_params.get("system_message")
        messages.append({"role": "system", "content": system_message})
        return messages

    def call_api(self, params, initial_summary=False, persona=False): # Calls openAI API
        # params (dict): key-value pairs to fill the user message template.
        """
        params = {
            "article": "News News New",
            "feedback": "Less news"
        }
        """
        # initial_summary: handle initial summary, yes it's messy I forgot about it until I tested
        if initial_summary:
            # We should all be using a basic prompt for this
            sys_msg = "You are a summarization agent who summarizes news articles in three sentences."
            usr_msg_template = "Please summarize the following article: {article}"
            user_message = usr_msg_template.format(**params)
            self.messages = []
            self.messages.append({"role": "system", "content": sys_msg})
            self.messages.append({"role": "user", "content": user_message})
        elif persona: # I also forgot about persona...
            sys_msg = (
                    "You are an assistant that generates a user persona based on their background knowledge. You will be given a list of keyphrases."
                    "Describe the user's familiarity with each topic, and indicate whether they are an expert, moderately informed, or a beginner."
                    )
            usr_msg_template = "Create a user persona based on the following information: {profile}"
            user_message = usr_msg_template.format(**params)
            persona_msg = []
            persona_msg.append({"role": "system", "content": sys_msg})
            persona_msg.append({"role": "user", "content": user_message})
        else: # regular usage
            # Fill in user msg template
            user_message_template = self.api_params["user_message_template"]
            user_message = user_message_template.format(**params)

            # Add msg to messages list (history)
            self.messages.append({"role": "user", "content": user_message})

        if persona:# I also forgot about persona...
            message = persona_msg
        else: #summary and normal operation
            message = self.messages

        api_params = {
            "model": self.api_params["model"],
            "temperature": self.api_params["temperature"],
            "max_tokens": self.api_params["max_tokens"],
            "top_p": self.api_params["top_p"],
            "frequency_penalty": self.api_params["frequency_penalty"],
            "presence_penalty": self.api_params["presence_penalty"],
            "messages": message
        }

        try:
            response = openai.chat.completions.create(**api_params)
            output = response.choices[0].message.content.strip()
            if not persona: # don't do it if generating persona
                self.messages.append({"role": "assistant", "content": output}) # Append response to messages list
            self.logger.info("Received response: %s", output) # Log for debugging
            # Log prompts and response for illustrative purposes
            if initial_summary: # Add back the config system message for refining summaries
                self.log_conversation("system", sys_msg)
                self.messages.append({"role": "system", "content": self.api_params["system_message"]}) #sys msg
            elif persona:
                self.log_conversation("system", sys_msg)
            else: # normal operation
                self.log_conversation("system", self.api_params["system_message"]) #sys msg
            self.log_conversation("user", user_message) # usr msg
            self.log_conversation("assistant", output)
            return output
        except Exception as e:
            self.logger.error(f"Error in API call: {e}")
            return None

    def process(self, *args, **kwargs):
        raise NotImplementedError("Implement in the agent subclasses")
    
    @staticmethod
    def load_profile():
        # Load the existing keyphrases from the profile.csv
        # outputs keyphrases
        # set: makes it easy to check for duplicates
        # list: needed if order matters
        # dict: if we want to add beginner, intermediate, advanced and date added
        # currently using a dict for future proofing
        profile_file = os.path.join(Agent.config_folder, "profile.csv")

        if not os.path.exists(profile_file):
            logging.warning(f"Profile file '{profile_file}' does not exist.")
            return {}

        try:
            profile = {}
            with open(profile_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                if 'Keyphrase' not in reader.fieldnames:
                    raise ValueError(f"Profile file '{profile_file}' must have a 'Keyphrase' column.")
                
                for row in reader:
                    keyword = row['Keyphrase'].strip()
                    level = row.get('Level', 'Advanced').strip() # Default: extreme case
                    date = row.get('Date', None) # Date, should get updated if repeated
                    profile[keyword] = {
                        "Level": level,
                        "Date": date
                    }

            logging.info(f"Loaded profile with {len(profile)} keyphrases.")
            return profile
        except Exception as e:
            logging.error(f"Error reading profile file: {e}")
            raise
    
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
            params = {"article": article, "feedback": feedback}
            summary = self.call_api(params)
        else: # Initial zero-shot summary
            self.logger.debug("Generating initial summary...")
            params = {"article": article}
            summary = self.call_api(params, initial_summary=True)

        if summary:
            self.logger.info("Summary generated successfully.")
            self.summaries.append(summary)
        else:
            self.logger.error("Failed to generate summary.")
        
        return summary

class PersonalizationAgent(Agent): # Personalization Agent
    def __init__(self):
        super().__init__("Personalization Agent")
        self.profile = self.load_profile() # List of keywords (How will we get this? Survey, reading history?, ideally with usage)
        self.persona = self.generate_persona()
    
    def generate_persona(self):
        # Create a persona based on profile keywords
        params = {"profile": self.profile}
        persona_description = self.call_api(params, persona=True)
        self.logger.info(f"Generated persona: {persona_description}")
        return persona_description
    
    def generate_feedback(self, summary):
        # Use the persona and summary to generate feedback about the summary
        params = {"persona": self.persona, "summary": summary}
        feedback = self.call_api(params)
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
        self.profile = self.load_profile()

    def check_bias(self, article, summary):
        # Check bias
        raise NotImplementedError("To be completed.")
    
    def check_truth(self, article, summary):
        # Check for preservation of truth/facts
        params = {"article": article, "summary": summary}
        try:
            response = self.call_api(params)

            if 'Arbiter=1' in response:
                return True, "Acceptable"
            else:
                return False, response
        except Exception as e:
            self.logger.error(f"Error in summary verification: {e}")
            return False, "Error during verification"
    
    @DeprecationWarning
    def _update_profile(self, profile, keyphrases):
        # Dynamically update user profile for more accurate persona

        # It takes in the keyphrases and updates the csv file
        # profile = existing keyphrases
        # keyphrases = new generated ones
        # Should probably check if the new keyphrases are unique or similar
        # Maybe add age of keyphrases to profile
        # there is an age field in profile.csv, doesn't need to be used though
        # output of load_profile is a dict
        ########################################################
        # Add code for updating the dict (profile) with newly generated keyphrases
        # Should check for similar/existing, update date if true
        ########################################################
        warnings.warn(
            "_update_profile is deprecated and may be removed in future versions.",
            DeprecationWarning,
        )
        profile_file = os.path.join(Agent.config_folder, "profile.csv")
        try:
            with open(profile_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['Keyphrase', 'Level', 'Date'])
                writer.writeheader()
                for keyword, metadata in profile.items():
                    writer.writerow({
                        "Keyphrase": keyword,
                        "Level": "",#metadata["Level"],
                        "Date": metadata["Date"]
                    })
            self.logger.info("Updated profile saved.")
        except Exception as e:
            self.logger.error(f"Error saving profile file: {e}")
            raise

    def update_profile(self, profile, keyphrases):
        """
        Update the profile with new keyphrases and save to CSV.

        Args:
            profile (dict): The existing profile dictionary.
            keyphrases (str or dict): New keyphrases to update, provided as a string or dictionary.
        """
        # Parse keyphrases if they are provided as a string
        if isinstance(keyphrases, str):
            try:
                keyphrases = json.loads(keyphrases)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid keyphrases format: {e}")
                raise ValueError("Keyphrases must be a valid JSON string or dictionary.")

        # Merge keyphrases into profile
        for keyword, metadata in keyphrases.items():
            profile[keyword] = metadata  # Update or add new keyphrases

        # Write the updated profile to a CSV
        profile_file = os.path.join(Agent.config_folder, "profile.csv")
        try:
            with open(profile_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['Keyphrase', 'Level', 'Date'])
                writer.writeheader()
                for keyword, metadata in profile.items():
                    writer.writerow({
                        "Keyphrase": metadata.get("Keyphrase", keyword),
                        "Level": "",#metadata.get("Level", "Unknown"),
                        "Date": datetime.datetime.now().strftime("%Y-%m-%d")
                    })
            self.logger.info("Updated profile saved.")
        except Exception as e:
            self.logger.error(f"Error saving profile file: {e}")
            raise

    def generate_keyphrases(self,final_summary):
        # Use the Personalization Agent to identify known information in the final summary.
        """
        Use the Personalization Agent to identify known information in the final summary.
        """
        # Code for generating keyphrases from article/summary goes here
        self.logger.info("Keyphrases extracted.")

        # Ask the Personalization Agent to identify known topics based on the summary
        previous_knolwedge_prompt = (
            f"This is the summary: {final_summary}"
            f"Known information from the user includes:\n{self.profile}\n\n"
        )

        extraction_prompt = (
            """
                Analyze the provided summary and extract key concepts, topics, or entities. For each, generate a JSON object where each key represents the concept, and its value is a dictionary with the following structure:
                {
                    "Keyphrase": "A single, concise sentence summarizing the topic or entity.",
                    "Level": "Importance level (e.g., high, medium, low).",
                    "Date": "YYYY-MM-DD."
                }
                Follow these rules:
                - Only use the topics explicitly mentioned in the summary.
                - Structure the output exactly as shown in the example below.
                - Do not add any text outside the JSON structure.
                - Ensure the output is a valid JSON object.

                Example output:
                {
                    "Topic 1": {
                        "Keyphrase": "A single, concise sentence.",
                        "Level": "high",
                        "Date": "2024-11-23"
                    },
                    "Topic 2": {
                        "Keyphrase": "Another concise sentence.",
                        "Level": "medium",
                        "Date": "2024-11-23"
                    }
                }

                Now extract the data and produce the JSON object.
            """
        )
        known_info_response = self.call_api(extraction_prompt, previous_knolwedge_prompt )

        return known_info_response
    
    def process(self, article, summaries):
        for summary in reversed(summaries):
            is_accurate, feedback = self.check_truth(article, summary)
            if is_accurate:
                self.logger.info("Summary accepted.")
                keyphrases = self.generate_keyphrases(summary) # generates keyphrases from articles/summary
                self.update_profile(self.profile, keyphrases) # checks and updates profile.csv
                return summary
            else:
                self.logger.warning("Summary needs revision: %s", feedback)
                # return something that forces the model to restart??
        
        self.logger.warning("No acceptable summary found. Reverting to zero-shot summary.")
        return summaries[0] if summaries else None