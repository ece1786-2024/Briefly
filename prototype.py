# Temporary file for testing prototype
from agent import SummarizationAgent, PersonalizationAgent, ArbiterAgent
import pandas as pd

def load_articles(filename):
    # Load articles and add output columns    
    df = pd.read_csv(filename)
    df['Zero-Shot Summary'] = pd.NA
    df['Last Iteration'] = pd.NA
    df['Selected'] = pd.NA
    return df

def generate_summary(article_text, feedback_rounds=2, max_retries=1):
    # Initialize agents
    summarization_agent = SummarizationAgent()
    personalization_agent = PersonalizationAgent()
    arbiter_agent = ArbiterAgent()

    retry_count = 0
    while retry_count < max_retries:
        # Generate initial summary zero-shot
        initial_summary = summarization_agent.process(article_text)

        # Refine summary with PersonalizationAgent Feedback
        summaries = [initial_summary]
        for _ in range(feedback_rounds):
            feedback = personalization_agent.process(summaries[-1])
            refined_summary = summarization_agent.process(article_text, feedback=feedback)
            summaries.append(refined_summary)

        # Verify using arbiter
        final_summary = arbiter_agent.process(article_text, summaries[1:]) # EXCLUDING ZERO-SHOT from arbiter

        if final_summary:  # If summary passes
            return final_summary, initial_summary, summaries[-1]
        else:
            retry_count += 1  # Summary fails
            print(f"Retry {retry_count}/{max_retries}: No acceptable summary found. Retrying...")
            
    # If max retries are exceeded
    print("Max retries exceeded. Returning the most recent try.")
    return None, initial_summary, summaries[-1] if summaries else None

if __name__ == "__main__":
    # Params
    ###############################
    #filename = 'data/newspaper.csv' # General
    filename = 'data/trump.csv' # US Politics
    article = -1
    single = True
    savename = 'results/revision.csv'
    #savename = 'results/general_summary.csv'
    ###############################
    df = load_articles(filename)
    if single:
        article_text = df['Body'].iloc[article]
        article_title = df['Title'].iloc[article]
        print(f'Summarizing: {article_title}...')
        generate_summary(article_text, feedback_rounds=2)
        print('Done.')
    else: 
        for article in range(len(df)):
            article_text = df['Body'].iloc[article]
            article_title = df['Title'].iloc[article]
            print(f'Summarizing: {article_title}...')
            final, initial, last = generate_summary(article_text, feedback_rounds=3)
            print('Done.')
            df.loc[article, 'Zero-Shot Summary'] = initial
            df.loc[article, 'Last Iteration'] = last
            df.loc[article, 'Selected'] = final
            df.to_csv(savename, index=False)
        print("Saved")
