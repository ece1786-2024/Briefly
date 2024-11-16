import os
from utils import OPENAI_API_KEY
import openai
from articles import entertainment1
from articles import general10
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY


INITIAL_SUMMARIZER_SYSTEM_MESSAGE = '''
You are a news summarization agent. Your primary function is to provide summaries of the full news article below. The 
summaries will be no longer than THREE sentences. You will then receive requests to refine these summaries. You should 
listen to the requests and provide new summaries based on the feedback. No matter what feedback is provided, you should 
ONLY respond with three sentence summaries, taking into account all feedback and requests that have been provided. 
The summaries should contain facts only from the article, and should sound like news articles themselves. Whenever 
possible, the sentences should be brief and snappy. Regardless of feedback, the first sentence should always recap the 
most important point of the article.
'''

INITIAL_PERSONA_SYSTEM_MESSAGE = '''
You are a personalization agent. Your primary function is to read generic news summaries and then ask for new summaries 
with more targeted focus. Your responses will be limited to one short sentence. Whenever relevant to the topic, you should use one of your 
INTEREST PHRASES to help guide the summary rewrite. If an interest phrase is relevant to an article, you should phrase your request as: 
"Please rewrite the summary, but this time tell me less about <INTEREST> and more about...". If none of your INTEREST PHRASES are relevant 
to the article, then you should phrase your request as: "Please rewrite the summary, but this time give me a more basic explanation about...".
Do NOT repeat interest phrases in follow-up questions. Your INTEREST PHRASES are as follows: 
Taylor Swift, Fearless Album, 1989 Album, Reputation Era, Folklore Vibes, Midnights Aesthetic, The Eras Tour Extravaganza, 
Travis Kelce Romance, The Swifties Family, 1989 World Tour Memories, Blank Space Anthem, All Too Well (10-Minute Version) Masterpiece, 
Shake It Off Energy, You Belong With Me Classic, Love Story Fairytale, The Man Statement, Taylor’s Version Re-recordings, 
The Squad Goals, Lucky Number 13, Secret Sessions Magic, Cat Mom Life, The Snake Era Drama, Long Live Tribute, 
Iconic Rolling Stone Covers, Miss Americana Documentary, Fifth Avenue Apartment Mystique, Tom Homan, border czar, immigration policy
'''

INITIAL_COMBINER_SYSTEM_MESSAGE = '''
You are a combining agent. You will receive three summaries about an article, each of which is three sentences long. 
You must combine these three summaries into one summary which is also three sentences long. Your focus should be on 
retaining the DEPTH AND DETAIL of the original summaries; this means keeping as many numbers, figures, proper nouns, 
and other details from all summaries as possible. Secondly, you should attempt to REMOVE ANY BIAS from the final summary 
by removing subjective descriptors that are overly positive or negative. Thirdly, try to keep the language plain and 
simple, targeting at most a tenth grade reading level.
'''

INITIAL_EXTRACTOR_SYSTEM_MESSAGE = '''
You are a helpful assistant.
'''


class OpenAI_Client():
    def __init__(self, instructions):
        self.instructions = instructions
        self.system_message = []
        self.key_phrases = []
        self.conversation_history = []
        self.client = openai.OpenAI()

    def add_phrase(self, phrase):
        self.key_phrases.append(phrase)

    def set_system_message(self):
        phrases = ", ".join(self.key_phrases)
        message = self.instructions + phrases
        self.system_message = [{"role": "system", "content": message}]

    def add_user_message(self, message):
        self.conversation_history.append({"role": "user", "content": message})

    def add_assistant_message(self, message):
        self.conversation_history.append({"role": "assistant", "content": message})

    def clear_history(self):
        self.conversation_history = []

    def get_response(self, temp=1.0):
        self.set_system_message()
        full_conversation = self.system_message + self.conversation_history
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=temp,
            messages=full_conversation
        )
        return response.choices[0].message.content


def generate_summary(summarizer: OpenAI_Client, prev_summary: str, refinement: str) -> str:
    # First, update the conversation history
    if prev_summary is not None:
        summarizer.add_assistant_message(prev_summary)
    if refinement is not None:
        summarizer.add_user_message(refinement)
    # Now get the new summary
    summary = summarizer.get_response()
    return summary


def generate_refinement(persona: OpenAI_Client, prev_refinement: str, summary: str) -> str:
    # First, update the conversation history
    if prev_refinement is not None:
        persona.add_assistant_message(prev_refinement)
    persona.add_user_message(summary)
    # Now get the new refinement
    refinement = persona.get_response(temp=1.5)
    return refinement


def generate_combined_summary(combiner: OpenAI_Client, summary1, summary2, summary3):
    prompt = "Please combine the following three summaries into a single summary. At the end, provide one long sentence explaining which are the most important aspects you've captured in the summary.\n\n"
    prompt += summary1 + "\n\n" + summary2 + "\n\n" + summary3
    combiner.add_user_message(prompt)
    combined_summary = combiner.get_response()
    return combined_summary

def extract_keywords(extractor: OpenAI_Client, summary):
    prompt = "Please create a comma-separated list of three small key phrases (1-3 words) to summarize the following text. Do not write anything except the comma-separated list of phrases. The text is:\n\n"
    prompt += summary
    extractor.add_user_message(prompt)
    keywords = extractor.get_response()
    return keywords

summarizer = OpenAI_Client(INITIAL_SUMMARIZER_SYSTEM_MESSAGE)
# summarizer.add_user_message(entertainment1)
summarizer.add_user_message(general10)
summary = generate_summary(summarizer, None, None)
print("SUMMARY 1: " + summary)

persona = OpenAI_Client(INITIAL_PERSONA_SYSTEM_MESSAGE)
persona.set_system_message()
refinement = generate_refinement(persona, None, summary)
print("REFINEMENT 1: " + refinement)

summary1 = generate_summary(summarizer, summary, refinement)
print("SUMMARY 2: " + summary1)

new_refinement = generate_refinement(persona, refinement, summary1)
print("REFINEMENT 2: " + new_refinement)

summary2 = generate_summary(summarizer, summary1, new_refinement)
print("SUMMARY 3: " + summary2)

new_refinement = generate_refinement(persona, new_refinement, summary2)
print("REFINEMENT 3: " + new_refinement)

summary3 = generate_summary(summarizer, summary2, new_refinement)
print("SUMMARY 3: " + summary3)

combiner = OpenAI_Client(INITIAL_COMBINER_SYSTEM_MESSAGE)
combined_summary = generate_combined_summary(combiner, summary1, summary2, summary3)
print("COMBINED: " + combined_summary)

extractor = OpenAI_Client(INITIAL_EXTRACTOR_SYSTEM_MESSAGE)
keywords = extract_keywords(extractor, combined_summary)
print("KEYWORDS: " + keywords)
