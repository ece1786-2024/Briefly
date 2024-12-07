import os
import json
import gradio as gr
from datetime import date
from demo_config import demo_keywords, demo_articles
from agent import SummarizationAgent, PersonalizationAgent, ArbiterAgent

# Comment out the below 2 lines if you don't need it!
# from personal_config import OPENAI_API_KEY
# os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

PROFILE = 'config/demo_profile.csv'
ARTICLE = None
NUM_ITERS = 3

def generate_demo_profile(selected_options):
    keywords = []
    for option in selected_options:
        keywords = keywords + demo_keywords[option]
    today = date.today()
    if os.path.exists(PROFILE):
        os.remove(PROFILE)

    with open(PROFILE, 'w') as f:
        f.write("Keyphrase,Level,Date\n")
        for keyword in keywords:
            line = keyword + ",Advanced," + str(today) + "\n"
            f.write(line)

def choose_article(selected_option):
    global ARTICLE
    ARTICLE = demo_articles[selected_option]

def get_personalized_summary():
    summarization_agent = SummarizationAgent()
    initial_summary = summarization_agent.process(ARTICLE)
    status_msg = "Zero-shot summary generated...\n"
    debug_msg = f"ZERO-SHOT SUMMARY IS: \n{initial_summary}\n\n"
    yield status_msg, debug_msg, gr.update(), gr.update()
    personalization_agent = PersonalizationAgent(profile_file=PROFILE)
    status_msg += "Persona generated...\n"
    debug_msg += f"PERSONA IS: \n{personalization_agent.persona}\n\n"
    yield status_msg, debug_msg, gr.update(), gr.update()
    summaries = [initial_summary]
    for i in range(NUM_ITERS):
        feedback = personalization_agent.process(summaries[-1])
        status_msg += f"Feedback #{i + 1} generated...\n"
        debug_msg += f"FEEDBACK #{i + 1} IS: \n{feedback}\n\n"
        yield status_msg, debug_msg, gr.update(), gr.update()
        new_summary = summarization_agent.process(ARTICLE, feedback)
        status_msg += f"Refined summary #{i + 1} generated...\n"
        debug_msg += f"REFINED SUMMARY #{i + 1} IS: \n{new_summary}\n\n"
        yield status_msg, debug_msg, gr.update(), gr.update()
        summaries.append(new_summary)
    status_msg += "Checking with arbiter...\n"
    debug_msg += "CHECKING WITH ARBITER!\n\n"
    yield status_msg, debug_msg, gr.update(), gr.update()
    arbiter_agent = ArbiterAgent(profile_file=PROFILE)
    final_summary, bias_rating, keyphrases = arbiter_agent.process(ARTICLE, summaries)
    if final_summary:
        status_msg += "Final summary generated...\n"
        debug_msg += f"FINAL SUMMARY IS: \n{final_summary}\n\n"
        final_msg = f"{final_summary}\n\nBIAS RATING: {bias_rating[0]}/5 (lower is less biased)"
        keyphrases = "\n".join(list(json.loads(keyphrases).keys()))
        yield status_msg, debug_msg, final_msg, keyphrases
    else:
        error_msg = "ERROR: All summaries had factual inconsistencies. Please check the debug logs."
        status_msg += error_msg
        debug_msg += f"ARBITER OUTPUT IS: \n{error_msg}\n\n"
        yield error_msg, f"ARBITER OUTPUT IS: \n{error_msg}\n\n", error_msg, "No keyphrases generated due to above error messages."

def soft_reset():
    return "", "", "", ""

def reset_form():
    return [], "", "", "", "", ""

demo_profile = "config/demo.csv"
with gr.Blocks() as demo:
    # Briefly banner
    gr.Image(value="assets/briefly.png", show_label=False, type="filepath")
    gr.Markdown("&nbsp;" * 10)

    # Interests checkboxes
    interests = gr.CheckboxGroup(
        choices=["World News", "U.S. Politics", "Business", "Sports", "Entertainment", "Technology", "Canada", "Food", "Travel"],
        label="Select your areas of expertise:"
    )
    interests.change(generate_demo_profile, interests)
    gr.Markdown("&nbsp;" * 10)

    # Articles radio buttons
    articles = gr.Radio(
        choices=[
            "Israeli Strike in the Heart of Beirut Kills at Least 20",
            "Trump’s Trade Agenda Could Benefit Friends and Punish Rivals",
            "What Elon Musk Needs From China",
            "Well, was it worth it, New York Giants fans?",
            "Kendrick Lamar Releases a Surprise Album, 'GNX'",
            "Elon Musk Gets a Crash Course in How Trumpworld Works",
            "Enjoy the GST break on those Christmas gifts, kids — you’ll still be paying it back long after Justin Trudeau is gone",
            "A Very Veggie Thanksgiving",
            "Explore Your Roots: How to Plan a Family Heritage Trip",
            "Dodgers Capture World Series by Storming Back in Game 5"
        ],
        label="Choose an article to summarize:",
    )
    articles.change(choose_article, articles)
    gr.Markdown("&nbsp;" * 10)

    # Get the personalized summary!
    get_personalized_summary_button = gr.Button("Get Your Personalized Summary")

    with gr.Tab("Main Output"):
        status_textbox = gr.Textbox(label="Status Updates:", lines=10)
        gr.Markdown("&nbsp;" * 10)
        final_summary_textbox = gr.Textbox(label="Personalized Summary:", lines=5)
        gr.Markdown("&nbsp;" * 10)
        keyphrases_textbox = gr.Textbox(label="Extracted Keyphrases:", lines=6)

    with gr.Tab("Full Agentic Conversation"):
        debug_textbox = gr.Textbox(label="", lines=20)

    get_personalized_summary_button.click(get_personalized_summary, inputs=None, outputs=[status_textbox, debug_textbox, final_summary_textbox, keyphrases_textbox])

    # Soft Reset
    gr.Markdown("&nbsp;" * 10)
    soft_reset_button = gr.Button("Reset All Fields but Keep User Data")
    soft_reset_button.click(soft_reset, inputs=None, outputs=[status_textbox, debug_textbox, final_summary_textbox, keyphrases_textbox])
    gr.Markdown("&nbsp;" * 10)

    # Hard Reset
    reset_button = gr.Button("Reset All Fields and Clear User Data")
    reset_button.click(reset_form, inputs=None, outputs=[interests, articles, status_textbox, debug_textbox, final_summary_textbox, keyphrases_textbox])
    gr.Markdown("&nbsp;" * 10)

demo.launch()