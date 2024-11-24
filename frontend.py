import os
import gradio as gr
from datetime import date
from demo_config import demo_keywords, demo_articles
from agent import SummarizationAgent, PersonalizationAgent, ArbiterAgent

# Comment out the below 2 lines if you don't need it!
# from personal_config import OPENAI_API_KEY
# os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

PROFILE = 'config/demo_profile.csv'
ARTICLE = None

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

def generate_zero_shot_summary():
    summarization_agent = SummarizationAgent()
    initial_summary = summarization_agent.process(ARTICLE)
    return initial_summary

def get_feedback(initial_summary):
    personalization_agent = PersonalizationAgent(profile_file=PROFILE)
    summaries = [initial_summary]
    feedback = personalization_agent.process(summaries[-1])
    return feedback

def generate_refined_summary(feedback):
    summarization_agent = SummarizationAgent()
    refined_summary = summarization_agent.process(ARTICLE, feedback=feedback)
    return refined_summary

def reset_form():
    return [], "", "", "", ""

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
            "Explore Your Roots: How to Plan a Family Heritage Trip"
        ],
        label="Choose an article to summarize:",
    )
    articles.change(choose_article, articles)
    gr.Markdown("&nbsp;" * 10)

    # Generate the zero-shot summary
    generate_initial_summary_button = gr.Button("1. Generate a Summary")
    initial_summary = gr.Textbox(label="Zero-Shot Summary:")
    generate_initial_summary_button.click(generate_zero_shot_summary, inputs=None, outputs=initial_summary)
    gr.Markdown("&nbsp;" * 10)

    # Get the feedback (and show it)
    get_feedback_button = gr.Button("2. Get Persona Feedback")
    feedback = gr.Textbox(label="Persona Feedback:")
    get_feedback_button.click(get_feedback, inputs=initial_summary, outputs=feedback)
    gr.Markdown("&nbsp;" * 10)

    # Get the refined summary
    get_refined_summary_button = gr.Button("3. Refine the Summary")
    refined_summary = gr.Textbox(label="Refined Summary:")
    get_refined_summary_button.click(generate_refined_summary, inputs=feedback, outputs=refined_summary)
    gr.Markdown("&nbsp;" * 10)

    # Reset button to go again
    reset_button = gr.Button("Reset All Fields")
    reset_button.click(reset_form, inputs=None, outputs=[interests, articles, initial_summary, feedback, refined_summary])
    gr.Markdown("&nbsp;" * 10)

demo.launch()